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
        Number of failing / erroring tests.
    failures:
        Structured info for each failing test.
    raw_output:
        Full combined stdout+stderr from pytest (for debugging).
    """

    output_dir: Path
    passed: int = 0
    failed: int = 0
    failures: List[TestFailure] = field(default_factory=list)
    raw_output: str = ""

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and len(self.failures) == 0


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
        result = subprocess.run(
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
        combined = result.stdout + result.stderr
        return parse_pytest_output(combined, output_dir)

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

# Matches: "FAILED path/to/test_foo.py::TestClass::test_method - Error msg"
_FAILED_LINE = re.compile(r"^FAILED\s+(.+?)::(.+?)\s+-\s+(.*)$")

# Matches the summary line: "3 failed, 2 passed in 0.4s"  or "1 failed in 0.1s"
_SUMMARY_LINE = re.compile(r"(\d+)\s+failed", re.IGNORECASE)
_PASSED_LINE = re.compile(r"(\d+)\s+passed", re.IGNORECASE)


def parse_pytest_output(output: str, output_dir: Path) -> VerificationResult:
    """Parse combined pytest stdout+stderr into a VerificationResult.

    Extracts:
    - Failing test IDs and their one-line error messages from FAILED lines.
    - Pass/fail counts from the summary line.
    """
    failures: list[TestFailure] = []
    passed = 0
    failed = 0

    for line in output.splitlines():
        m = _FAILED_LINE.match(line.strip())
        if m:
            file_part, test_id_part, error_msg = m.group(1), m.group(2), m.group(3)
            test_file = _resolve_test_file(file_part, output_dir)
            failures.append(
                TestFailure(
                    test_file=test_file,
                    test_id=test_id_part.strip(),
                    error_output=error_msg.strip(),
                )
            )

    # Count from summary line (more reliable than counting FAILED lines when
    # collection errors occur)
    summary = _find_summary_line(output)
    if summary:
        failed_m = _SUMMARY_LINE.search(summary)
        passed_m = _PASSED_LINE.search(summary)
        failed = int(failed_m.group(1)) if failed_m else len(failures)
        passed = int(passed_m.group(1)) if passed_m else 0
    else:
        failed = len(failures)

    return VerificationResult(
        output_dir=output_dir,
        passed=passed,
        failed=failed,
        failures=failures,
        raw_output=output,
    )


def _find_summary_line(output: str) -> Optional[str]:
    """Return the last line that looks like a pytest summary."""
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if stripped and ("passed" in stripped or "failed" in stripped or "error" in stripped):
            return stripped
    return None


def _resolve_test_file(file_part: str, output_dir: Path) -> Path:
    """Turn a relative or absolute pytest file path into an absolute Path."""
    p = Path(file_part)
    if p.is_absolute():
        return p
    # Try relative to output_dir first
    candidate = output_dir / p
    if candidate.exists():
        return candidate.resolve()
    return p.resolve()
