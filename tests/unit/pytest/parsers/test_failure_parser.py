# tests/pytest/error_parser/test_failure_parser.py
import unittest
from typing import Optional
from pathlib import Path
import re


class TestFailureParser(unittest.TestCase):
    def setUp(self):
        """Set up common test data"""
        from branch_fixer.services.pytest.parsers.failure_parser import FailureParser
        self.parser = FailureParser()

    def test_parse_import_error(self):
        """Should parse a real pytest import error output"""
        pytest_output = """=================================== FAILURES ===================================
___________________ TestFailureParser.test_extract_traceback ___________________

self = <test_failure_parser.TestFailureParser testMethod=test_extract_traceback>

    def setUp(self):
        \"\"\"Set up common test data\"\"\"
>       from branch_fixer.services.pytest.error_parser.failure_parser import FailureParser
E       ImportError: cannot import name 'FailureParser' from 'branch_fixer.pytest.error_parser.failure_parser' (/Volumes/Totallynotaharddrive/Pytest-Error-Fixing-Framework/src/branch_fixer/pytest/error_parser/failure_parser.py)

tests/pytest/error_parser/test_failure_parser.py:10: ImportError"""

        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 1)

        error = errors[0]
        self.assertEqual(error.test_file, "tests/pytest/error_parser/test_failure_parser.py")
        self.assertEqual(error.function, "test_extract_traceback")
        self.assertEqual(error.error_type, "ImportError")
        self.assertEqual(error.line_number, "10")
        self.assertIn("cannot import name 'FailureParser'", error.error_details)
        self.assertIn("Set up common test data", error.code_snippet)

    def test_parse_full_test_session(self):
        """Should parse a complete pytest session with multiple failures"""
        pytest_output = """============================= test session starts ==============================
platform darwin -- Python 3.11.5, pytest-8.3.4, pluggy-1.5.0
rootdir: /Volumes/Totallynotaharddrive/Pytest-Error-Fixing-Framework
configfile: pytest.ini
plugins: anyio-4.6.2.post1, cov-6.0.0
collected 19 items

tests/pytest/error_parser/test_collection_parser.py ......               [ 31%]
tests/pytest/error_parser/test_failure_parser.py FFFFFFFF                [ 73%]
tests/pytest/test_error_info.py .....                                    [100%]

=================================== FAILURES ===================================
___________________ TestFailureParser.test_extract_traceback ___________________

self = <test_failure_parser.TestFailureParser testMethod=test_extract_traceback>

    def setUp(self):
        \"\"\"Set up common test data\"\"\"
>       from branch_fixer.services.pytest.error_parser.failure_parser import FailureParser
E       ImportError: cannot import name 'FailureParser' from 'branch_fixer.pytest.error_parser.failure_parser'

tests/pytest/error_parser/test_failure_parser.py:10: ImportError"""

        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 1)

        error = errors[0]
        self.assertEqual(error.test_file, "tests/pytest/error_parser/test_failure_parser.py")
        self.assertEqual(error.function, "test_extract_traceback")
        self.assertEqual(error.error_type, "ImportError")
        self.assertEqual(error.line_number, "10")

    def test_parse_assertion_error(self):
        """Should parse a standard pytest assertion error"""
        pytest_output = """=================================== FAILURES ===================================
_______________________________ test_something ________________________________

    def test_something():
>       assert 2 + 2 == 5
E       assert 4 == 5

test_example.py:42: AssertionError"""

        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 1)

        error = errors[0]
        self.assertEqual(error.test_file, "test_example.py")
        self.assertEqual(error.function, "test_something")
        self.assertEqual(error.error_type, "AssertionError")
        self.assertEqual(error.line_number, "42")
        self.assertIn("assert 4 == 5", error.error_details)
        self.assertIn("assert 2 + 2 == 5", error.code_snippet)

    def test_parse_multiple_failures(self):
        """Should parse multiple test failures from the same file"""
        pytest_output = """=================================== FAILURES ===================================
_______________________________ test_first __________________________________

    def test_first():
>       raise ValueError("Invalid value")
E       ValueError: Invalid value

test_example.py:10: ValueError
_______________________________ test_second _________________________________

    def test_second():
>       assert False, "This should fail"
E       AssertionError: This should fail
E       assert False

test_example.py:15: AssertionError"""

        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 2)

        self.assertEqual(errors[0].test_file, "test_example.py")
        self.assertEqual(errors[0].function, "test_first")
        self.assertEqual(errors[0].error_type, "ValueError")
        self.assertEqual(errors[0].line_number, "10")

        self.assertEqual(errors[1].test_file, "test_example.py")
        self.assertEqual(errors[1].function, "test_second")
        self.assertEqual(errors[1].error_type, "AssertionError")
        self.assertEqual(errors[1].line_number, "15")

    def test_parse_nested_failure(self):
        """Should parse failures with nested function calls"""
        pytest_output = """=================================== FAILURES ===================================
_______________________________ test_complex ________________________________

request = <FixtureRequest for <Function test_complex>>

    def test_complex(request):
        result = complex_operation()
>       process_result(result)

test_example.py:25: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
result = None

    def process_result(result):
>       assert result is not None, "Result cannot be None"
E       AssertionError: Result cannot be None
E       assert None is not None

test_example.py:15: AssertionError"""

        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 1)

        error = errors[0]
        self.assertEqual(error.test_file, "test_example.py")
        self.assertEqual(error.function, "test_complex")
        self.assertEqual(error.error_type, "AssertionError")
        self.assertEqual(error.line_number, "15")
        self.assertIn("Result cannot be None", error.error_details)

    def test_parse_parametrized_test_failure(self):
        """Should parse failures from parametrized tests"""
        pytest_output = """=================================== FAILURES ===================================
_________________________ test_param[1-2-expected] __________________________

a = 1, b = 2, expected = 4

    @pytest.mark.parametrize("a,b,expected", [
        (1, 2, 4),
        (2, 3, 5),
    ])
    def test_param(a, b, expected):
>       assert a + b == expected
E       assert 3 == 4
E        +  where 3 = 1 + 2

test_example.py:30: AssertionError"""

        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 1)

        error = errors[0]
        self.assertEqual(error.test_file, "test_example.py")
        self.assertEqual(error.function, "test_param[1-2-expected]")
        self.assertEqual(error.error_type, "AssertionError")
        self.assertEqual(error.line_number, "30")
        self.assertIn("assert 3 == 4", error.error_details)

    def test_process_failure_line_no_match(self):
        """Should return None for non-matching failure lines"""
        result = self.parser.process_failure_line("Not a failure line")
        self.assertIsNone(result)

    def test_supported_patterns(self):
        """Should have all required failure patterns"""
        patterns = self.parser.patterns
        self.assertIsInstance(patterns, list)
        self.assertGreater(len(patterns), 0)

        for pattern in patterns:
            self.assertIsInstance(pattern, str)
            re.compile(pattern)  # Validates regex pattern

        # Test actual failure line patterns from our own test failures
        test_lines = [
            "tests/pytest/error_parser/test_failure_parser.py::TestFailureParser::test_extract_traceback",
            "___________________ TestFailureParser.test_extract_traceback ___________________",
            "tests/pytest/error_parser/test_failure_parser.py:10: ImportError",
            "test_example.py:42: AssertionError",
            "_________________________ test_param[1-2-expected] __________________________",
        ]

        matches = 0
        for line in test_lines:
            for pattern in patterns:
                if re.search(pattern, line):
                    matches += 1
                    break
        self.assertGreater(matches, 0, "Patterns should match real pytest output formats")

    def test_get_test_name_from_header(self):
        """Should properly extract test name from header line"""
        header = "___________________ TestFailureParser.test_extract_traceback ___________________"
        test_name = self.parser._get_test_name_from_header(header)
        self.assertEqual(test_name, "test_extract_traceback")

        # Test without class prefix 
        header = "________________________________ test_something ________________________________"
        test_name = self.parser._get_test_name_from_header(header)
        self.assertEqual(test_name, "test_something")

        # Test with parametrization
        header = "_________________________ test_param[1-2-expected] __________________________"
        test_name = self.parser._get_test_name_from_header(header)
        self.assertEqual(test_name, "test_param[1-2-expected]")

    def test_extract_traceback(self):
        """Should properly extract traceback from real error output"""
        lines = [
            "self = <test_failure_parser.TestFailureParser testMethod=test_extract_traceback>",
            "",
            '    def setUp(self):',
            '        """Set up common test data"""',
            '>       from branch_fixer.services.pytest.error_parser.failure_parser import FailureParser',
            "E       ImportError: cannot import name 'FailureParser' from 'branch_fixer.pytest.error_parser.failure_parser'",
            "",
            "tests/pytest/error_parser/test_failure_parser.py:10: ImportError"
        ]

        traceback, _ = self.parser.extract_traceback(lines, 0)
        self.assertIn("Set up common test data", traceback)
        self.assertIn("from branch_fixer.services.pytest.error_parser.failure_parser import FailureParser", traceback)