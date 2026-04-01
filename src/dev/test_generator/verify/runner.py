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
        """True only when pytest exit code indicates success.

        Exit codes:
          0 — all collected tests passed
          5 — no tests collected (acceptable: nothing to fail)
        Any other code means at least one test failed or errored.
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
        self.extra_pythonpath = extra_pythonpath

    def run(self, output_dir: Path) -> VerificationResult:
        """Run pytest on *output_dir* and return a VerificationResult."""
        env = self._build_env()
        proc = subprocess.run(
            [
                sys.executable, "-m", "pytest",
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
        """Run pytest on a single file with long tracebacks and return the output.

        Used by GeneratedTestFixer to get detailed error context before asking
        the LLM to fix a file.  Returns combined stdout+stderr.
        """
        env = self._build_env()
        proc = subprocess.run(
            [
                sys.executable, "-m", "pytest",
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
        env = os.environ.copy()
        if self.extra_pythonpath:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = (
                f"{self.extra_pythonpath}:{existing}" if existing else self.extra_pythonpath
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
    """Parse combined pytest stdout+stderr into a VerificationResult.

    Uses the subprocess exit code as the authoritative pass/fail signal.
    Text parsing provides structured failure details on a best-effort basis.
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
    """Return the pytest summary line (must end with 'in N.Ns').

    Requires the ' in Xs' suffix to distinguish real summaries from
    incidental lines containing 'error' (e.g. PytestWarning garbage).
    """
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if _SUMMARY_LINE_PATTERN.search(stripped):
            return stripped
    return None


def _resolve_test_file(file_part: str, output_dir: Path) -> Path:
    """Turn a relative or absolute pytest file path into an absolute Path."""
    p = Path(file_part)
    if p.is_absolute():
        return p
    candidate = output_dir / p
    if candidate.exists():
        return candidate.resolve()
    return p.resolve()
