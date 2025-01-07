import unittest
from textwrap import dedent

from branch_fixer.services.pytest.error_info import ErrorInfo
from branch_fixer.services.pytest.parsers.unified_error_parser import (
    UnifiedErrorParser,
    parse_pytest_output,
)


class TestUnifiedErrorParser(unittest.TestCase):
    def setUp(self):
        self.parser = UnifiedErrorParser()

    def test_no_errors(self):
        """Should return an empty list when there are no collection or failure errors."""
        pytest_output = "collected 5 items\n\n tests/example_test.py .....  [100%]"
        results = self.parser.parse_pytest_output(pytest_output)
        self.assertEqual(len(results), 0, "Expected no errors parsed.")

    def test_collection_error_only(self):
        """Should parse only collection errors and return them as ErrorInfo."""
        pytest_output = dedent("""
            ============================== test session starts ==============================
            collected 0 items / 1 error

            ================================ ERRORS ====================================
            ERROR collecting test_example.py
            imported module 'test_example' has __file__ attribute:
            /path/to/venv/site-packages/test_example.py
            which is not the same as the test file we want to collect:
            /Users/dev/project/tests/test_example.py
        """)
        results = self.parser.parse_pytest_output(pytest_output)
        self.assertEqual(len(results), 1)
        err = results[0]
        self.assertIsInstance(err, ErrorInfo)
        self.assertEqual(err.function, "collection")
        self.assertEqual(err.error_type, "CollectionError")

    def test_failure_errors_only(self):
        """Should parse only standard test failures."""
        pytest_output = dedent("""
            ============================== test session starts ==============================
            ============================= FAILURES ========================================
            ___________________ test_something ___________________
            
                def test_something():
            >       assert 2 + 2 == 5
            E       assert 4 == 5
            
            test_example.py:42: AssertionError
        """)
        results = self.parser.parse_pytest_output(pytest_output)
        self.assertEqual(len(results), 1)
        err = results[0]
        self.assertEqual(err.test_file, "test_example.py")
        self.assertEqual(err.function, "test_something")
        self.assertEqual(err.error_type, "AssertionError")
        self.assertIn("assert 4 == 5", err.error_details)
        self.assertEqual(err.line_number, "42")

    def test_mixed_collection_and_failures(self):
        """Should parse both collection errors and standard failures from the same output."""
        pytest_output = dedent("""
            collected 0 items / 1 error
            
            ================================ ERRORS ====================================
            ERROR collecting test_one.py
            imported module 'test_one' has __file__ attribute:
            /path/to/venv/site-packages/test_one.py
            which is not the same as the test file we want to collect:
            /Users/dev/project/tests/test_one.py

            ============================= FAILURES ========================================
            ___________________ test_another ___________________

                def test_another():
            >       assert False, "This fails"
            E       AssertionError: This fails
            E       assert False

            test_two.py:37: AssertionError
        """)
        results = self.parser.parse_pytest_output(pytest_output)
        self.assertEqual(len(results), 2)

        # Check collection error
        coll_err = next(e for e in results if e.function == "collection")
        self.assertEqual(coll_err.error_type, "CollectionError")
        self.assertIn("Import path mismatch", coll_err.error_details)

        # Check standard failure
        fail_err = next(e for e in results if e.function != "collection")
        self.assertEqual(fail_err.test_file, "test_two.py")
        self.assertEqual(fail_err.error_type, "AssertionError")
        self.assertEqual(fail_err.line_number, "37")

    def test_shortcut_function(self):
        """Should parse output using the top-level parse_pytest_output function."""
        out = "============================= FAILURES =============================\nE   ValueError: Something"
        # This won't parse a real file, but tests we can call parse_pytest_output directly
        results = parse_pytest_output(out)
        # We expect it to either find no recognized pattern or parse a partial failure
        # This is just an example that the convenience function is accessible
        self.assertIsInstance(results, list)


if __name__ == "__main__":
    unittest.main()
