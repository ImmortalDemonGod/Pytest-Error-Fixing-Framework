# tests/pytest/error_parser/test_failure_parser_debug.py
import snoop
from pathlib import Path

def test_parse_import_error_debug():
    """Debugging version to understand function name extraction"""
    from branch_fixer.pytest.error_parser.failure_parser import FailureParser
    
    @snoop(depth=2)
    def debug_parsing():
        parser = FailureParser()
        pytest_output = """=================================== FAILURES ===================================
___________________ TestFailureParser.test_extract_traceback ___________________

self = <test_failure_parser.TestFailureParser testMethod=test_extract_traceback>

    def setUp(self):
        \"\"\"Set up common test data\"\"\"
>       from branch_fixer.pytest.error_parser.failure_parser import FailureParser
E       ImportError: cannot import name 'FailureParser' from 'branch_fixer.pytest.error_parser.failure_parser'

tests/pytest/error_parser/test_failure_parser.py:10: ImportError"""

        # Debug: Print each line with repr to see exact whitespace
        print("\nDEBUG: Line by line output:")
        for i, line in enumerate(pytest_output.splitlines()):
            print(f"Line {i}: {repr(line)}")

        # Try different pattern variations
        patterns_to_try = [
            # Original pattern
            r"_{20,}\s+([a-zA-Z0-9_\.:]+(?:\[[^\]]+\])?)\s*_{20,}",
            # Try with less strict underscore matching
            r"_{10,}\s+([a-zA-Z0-9_\.:]+(?:\[[^\]]+\])?)\s*_{10,}",
            # Try with looser whitespace
            r"_+\s*([a-zA-Z0-9_\.:]+(?:\[[^\]]+\])?)\s*_+",
            # Try with exact pattern from original code
            r"_{20,}\s+([\w\.:]+::\w+(?:\[\w+\-\d\-\w+\])?)\s*_{20,}",
        ]

        print("\nDEBUG: Testing different patterns:")
        import re
        for i, pattern in enumerate(patterns_to_try):
            print(f"\nPattern {i + 1}: {pattern}")
            match = re.search(pattern, pytest_output)
            if match:
                print(f"MATCHED! Groups: {match.groups()}")
                print(f"Full match: {match.group(0)}")
            else:
                print("No match")

        # Parse with original parser to see what we get
        errors = parser.parse_test_failures(pytest_output)
        print(f"\nFound {len(errors)} errors")
        for error in errors:
            print("\nError details:")
            print(f"  Function name: {error.function}")
            print(f"  Error type: {error.error_type}")
            print(f"  Error details: {error.error_details}")
            print(f"  File: {error.test_file}")
            print(f"  Line number: {error.line_number}")
            print(f"  Code snippet: {error.code_snippet!r}")

        # Extract the exact failure header line for detailed inspection
        header_line = [line for line in pytest_output.splitlines() 
                      if "TestFailureParser.test_extract_traceback" in line][0]
        print(f"\nExact header line: {repr(header_line)}")
        
    debug_parsing()