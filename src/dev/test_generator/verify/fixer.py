"""
GeneratedTestFixer — application layer.

Takes a VerificationResult containing failing generated tests and attempts
to fix them using the existing AIManager + ChangeApplier infrastructure.

Each failing test file gets one or more fix attempts.  After all fixes are
applied the generated-test directory is re-verified and the new result is
returned so the caller can report what was fixed vs still broken.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from branch_fixer.core.models import ErrorDetails, TestError
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.code.change_applier import ChangeApplier

from src.dev.test_generator.verify.runner import (
    TestFailure,
    VerificationResult,
    VerificationRunner,
)

logger = logging.getLogger(__name__)

# Temperature schedule: start low (deterministic), increase on retry
_TEMPERATURES = [0.1, 0.4, 0.7]


class GeneratedTestFixer:
    """Fix failing generated tests using AIManager.

    Parameters
    ----------
    ai_manager:
        Configured AIManager instance (LiteLLM, with API key already set).
    change_applier:
        ChangeApplier instance for writing fixed code back to disk.
    max_attempts:
        Maximum fix attempts per failing file (default: 2).
    """

    def __init__(
        self,
        ai_manager: AIManager,
        change_applier: ChangeApplier,
        max_attempts: int = 2,
    ) -> None:
        """
        Initialize the GeneratedTestFixer with the required collaborators and configuration.
        
        Parameters:
            ai_manager (AIManager): Manager used to generate test-file fixes.
            change_applier (ChangeApplier): Component responsible for applying changes and managing backups.
            max_attempts (int): Maximum number of fix attempts per test file.
        """
        self._ai = ai_manager
        self._applier = change_applier
        self.max_attempts = max_attempts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fix_failures(
        self,
        result: VerificationResult,
        runner: VerificationRunner,
    ) -> VerificationResult:
        """
        Fix failing generated tests in the given verification result and re-run verification.
        
        Attempts AI-driven fixes for each file containing failures, applies successful changes to disk, and then runs a full verification of the output directory.
        
        Returns:
        	An updated VerificationResult reflecting the state after attempting fixes; if all tests already passed, the original `result` is returned.
        """
        if result.all_passed:
            return result

        for test_file, failures in _group_by_file(result.failures).items():
            self._fix_file(test_file, failures, runner)

        return runner.run(result.output_dir)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fix_file(
        self,
        test_file: Path,
        failures: List[TestFailure],
        runner: VerificationRunner,
    ) -> None:
        """
        Attempt to repair a single failing test file by generating and applying fixes until the tests pass or the retry limit is reached.
        
        Tries up to self.max_attempts attempts: for each attempt it requests a fix from the AI, applies the change with a backup, and re-runs pytest for the specific test file. If the tests pass the method returns immediately. If an applied fix does not improve the test outcome the backup is restored and the error context is refreshed for the next attempt. If a required backup restore fails the method aborts further retries to avoid leaving the file in an unknown state.
        """
        raw_error = runner.capture_error_output(test_file)
        failure = failures[0]
        error = _make_test_error(test_file, failure, raw_error)

        for i in range(max(1, self.max_attempts)):
            temperature = _TEMPERATURES[min(i, len(_TEMPERATURES) - 1)]
            logger.info(
                "Fix attempt %d/%d for %s (temp=%.1f)",
                i + 1,
                self.max_attempts,
                test_file.name,
                temperature,
            )
            backup_path: Optional[Path] = None
            try:
                changes = self._ai.generate_fix(error, temperature=temperature)
                applied, backup_path = self._applier.apply_changes_with_backup(
                    test_file, changes
                )
                if not applied:
                    logger.warning(
                        "Fix attempt %d: apply failed for %s", i + 1, test_file.name
                    )
                    continue

                # Verify the fix actually works by re-running the file.
                # Exit code 0 = tests collected AND all passed — the only
                # acceptable outcome.  Exit code 5 (no tests) means the AI
                # deleted or corrupted all tests, which is NOT a fix.
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        str(test_file),
                        "-q",
                        "--no-header",
                        "--tb=no",
                    ],
                    capture_output=True,
                    text=True,
                    env=runner._build_env(),
                    timeout=120,
                )
                if proc.returncode == 0:
                    logger.info("Fix verified for %s", test_file.name)
                    return

                # Fix applied but tests still fail — restore and try again
                logger.info(
                    "Fix attempt %d produced no improvement for %s; restoring",
                    i + 1,
                    test_file.name,
                )
                if backup_path:
                    try:
                        self._applier.restore_backup(test_file, backup_path)
                    except Exception as restore_exc:
                        logger.error(
                            "Restore failed after bad fix for %s: %s",
                            test_file.name,
                            restore_exc,
                        )
                        return  # File in unknown state — abort retries
                # Update error context but keep the same TestError identity
                # so AIManager's conversation thread is preserved across retries.
                raw_error = runner.capture_error_output(test_file)
                if raw_error:
                    error.error_details = ErrorDetails(
                        error_type=error.error_details.error_type,
                        message=raw_error[:500],
                        stack_trace=error.error_details.stack_trace,
                    )

            except subprocess.TimeoutExpired:
                logger.warning("Fix attempt %d timed out for %s", i + 1, test_file.name)
                if backup_path:
                    try:
                        self._applier.restore_backup(test_file, backup_path)
                    except Exception:
                        logger.error(
                            "Restore failed after timeout for %s — aborting",
                            test_file.name,
                        )
                        return
            except Exception as exc:
                logger.warning("Fix attempt %d failed: %s", i + 1, exc)
                if backup_path:
                    try:
                        self._applier.restore_backup(test_file, backup_path)
                    except Exception:
                        logger.error(
                            "Restore failed after error for %s — aborting",
                            test_file.name,
                        )
                        return


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _group_by_file(failures: List[TestFailure]) -> dict:
    """
    Group test failures by their test file.
    
    Parameters:
        failures (List[TestFailure]): Iterable of test failure records.
    
    Returns:
        dict: Mapping from test file Path to a list of `TestFailure` objects for that file.
    """
    groups: dict = {}
    for f in failures:
        groups.setdefault(f.test_file, []).append(f)
    return groups


def _make_test_error(
    test_file: Path, failure: TestFailure, raw_error: str = ""
) -> TestError:
    """
    Create a TestError representing a generated-test failure to guide the AI fixer.
    
    Parameters:
        test_file (Path): Path to the failing test file.
        failure (TestFailure): The failure record for a single failing test in the file.
        raw_error (str): Optional full pytest output; if provided, it is used instead of
            failure.error_output to populate the error details.
    
    Returns:
        TestError: A TestError whose ErrorDetails.error_type is "GeneratedTestFailure" and
            whose message and stack_trace contain an instruction that the AI must return
            a complete, valid pytest test file (not implementation code) followed by the
            pytest output for all failures in the file.
    """
    # Prefer raw_error (full pytest output) over the often-empty inline message.
    # Prepend a clear instruction so the AI cannot mistake this for a source-code
    # rewrite task — it must return a complete, valid TEST file.
    pytest_output = raw_error or failure.error_output
    error_text = (
        "IMPORTANT: This is a TEST FILE. Your output MUST be a complete, valid "
        "pytest test file — not source code, not an implementation. "
        "Fix only the failing tests listed below while keeping all passing tests intact.\n\n"
        f"Pytest output (all failures in this file):\n{pytest_output}"
    )
    return TestError(
        test_file=test_file,
        test_function=failure.test_id,
        error_details=ErrorDetails(
            error_type="GeneratedTestFailure",
            message=error_text,
            stack_trace=error_text,
        ),
    )
