# tests/pytest/test_error_info.py
import unittest
from pathlib import Path

class TestErrorInfo(unittest.TestCase):
    def setUp(self):
        """Set up common test data"""
        from branch_fixer.pytest.error_info import ErrorInfo
        self.error_info = ErrorInfo(
            test_file="tests/test_example.py",
            function="test_something",
            error_type="AssertionError", 
            error_details="Expected 5 but got 4",
            line_number="42",
            code_snippet="def test_something():\n    assert 2 + 2 == 5"
        )

    def test_file_path_property(self):
        """file_path property should return a Path object"""
        self.assertIsInstance(self.error_info.file_path, Path)
        self.assertEqual(self.error_info.file_path, Path("tests/test_example.py"))

    def test_formatted_error_property(self):
        """formatted_error should combine error type and details"""
        expected = "AssertionError: Expected 5 but got 4"
        self.assertEqual(self.error_info.formatted_error, expected)

    def test_has_traceback_with_snippet(self):
        """has_traceback should return True when code_snippet exists"""
        self.assertTrue(self.error_info.has_traceback)

    def test_has_traceback_without_snippet(self):
        """has_traceback should return False when code_snippet is empty"""
        from branch_fixer.pytest.error_info import ErrorInfo
        error_info = ErrorInfo(
            test_file="tests/test_example.py",
            function="test_something",
            error_type="AssertionError",
            error_details="Error occurred"
        )
        self.assertFalse(error_info.has_traceback)

    def test_update_snippet(self):
        """update_snippet should update the code snippet with proper formatting"""
        new_snippet = "    def test_something():\n        assert True"
        self.error_info.update_snippet(new_snippet)
        self.assertEqual(self.error_info.code_snippet, new_snippet)