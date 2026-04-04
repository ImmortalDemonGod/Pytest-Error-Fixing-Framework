# branch_fixer/services/pytest/parsers/failure_parser.py
import re
from typing import List, Optional, Tuple

from branch_fixer.services.pytest.error_info import ErrorInfo

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
        """
        Parse pytest console output and extract structured ErrorInfo records for each test failure.
        
        Parameters:
            output (str): Full pytest run output text to scan for failure blocks and traceback information.
        
        Returns:
            errors (List[ErrorInfo]): A list of parsed failure records. Each ErrorInfo contains the failing test file path, the test function name (or "unknown"), the error type, the line number, the captured code snippet (traceback/context lines), and aggregated error detail lines.
        """
        errors: List[ErrorInfo] = []
        lines = output.splitlines()

        capture_traceback = False
        current_function: Optional[str] = None
        traceback_lines: list[str] = []
        error_details_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            if self._should_start_capturing(stripped):
                capture_traceback = True
                continue

            if not capture_traceback:
                continue

            if self._is_test_header(stripped):
                current_function, traceback_lines, error_details_lines = (
                    self._handle_test_header(line, stripped, current_function)
                )
                continue

            if self._is_error_detail(stripped):
                self._handle_error_detail(
                    line, stripped, traceback_lines, error_details_lines
                )
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
        Update the current test function name from a pytest header line and initialize traceback and error-detail accumulators.
        
        If the header line contains a test name, sets the current function to that name; otherwise leaves the current function unchanged and treats the header line as part of the traceback.
        
        Returns:
            A tuple of (current_function, traceback_lines, error_details_lines) where:
            - current_function: the updated test function name or the original value if no name was parsed.
            - traceback_lines: list of lines to use as the starting traceback/context (initialized with the header line).
            - error_details_lines: empty list to collect subsequent error detail lines.
        """
        test_name = self._get_test_name_from_header(stripped_line)
        if test_name:
            current_function = test_name
            traceback_lines: list[str] = [line]
            error_details_lines: list[str] = []
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
        """
        Extract a contiguous traceback/code-context block from pytest output lines.
        
        Parameters:
            lines (List[str]): The full pytest output split into lines.
            start_idx (int): Index in `lines` to begin extraction.
            end_idx (Optional[int]): Exclusive upper bound index to stop scanning; defaults to end of `lines`.
        
        Returns:
            Tuple[str, int]: A tuple containing the extracted traceback block (lines joined by '\n')
            and the index at which scanning stopped (the index of the matching location line or the first
            line after the last considered line).
        """
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
