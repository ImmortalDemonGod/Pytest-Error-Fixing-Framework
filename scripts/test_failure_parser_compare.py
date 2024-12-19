# tests/pytest/error_parser/test_failure_parser_compare.py
import snoop
from pathlib import Path
import re

def test_compare_parsers():
    """Compare original working parser with new implementation"""
    from branch_fixer.services.pytest.error_parser.failure_parser import FailureParser
    from branch_fixer.services.pytest.error_info import ErrorInfo

    @snoop
    def debug_parsing():
        # The example test failure
        pytest_output = """=================================== FAILURES ===================================
___________________ TestFailureParser.test_extract_traceback ___________________

self = <test_failure_parser.TestFailureParser testMethod=test_extract_traceback>

    def setUp(self):
        \"\"\"Set up common test data\"\"\"
>       from branch_fixer.services.pytest.error_parser.failure_parser import FailureParser
E       ImportError: cannot import name 'FailureParser' from 'branch_fixer.pytest.error_parser.failure_parser'

tests/pytest/error_parser/test_failure_parser.py:10: ImportError"""

        print("\nOriginal working patterns:")
        original_patterns = [
            # Collection error pattern
            r"ERROR collecting (.*?)\s*\n.*?imported module.*?__file__ attribute:.*?\n.*?(test_\w+).*?\n",
            # Standard pytest failure pattern - this is the one we want for this case
            r"FAILED (.*?)::(.*?) - (.*?): (.*?)$",
            # Pattern for simple failures without dash
            r"FAILED (.*?)::(.*?)\s*$",
            # Pattern for errors with full path 
            r"(?:FAILED|ERROR) ([\w\/\._-]+)::([\w_]+)(?:\[(.*?)\])?\s*(?:-\s*)?(.*?)$",
            # Pattern for assertion errors
            r"(?:.*?)::(\w+)\s+-\s+(\w+Error):\s+(.+?)$",
        ]

        print("Testing each original pattern:")
        for i, pattern in enumerate(original_patterns):
            print(f"\nPattern {i + 1}: {pattern}")
            match = re.search(pattern, pytest_output)
            if match:
                print(f"MATCHED! Groups: {match.groups()}")

        # Now check if the header line matches any pattern
        header_line = "___________________ TestFailureParser.test_extract_traceback ___________________"
        print("\nTesting patterns against header line:")
        for i, pattern in enumerate(original_patterns):
            print(f"\nPattern {i + 1}:")
            match = re.search(pattern, header_line)
            if match:
                print(f"MATCHED! Groups: {match.groups()}")

        # Now parse with new implementation
        parser = FailureParser()
        print("\nNew implementation results:")
        errors = parser.parse_test_failures(pytest_output)
        for error in errors:
            print(f"\nError details:")
            print(f"  Function: {error.function}")
            print(f"  File: {error.test_file}")
            print(f"  Type: {error.error_type}")
            print(f"  Details: {error.error_details}")
            print(f"  Line: {error.line_number}")
            print(f"  Snippet: {error.code_snippet!r}")

        # Original working code capture strategy
        print("\nSimulating original capture strategy:")
        current_error = None
        capture_traceback = False
        traceback_lines = []

        for line in pytest_output.splitlines():
            print(f"\nProcessing line: {line!r}")
            if "FAILURES" in line or "ERRORS" in line:
                print("Found FAILURES/ERRORS section, starting capture")
                capture_traceback = True
                continue

            if capture_traceback and not any(re.search(p, line) for p in original_patterns):
                if line.startswith("E       "):
                    error_line = line.replace("E       ", "").strip()
                    traceback_lines.append(error_line)
                    print(f"Added error line: {error_line}")
                elif line.strip() and line[0].isalpha():  # New section started
                    print("Found new section")
                    capture_traceback = False
                    if current_error and traceback_lines:
                        print(f"Setting traceback for error: {traceback_lines}")
                    traceback_lines = []

    debug_parsing()
    