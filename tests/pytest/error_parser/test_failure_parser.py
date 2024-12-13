# tests/pytest/error_parser/test_failure_parser.py
import unittest
from typing import Optional
from pathlib import Path


class TestFailureParser(unittest.TestCase):
    def setUp(self):
        """Set up common test data"""
        from branch_fixer.pytest.error_parser.failure_parser import FailureParser
        self.parser = FailureParser()

    def test_parse_standard_failure(self):
        """Should parse a standard pytest failure with assertion error"""
        pytest_output = """
        ============================= test session starts ==============================
        platform darwin -- Python 3.9.7, pytest-6.2.4
        rootdir: /Users/dev/project
        collected 1 item
        
        test_example.py F                                                      [100%]
        
        =================================== FAILURES ==================================
        _______________________________ test_something ________________________________
        
        def test_something():
        >       assert 2 + 2 == 5
        E       assert 4 == 5
        
        test_example.py:42: AssertionError
        """
        
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
        pytest_output = """
        ============================= test session starts ==============================
        platform darwin -- Python 3.9.7, pytest-6.2.4
        rootdir: /Users/dev/project
        collected 2 items
        
        test_example.py FF                                                     [100%]
        
        =================================== FAILURES ==================================
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
        
        test_example.py:15: AssertionError
        """
        
        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 2)
        
        # Check first error
        self.assertEqual(errors[0].test_file, "test_example.py")
        self.assertEqual(errors[0].function, "test_first")
        self.assertEqual(errors[0].error_type, "ValueError")
        self.assertEqual(errors[0].line_number, "10")
        
        # Check second error
        self.assertEqual(errors[1].test_file, "test_example.py")
        self.assertEqual(errors[1].function, "test_second")
        self.assertEqual(errors[1].error_type, "AssertionError")
        self.assertEqual(errors[1].line_number, "15")

    def test_parse_failure_with_complex_traceback(self):
        """Should parse failures with multi-line tracebacks and nested function calls"""
        pytest_output = """
        =================================== FAILURES ==================================
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
        
        test_example.py:15: AssertionError
        """
        
        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 1)
        
        error = errors[0]
        self.assertEqual(error.test_file, "test_example.py")
        self.assertEqual(error.function, "test_complex")
        self.assertEqual(error.error_type, "AssertionError")
        self.assertEqual(error.line_number, "15")
        self.assertIn("Result cannot be None", error.error_details)
        self.assertIn("def process_result(result):", error.code_snippet)

    def test_parse_parametrized_test_failure(self):
        """Should parse failures from parametrized tests"""
        pytest_output = """
        =================================== FAILURES ==================================
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
        
        test_example.py:30: AssertionError
        """
        
        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 1)
        
        error = errors[0]
        self.assertEqual(error.test_file, "test_example.py")
        self.assertEqual(error.function, "test_param[1-2-expected]")
        self.assertEqual(error.error_type, "AssertionError")
        self.assertEqual(error.line_number, "30")
        self.assertIn("assert 3 == 4", error.error_details)

    def test_parse_failure_with_custom_exception(self):
        """Should parse failures with custom exceptions"""
        pytest_output = """
        =================================== FAILURES ==================================
        _______________________________ test_custom _________________________________
        
            def test_custom():
        >       raise CustomError("Something went wrong")
        E       custom_module.exceptions.CustomError: Something went wrong
        
        test_example.py:50: CustomError
        """
        
        errors = self.parser.parse_test_failures(pytest_output)
        self.assertEqual(len(errors), 1)
        
        error = errors[0]
        self.assertEqual(error.error_type, "CustomError")
        self.assertEqual(error.error_details, "Something went wrong")

    def test_extract_traceback(self):
        """Should properly extract traceback information"""
        lines = [
            "def test_function():",
            ">   assert True is False",
            "E   assert True is False",
            "",
            "test_file.py:42: AssertionError"
        ]
        
        traceback, end_idx = self.parser.extract_traceback(lines, 0)
        self.assertEqual(end_idx, 4)
        self.assertIn("def test_function():", traceback)
        self.assertIn("assert True is False", traceback)

    def test_process_failure_line_no_match(self):
        """Should return None for non-matching failure lines"""
        result = self.parser.process_failure_line("Not a failure line")
        self.assertIsNone(result)

    def test_supported_patterns(self):
        """Should have all required failure patterns"""
        patterns = self.parser.patterns
        self.assertIsInstance(patterns, list)
        self.assertGreater(len(patterns), 0)
        # Each pattern should be a valid regex string
        import re
        for pattern in patterns:
            self.assertIsInstance(pattern, str)
            # This will raise re.error if pattern is invalid
            re.compile(pattern)