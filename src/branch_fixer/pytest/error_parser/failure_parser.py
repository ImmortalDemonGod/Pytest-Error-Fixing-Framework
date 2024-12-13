# src/branch_fixer/pytest/error_parser/failure_parser.py
import re
from typing import List, Optional, Tuple

from branch_fixer.pytest.error_info import ErrorInfo

FAILURE_PATTERNS = [
    # Pattern for standard pytest failure headers
    r"_{20,}\s+(\w+::\w+|\w+)(?:\[\w+\])?\s+_{20,}",
    # Pattern for file paths with line numbers and error types
    r"([\w\/\._-]+):(\d+):\s+(\w+(?:\.\w+)*Error)",
    # Pattern for failures in test collection
    r"FAILED\s+([\w\/\._-]+)::([\w_\[\]\-]+)\s*(?:-\s*)?([\w\.]+Error)?:?\s*(.*?)$",
    # Pattern for simple failures without dash
    r"FAILED\s+([\w\/\._-]+)::([\w_\[\]\-]+)\s*$",
    # Pattern for test IDs in pytest format
    r"([\w\/\._-]+)::(\w+)::\w+(?:\[\w+\])?$",
]


class FailureParser:
    """Parses pytest test failures and extracts error information."""

    @property
    def patterns(self) -> List[str]:
        """Returns list of failure patterns used for matching."""
        return FAILURE_PATTERNS

    def parse_test_failures(self, output: str) -> List[ErrorInfo]:
        """
        Parse pytest output and extract test failures.

        Args:
            output: Complete pytest output string

        Returns:
            List of ErrorInfo objects representing test failures
        """
        errors = []
        lines = output.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and session info
            if not line or "test session starts" in line:
                i += 1
                continue

            # Look for failure sections
            if "FAILURES" in line:
                i += 1
                while i < len(lines):
                    error = self.process_failure_line(lines[i].strip())
                    if error:
                        # Extract traceback for this error
                        traceback, end_idx = self.extract_traceback(lines, i + 1)
                        i = end_idx

                        # Update error with traceback info
                        if traceback:
                            error.code_snippet = traceback

                            # Try to extract better error details from traceback
                            for line in traceback.splitlines():
                                if line.startswith("E       "):
                                    error.error_details = line.replace(
                                        "E       ", ""
                                    ).strip()
                                    break

                        errors.append(error)
                    i += 1
            else:
                i += 1

        return errors

    def process_failure_line(self, line: str) -> Optional[ErrorInfo]:
        """
        Process a single line to extract error information.

        Args:
            line: Single line from pytest output

        Returns:
            ErrorInfo object if line contains error info, None otherwise
        """
        # Skip empty or irrelevant lines
        if (
            not line
            or "collected" in line
            or "[" in line
            and "]" in line
            and "%" in line
        ):
            return None

        # Try all patterns
        for pattern in self.patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                # Handle different pattern matches
                if len(groups) >= 2:
                    # Extract file and function name
                    test_file = groups[0]

                    # For file:line:error pattern
                    if len(groups) >= 3 and groups[1].isdigit():
                        return ErrorInfo(
                            test_file=test_file,
                            function="unknown",  # Function name will be updated from traceback
                            error_type=groups[2],
                            error_details="",
                            line_number=groups[1],
                        )

                    # For failure header pattern
                    else:
                        function = groups[1]
                        error_type = groups[2] if len(groups) > 2 else "Error"
                        error_details = groups[3] if len(groups) > 3 else ""

                        return ErrorInfo(
                            test_file=test_file,
                            function=function,
                            error_type=error_type,
                            error_details=error_details,
                        )

        return None

    def extract_traceback(self, lines: List[str], start_idx: int) -> Tuple[str, int]:
        """
        Extract traceback information from pytest output lines.

        Args:
            lines: List of output lines
            start_idx: Starting index to look for traceback

        Returns:
            Tuple of (traceback string, ending index)
        """
        traceback_lines = []
        i = start_idx

        while i < len(lines):
            line = lines[i].strip()

            # Stop at empty lines after we've started collecting
            if not line and traceback_lines:
                break

            # Stop at new test failure section
            if line and ("_" * 20) in line:
                break

            # Collect relevant lines
            if line and (
                line.startswith(">")
                or line.startswith("E")
                or line.startswith("def ")
                or ".py" in line
                or "self = " in line
            ):
                traceback_lines.append(line)

            i += 1

        # If we found a traceback, include the last line with file:line info
        if traceback_lines and i < len(lines):
            next_line = lines[i].strip()
            if ".py:" in next_line and ":" in next_line:
                traceback_lines.append(next_line)
                i += 1

        return "\n".join(traceback_lines), i - 1 if traceback_lines else start_idx
