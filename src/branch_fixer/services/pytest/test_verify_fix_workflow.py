# src/branch_fixer/services/pytest/test_verify_fix_workflow.py
import snoop
import pytest
from pathlib import Path
from textwrap import dedent
from branch_fixer.services.pytest.runner import PytestRunner
from branch_fixer.services.pytest.models import SessionResult
from _pytest.main import ExitCode

@snoop
def test_fix_workflow(tmp_path: Path):
    """
    Test the workflow of fixing a failing test to pass using PytestRunner.

    This test performs the following steps:
    1. Creates a test file with a failing test.
    2. Runs pytest using PytestRunner to ensure the test fails.
    3. Modifies the test file to fix the test.
    4. Uses PytestRunner's verify_fix method in a subprocess to ensure the test now passes.
    """
    # Initialize the PytestRunner with the temporary directory
    runner = PytestRunner(working_dir=tmp_path)

    # Define the path for the temporary test file
    test_file = tmp_path / "test_example.py"

    # Step 1: Create a failing test
    failing_test_content = dedent("""
        def test_should_fail():
            assert False, "Intentional Failure"
    """).strip()
    test_file.write_text(failing_test_content)
    print(f"Created failing test file at {test_file}")
    print(f"Test file content:\n{test_file.read_text()}")

    # Step 2: Run pytest on the failing test and expect it to fail
    session_result = runner.run_test(test_path=test_file)

    print(f"Pytest exit code (should indicate failure): {session_result.exit_code}")

    # Assert that the test failed
    assert session_result.exit_code != ExitCode.OK, "The test was expected to fail but did not."
    assert session_result.failed == 1, f"Expected 1 failed test, got {session_result.failed}"
    assert session_result.passed == 0, f"Expected 0 passed tests, got {session_result.passed}"
    assert len(session_result.test_results) == 1, f"Expected 1 test result, got {len(session_result.test_results)}"
    test_result = session_result.test_results.get("test_example.py::test_should_fail")
    assert test_result is not None, "Test result not found."
    assert test_result.failed, "Test should have failed."
    assert test_result.error_message == "AssertionError: Intentional Failure", "Unexpected error message."

    # Step 3: Modify the test file to fix the test
    updated_test_content = dedent("""
        def test_should_fail():
            assert True, "Test is now fixed and should pass"
    """).strip()
    test_file.write_text(updated_test_content)
    print(f"Modified test file at {test_file}")
    print(f"Updated test file content:\n{test_file.read_text()}")

    # Step 4: Use verify_fix to ensure the test now passes
    # Instead of calling run_test again, which reuses state, use verify_fix which spawns a subprocess
    is_fixed = runner.verify_fix(test_file, "test_should_fail")
    print(f"Verification result (should be True): {is_fixed}")

    # Assert that the test now passes
    assert is_fixed, "The test was expected to pass but it did not."