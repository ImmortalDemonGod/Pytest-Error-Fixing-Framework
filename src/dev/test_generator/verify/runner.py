"""
VerificationRunner — infrastructure layer.

Runs pytest as a subprocess on a directory of generated test files and
returns a structured VerificationResult describing which tests passed
and which failed (with error output).

Using a subprocess (not in-process pytest) gives a clean environment and
avoids the ``report.function`` parsing bug documented in CLAUDE.md.
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class TestFailure:
    """A single failing test item from a generated test file.

    Attributes
    ----------
    test_file:
        Absolute path to the test file.
    test_id:
        The pytest node ID after the file path, e.g. ``TestAdd::test_add_positive``.
    error_output:
        The short traceback / error message captured from pytest output.
    """

    test_file: Path
    test_id: str
    error_output: str


@dataclass
class VerificationResult:
    """Aggregated result of running pytest on a generated-test directory.

    Attributes
    ----------
    output_dir:
        Directory that was tested.
    passed:
        Number of passing tests.
    failed:
        Number of failing / erroring tests (includes ERROR at setup/teardown).
    failures:
        Structured info for each failing test item (best-effort; may be
        incomplete for collection errors).
    exit_code:
        Raw pytest exit code. 0 = all passed, 1 = some failed, 5 = no tests.
        This is the authoritative signal for ``all_passed``.
    raw_output:
        Full combined stdout+stderr from pytest (for debugging).
    """

    output_dir: Path
    passed: int = 0
    failed: int = 0
    failures: List[TestFailure] = field(default_factory=list)
    exit_code: int = 0
    raw_output: str = ""

    @property
    def all_passed(self) -> bool:
        """
        Indicates whether the pytest run is considered successful.
        
        Returns:
            bool: `true` if the exit code is 0 (all collected tests passed) or 5 (no tests collected), `false` otherwise.
        """
        return self.exit_code in (0, 5)


class VerificationRunner:
    """Run pytest on a directory of generated tests and parse the results.

    Parameters
    ----------
    extra_pythonpath:
        Colon-separated paths to prepend to PYTHONPATH so generated tests
        can import the source modules they test.
    """

    def __init__(self, extra_pythonpath: str = "") -> None:
        """
        Initialize the runner with an optional PYTHONPATH prefix for subprocessed pytest runs.
        
        Parameters:
            extra_pythonpath (str): Colon-separated path(s) to prepend to `PYTHONPATH` when spawning pytest subprocesses; empty string means no modification.
        """
        self.extra_pythonpath = extra_pythonpath

    def run(self, output_dir: Path) -> VerificationResult:
        """
        Execute pytest against the generated tests in `output_dir` and return a parsed VerificationResult.
        
        Parameters:
            output_dir (Path): Directory containing the generated test files to run.
        
        Returns:
            VerificationResult: Aggregated results parsed from pytest's output, including passed/failed counts, per-test failures, the raw pytest output, and the subprocess exit code.
        """
        env = self._build_env()
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(output_dir),
                "--tb=short",
                "-q",
                "--no-header",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        combined = proc.stdout + proc.stderr
        return parse_pytest_output(combined, output_dir, exit_code=proc.returncode)

    def capture_error_output(self, test_file: Path) -> str:
        """
        Run pytest on a single test file with long tracebacks to capture detailed failure output.
        
        Returns:
            combined (str): Combined stdout and stderr produced by the pytest subprocess.
        """
        env = self._build_env()
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_file),
                "--tb=long",
                "-q",
                "--no-header",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        return proc.stdout + proc.stderr

    def _build_env(self) -> dict:
        """
        Build an environment mapping for subprocess execution, copying the current process environment and prepending this runner's extra_pythonpath to PYTHONPATH when provided.
        
        If `self.extra_pythonpath` is non-empty, it is prepended to the existing `PYTHONPATH` using a colon separator; the existing `PYTHONPATH` is preserved when present.
        
        Returns:
            dict: A copy of the environment suitable for passing to subprocess calls.
        """
        env = os.environ.copy()
        if self.extra_pythonpath:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = (
                f"{self.extra_pythonpath}:{existing}"
                if existing
                else self.extra_pythonpath
            )
        return env


# ---------------------------------------------------------------------------
# Pure parsing helpers (module-level for easy testing)
# ---------------------------------------------------------------------------

# Matches FAILED or ERROR lines in pytest -q output.
# The " - error message" suffix is optional (parametrized tests often omit it).
_FAILED_LINE = re.compile(r"^(?:FAILED|ERROR)\s+(.+?)::(.+?)(?:\s+-\s+(.*))?$")

# Pytest summary line ends with " in N.Ns" and contains digit-prefixed counts.
# Must have at least one digit before "passed", "failed", or "error" to avoid
# matching garbage like "PytestWarning: (rm_rf) error removing /path".
_SUMMARY_PATTERN = re.compile(
    r"(\d+)\s+(?:failed|passed|error)",
    re.IGNORECASE,
)
_SUMMARY_LINE_PATTERN = re.compile(
    r"\d+\s+(?:failed|passed|error).*\s+in\s+[\d.]+s",
    re.IGNORECASE,
)
_FAILED_COUNT = re.compile(r"(\d+)\s+(?:failed|error)", re.IGNORECASE)
_PASSED_COUNT = re.compile(r"(\d+)\s+passed", re.IGNORECASE)


def parse_pytest_output(
    output: str, output_dir: Path, exit_code: int = 0
) -> VerificationResult:
    """
    Parse pytest combined stdout/stderr into a VerificationResult.
    
    Scans the provided pytest output for failing/errored test lines and a pytest summary line to build structured results. The subprocess exit code is used as the authoritative signal for overall success; textual parsing is used on a best-effort basis to collect per-test failure details, resolve test file paths relative to `output_dir`, and extract passed/failed counts (preferring the numeric values from the pytest summary line that ends with `in Xs`; if no summary is found, the failed count falls back to the number of captured failures).
    
    Parameters:
        output (str): Combined stdout and stderr produced by running pytest.
        output_dir (Path): Directory containing the generated tests; used to resolve relative test file paths found in the output.
        exit_code (int): Subprocess exit code returned by pytest; treated as the authoritative pass/fail indicator.
    
    Returns:
        VerificationResult: Aggregated result containing `output_dir`, `passed`, `failed`, list of `TestFailure` items, `exit_code`, and the original `raw_output`.
    """
    failures: list[TestFailure] = []
    passed = 0
    failed = 0

    for line in output.splitlines():
        stripped = line.strip()
        m = _FAILED_LINE.match(stripped)
        if m:
            file_part = m.group(1)
            test_id_part = m.group(2)
            error_msg = (m.group(3) or "").strip()
            test_file = _resolve_test_file(file_part, output_dir)
            failures.append(
                TestFailure(
                    test_file=test_file,
                    test_id=test_id_part.strip(),
                    error_output=error_msg,
                )
            )

    # Extract counts from the actual pytest summary line (must end in "in Xs")
    summary = _find_summary_line(output)
    if summary:
        failed_m = _FAILED_COUNT.search(summary)
        passed_m = _PASSED_COUNT.search(summary)
        failed = int(failed_m.group(1)) if failed_m else len(failures)
        passed = int(passed_m.group(1)) if passed_m else 0
    else:
        failed = len(failures)

    return VerificationResult(
        output_dir=output_dir,
        passed=passed,
        failed=failed,
        failures=failures,
        exit_code=exit_code,
        raw_output=output,
    )


def _find_summary_line(output: str) -> Optional[str]:
    """
    Find the pytest summary line that ends with the 'in N.Ns' suffix.
    
    The suffix requirement reduces false positives from incidental lines that mention 'error' (for example, PytestWarning messages).
    
    Parameters:
        output (str): Complete pytest stdout/stderr output to search.
    
    Returns:
        Optional[str]: The matched summary line with surrounding whitespace removed, or `None` if no summary line is found.
    """
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if _SUMMARY_LINE_PATTERN.search(stripped):
            return stripped
    return None


def _resolve_test_file(file_part: str, output_dir: Path) -> Path:
    """
    Resolve a pytest-reported file path to an absolute Path.
    
    Parameters:
        file_part (str): File path as reported by pytest; may be absolute or relative.
        output_dir (Path): Directory containing generated tests; used to interpret relative paths.
    
    Returns:
        Path: Absolute path to the test file. If `file_part` is absolute it is returned as-is; otherwise,
        if `output_dir / file_part` exists that path is returned; if not, `file_part` is resolved to an
        absolute path relative to the current working directory.
    """
    p = Path(file_part)
    if p.is_absolute():
        return p
    candidate = output_dir / p
    if candidate.exists():
        return candidate.resolve()
    return p.resolve()
