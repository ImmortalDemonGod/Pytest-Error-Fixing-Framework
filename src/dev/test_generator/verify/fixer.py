"""
GeneratedTestFixer — application layer.

Takes a VerificationResult containing failing generated tests and attempts
to fix them using the existing AIManager + ChangeApplier infrastructure.

Each failing test file gets one or more fix attempts.  After all fixes are
applied the generated-test directory is re-verified and the new result is
returned so the caller can report what was fixed vs still broken.
"""

import logging
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
        """Attempt to fix all failures in *result*, then re-verify.

        Returns a new VerificationResult reflecting the state after fixes.
        If all tests already passed, returns *result* unchanged.
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
        """Attempt to fix a single test file, trying up to max_attempts times.

        After each fix attempt we re-run the test file to verify the fix
        actually works.  If it doesn't, we restore from backup before the
        next attempt so we never leave the file in a *worse* state.
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
                    logger.warning("Fix attempt %d: apply failed for %s", i + 1, test_file.name)
                    continue

                # Verify the fix actually works by re-running the file
                post_output = runner.capture_error_output(test_file)
                from src.dev.test_generator.verify.runner import parse_pytest_output
                import subprocess, sys
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", str(test_file), "-q", "--no-header", "--tb=no"],
                    capture_output=True, text=True,
                    env=runner._build_env(),
                )
                if proc.returncode in (0, 5):
                    logger.info("Fix verified for %s", test_file.name)
                    return

                # Fix applied but tests still fail — restore and try again
                logger.info(
                    "Fix attempt %d produced no improvement for %s; restoring",
                    i + 1,
                    test_file.name,
                )
                if backup_path:
                    self._applier.restore_backup(test_file, backup_path)
                # Update error context with new failures for next attempt
                raw_error = runner.capture_error_output(test_file)
                error = _make_test_error(test_file, failure, raw_error)

            except Exception as exc:
                logger.warning("Fix attempt %d failed: %s", i + 1, exc)
                if backup_path:
                    try:
                        self._applier.restore_backup(test_file, backup_path)
                    except Exception:
                        pass


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _group_by_file(failures: List[TestFailure]) -> dict:
    """Group TestFailures by their test_file path."""
    groups: dict = {}
    for f in failures:
        groups.setdefault(f.test_file, []).append(f)
    return groups


def _make_test_error(test_file: Path, failure: TestFailure, raw_error: str = "") -> TestError:
    """Build a branch_fixer TestError from a TestFailure for AIManager."""
    # Prefer raw_error (full pytest output) over the often-empty inline message
    error_text = raw_error or failure.error_output
    return TestError(
        test_file=test_file,
        test_function=failure.test_id,
        error_details=ErrorDetails(
            error_type="GeneratedTestFailure",
            message=error_text,
            stack_trace=error_text,
        ),
    )
