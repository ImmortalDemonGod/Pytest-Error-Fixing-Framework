# tests/pytest/error_parser/test_collection_parser.py
import unittest
from pathlib import Path

class TestCollectionParser(unittest.TestCase):
    def setUp(self):
        """Set up common test data"""
        from branch_fixer.services.pytest.error_processor import CollectionParser
        self.parser = CollectionParser()

    def test_parse_collection_errors_single_error(self):
        """Should parse a single collection error from pytest output"""
        pytest_output = """
        ============================= test session starts ==============================
        platform darwin -- Python 3.9.7, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
        rootdir: /Users/dev/project
        plugins: hypothesis-6.75.3, cov-4.1.0, reportlog-0.3.0
        collected 0 items / 1 error
        
        ==================================== ERRORS ====================================
        ERROR collecting test_example.py
        imported module 'test_example' has __file__ attribute:
        /path/to/venv/site-packages/test_example.py
        which is not the same as the test file we want to collect:
        /Users/dev/project/tests/test_example.py
        """
        
        errors = self.parser.parse_collection_errors(pytest_output)
        
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.test_file, "test_example.py")
        self.assertEqual(error.function, "collection")
        self.assertEqual(error.error_type, "CollectionError")
        self.assertIn("Import path mismatch", error.error_details)

    def test_parse_collection_errors_multiple_errors(self):
        """Should parse multiple collection errors from pytest output"""
        pytest_output = """
        ============================= test session starts ==============================
        platform darwin -- Python 3.9.7, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
        rootdir: /Users/dev/project
        collected 0 items / 2 errors
        
        ==================================== ERRORS ====================================
        ERROR collecting test_one.py
        imported module 'test_one' has __file__ attribute:
        /path/to/one/test_one.py
        which is not the same as the test file we want to collect:
        /Users/dev/project/tests/test_one.py
        
        ERROR collecting test_two.py
        imported module 'test_two' has __file__ attribute:
        /path/to/two/test_two.py
        which is not the same as the test file we want to collect:
        /Users/dev/project/tests/test_two.py
        """
        
        errors = self.parser.parse_collection_errors(pytest_output)
        
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0].test_file, "test_one.py")
        self.assertEqual(errors[1].test_file, "test_two.py")

    def test_parse_collection_errors_no_errors(self):
        """Should return empty list when no collection errors exist"""
        pytest_output = """
        ============================= test session starts ==============================
        platform darwin -- Python 3.9.7, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
        rootdir: /Users/dev/project
        collected 5 items
        
        test_example.py .....                                                  [100%]
        """
        
        errors = self.parser.parse_collection_errors(pytest_output)
        self.assertEqual(len(errors), 0)

    def test_extract_collection_match(self):
        """Should extract ErrorInfo from regex match"""
        import re
        from branch_fixer.services.pytest.error_parser.collection_parser import COLLECTION_PATTERN
        
        error_text = """
        ERROR collecting test_example.py
        imported module 'test_example' has __file__ attribute:
        /path/to/venv/site-packages/test_example.py
        which is not the same as the test file we want to collect:
        /Users/dev/project/tests/test_example.py
        """
        
        match = re.search(COLLECTION_PATTERN, error_text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match, "Pattern should match the error text")
        
        error = self.parser.extract_collection_match(match)
        self.assertEqual(error.test_file, "test_example.py")
        self.assertEqual(error.function, "collection")
        self.assertEqual(error.error_type, "CollectionError")
        self.assertIn("Import path mismatch", error.error_details)

    def test_validate_collection_error(self):
        """Should validate collection error details"""
        from branch_fixer.services.pytest.error_info import ErrorInfo
        
        error = ErrorInfo(
            test_file="test_example.py",
            function="collection",
            error_type="CollectionError",
            error_details="Import path mismatch",
        )
        
        self.assertTrue(self.parser.validate_collection_error(error))

    def test_validate_collection_error_invalid(self):
        """Should reject invalid collection errors"""
        from branch_fixer.services.pytest.error_info import ErrorInfo
        
        # Wrong function name
        error1 = ErrorInfo(
            test_file="test_example.py",
            function="test_something",
            error_type="CollectionError",
            error_details="Import path mismatch",
        )
        self.assertFalse(self.parser.validate_collection_error(error1))
        
        # Wrong error type
        error2 = ErrorInfo(
            test_file="test_example.py",
            function="collection",
            error_type="AssertionError",
            error_details="Import path mismatch",
        )
        self.assertFalse(self.parser.validate_collection_error(error2))