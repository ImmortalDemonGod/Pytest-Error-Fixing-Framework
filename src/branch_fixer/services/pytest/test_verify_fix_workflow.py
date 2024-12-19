# src/branch_fixer/services/pytest/test_verify_fix_workflow.py
import pytest
from textwrap import dedent
from pathlib import Path
import snoop


class TestVerifyFixWorkflow:
    """Test the complete fix verification workflow."""

    @snoop.watching(['test_file.read_text()', 'fixed'])
    def test_verify_fix_workflow(self, runner, test_suite_dir):
        """
        Test the complete fix verification workflow.

        This test verifies that a failing test can be fixed and subsequently passes.
        """
        test_file = test_suite_dir / "test_to_fix.py"

        # First version - failing test with proper 4-space indentation
        test_file_content_initial = dedent("""
            def test_needs_fix():
                assert False, "This test should fail"
        """).lstrip()
        test_file.write_text(test_file_content_initial)
        print(f"Initial test file content:\n{test_file.read_text()}")

        # Verify that the test initially fails
        fixed = runner.verify_fix(test_file, "test_needs_fix")
        assert not fixed, "Test should fail initially"

        # Second version - passing test with proper 4-space indentation  
        test_file_content_fixed = dedent("""
            def test_needs_fix():
                assert True, "Test is fixed"
        """).lstrip()
        test_file.write_text(test_file_content_fixed)
        print(f"Updated test file content:\n{test_file.read_text()}")

        # Verify that the test passes after the fix
        fixed = runner.verify_fix(test_file, "test_needs_fix")
        assert fixed, "Test should pass after fix"