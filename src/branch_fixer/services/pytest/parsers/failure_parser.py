# src/branch_fixer/pytest/error_parser/failure_parser.py
import re
from typing import List, Optional, Tuple

from branch_fixer.pytest.error_info import ErrorInfo

PATTERNS = [
    # File path with line number and error type
    r"([\w\/\._-]+):(\d+):\s+([\w\.]+Error)",
]


class FailureParser:
    """Parses pytest test failures and extracts error information."""

    @property
    def patterns(self) -> List[str]:
        """Returns list of failure patterns used for matching."""
        return PATTERNS

    def _get_test_name_from_header(self, line: str) -> Optional[str]:
        """Extract test name from a header line with underscores."""
        if not (line.startswith("_") and line.endswith("_")):
            return None

        content = line.strip("_ ").strip()
        if not content:
            return None

        return content.split(".")[-1] if "." in content else content

    def parse_test_failures(self, output: str) -> List[ErrorInfo]:
        """Parse pytest output and extract test failures."""
        errors: List[ErrorInfo] = []
        lines = output.splitlines()

        capture_traceback = False
        current_function: Optional[str] = None
        traceback_lines = []
        error_details_lines = []

        for line in lines:
            stripped = line.strip()

            if self._should_start_capturing(stripped):
                capture_traceback = True
                continue

            if not capture_traceback:
                continue

            if self._is_test_header(stripped):
                current_function, traceback_lines, error_details_lines = self._handle_test_header(
                    line, stripped, current_function
                )
                continue

            if self._is_error_detail(stripped):
                self._handle_error_detail(line, stripped, traceback_lines, error_details_lines)
                continue

            if self._is_failing_line_indicator(stripped):
                traceback_lines.append(line)
                continue

            error_info = self._process_line_for_error(
                line, current_function, traceback_lines, error_details_lines
            )
            if error_info:
                errors.append(error_info)

        return errors

    def _should_start_capturing(self, stripped_line: str) -> bool:
        """Determine if traceback capturing should start."""
        return "FAILURES" in stripped_line

    def _handle_test_header(
        self, line: str, stripped_line: str, current_function: Optional[str]
    ) -> Tuple[Optional[str], List[str], List[str]]:
        """
        Handle lines that are test headers.

        Returns the updated current function name, reset traceback lines, and reset error details lines.
        """
        test_name = self._get_test_name_from_header(stripped_line)
        if test_name:
            current_function = test_name
            traceback_lines = [line]
            error_details_lines = []
        else:
            # Underscore line isn't a test name, treat as traceback line
            # Do not modify current_function
            traceback_lines = [line]
            error_details_lines = []
        return current_function, traceback_lines, error_details_lines

    def _handle_error_detail(
        self,
        line: str,
        stripped_line: str,
        traceback_lines: List[str],
        error_details_lines: List[str],
    ) -> None:
        """
        Handle lines that contain error details.

        Updates traceback_lines and error_details_lines accordingly.
        """
        error_line = stripped_line[2:].strip()
        traceback_lines.append(line)
        error_details_lines.append(error_line)

    def _is_test_header(self, stripped_line: str) -> bool:
        """Check if the line is a test header."""
        return stripped_line.startswith("_") and stripped_line.endswith("_")

    def _is_error_detail(self, stripped_line: str) -> bool:
        """Check if the line contains error details."""
        return stripped_line.startswith("E ")

    def _is_failing_line_indicator(self, stripped_line: str) -> bool:
        """Check if the line indicates a failing line."""
        return stripped_line.startswith(">")

    def _process_line_for_error(
        self,
        line: str,
        current_function: Optional[str],
        traceback_lines: List[str],
        error_details_lines: List[str],
    ) -> Optional[ErrorInfo]:
        """Process a line to extract error information."""
        match = re.search(PATTERNS[0], line)
        if not match:
            if line.strip() and not line.strip().startswith("_"):
                traceback_lines.append(line)
            return None

        test_file, line_number, error_type = match.groups()
        return ErrorInfo(
            test_file=test_file,
            function=current_function or "unknown",
            error_type=error_type,
            error_details="\n".join(error_details_lines),
            line_number=line_number,
            code_snippet="\n".join(traceback_lines),
        )

    def process_failure_line(self, line: str) -> Optional[ErrorInfo]:
        """Process a single line to extract error information."""
        if not line:
            return None

        match = re.search(PATTERNS[0], line)
        if match:
            return ErrorInfo(
                test_file=match.group(1),
                function="unknown",
                error_type=match.group(3),
                error_details="",
                line_number=match.group(2),
            )
        return None

    def extract_traceback(
        self, lines: List[str], start_idx: int, end_idx: Optional[int] = None
    ) -> Tuple[str, int]:
        """Extract traceback information from pytest output lines."""
        end_idx = end_idx or len(lines)
        traceback_lines = []
        i = start_idx

        while i < end_idx:
            stripped = lines[i].strip()
            if stripped and not stripped.startswith("_"):
                traceback_lines.append(lines[i])

            if re.search(PATTERNS[0], lines[i]):
                break

            i += 1

        return ("\n".join(traceback_lines), i)