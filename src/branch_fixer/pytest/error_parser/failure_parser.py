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
        """Extract test name from header line with underscores."""
        # The header lines look like:
        # ___________________ TestFailureParser.test_extract_traceback ___________________
        # or
        # _________________________ test_param[1-2-expected] __________________________
        # We want only the test function name.
        if line.startswith("_") and line.endswith("_"):
            content = line.strip("_ ")
            if content:
                # If there's a dot, we might have ClassName.test_name
                # Split by dot and take the last segment as test name
                if "." in content:
                    return content.split(".")[-1]
                return content
        return None

    def parse_test_failures(self, output: str) -> List[ErrorInfo]:
        """Parse pytest output and extract test failures."""
        errors: List[ErrorInfo] = []
        lines = output.splitlines()

        capture_traceback = False
        current_function: Optional[str] = None
        traceback_lines = []
        error_details_lines = []
        current_error = None

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Start capturing after seeing FAILURES
            if "FAILURES" in line:
                capture_traceback = True
                i += 1
                continue

            if capture_traceback:
                # Check for test header lines
                if stripped.startswith("_") and stripped.endswith("_"):
                    # New test block
                    current_function = self._get_test_name_from_header(stripped)
                    # Reset accumulators for this new test's traceback
                    traceback_lines = [line]
                    error_details_lines = []
                    current_error = None
                else:
                    # Process lines within a test block
                    if stripped.startswith("E "):
                        # Error detail line
                        error_line = stripped[2:].strip()
                        traceback_lines.append(line)
                        error_details_lines.append(error_line)
                    elif stripped.startswith(">"):
                        # Line indicator for error location
                        traceback_lines.append(line)
                    else:
                        # Check if this line contains file:line:error pattern
                        match = re.search(PATTERNS[0], line)
                        if match:
                            # We found a line indicating the file, line and error type
                            test_file = match.group(1)
                            line_number = match.group(2)
                            error_type = match.group(3)

                            # Create the error entry now that we have all info
                            current_error = ErrorInfo(
                                test_file=test_file,
                                function=current_function or "unknown",
                                error_type=error_type,
                                error_details="\n".join(error_details_lines),
                                line_number=line_number,
                                code_snippet="\n".join(traceback_lines)
                            )
                            errors.append(current_error)
                        else:
                            # Just a regular traceback line, include it
                            # (only if not underscores)
                            if stripped and not stripped.startswith("_"):
                                traceback_lines.append(line)

            i += 1

        return errors

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
                line_number=match.group(2)
            )
        return None

    def extract_traceback(self, lines: List[str], start_idx: int, end_idx: Optional[int] = None) -> Tuple[str, int]:
        """Extract traceback information from pytest output lines."""
        if end_idx is None:
            end_idx = len(lines)

        traceback_lines = []
        i = start_idx

        # We'll gather lines until we hit a file:line:error pattern or run out of lines
        while i < end_idx:
            stripped = lines[i].strip()
            if stripped and not stripped.startswith("_"):
                traceback_lines.append(lines[i])

            if re.search(PATTERNS[0], lines[i]):
                # Once we hit the file:line:error line, we stop
                return ("\n".join(traceback_lines), i)

            i += 1

        return ("\n".join(traceback_lines), i)