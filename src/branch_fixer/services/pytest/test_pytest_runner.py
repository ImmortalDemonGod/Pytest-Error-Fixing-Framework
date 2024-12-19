import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

from _pytest.main import ExitCode
from _pytest.reports import TestReport

from branch_fixer.services.pytest.runner import PytestRunner
from branch_fixer.services.pytest.models import TestResult, SessionResult

@pytest.fixture
def mock_test_report():
    """Create a mock test report for testing."""
    report = Mock(spec=TestReport)
    report.nodeid = "test_file.py::test_function"
    report.fspath = "test_file.py"
    report.function = Mock(__name__="test_function")
    report.when = "call"
    report.outcome = "passed"
    report.passed = True
    report.failed = False
    report.skipped = False
    report.capstdout = "Test output"
    report.capstderr = ""
    report.duration = 0.1
    report.longrepr = None
    report.keywords = {}
    return report

@pytest.fixture(autouse=True)
def _ensure_clean_session(runner):
    """Ensure test session is clean before and after each test."""
    runner._current_session = None
    yield
    runner._current_session = None

@pytest.mark.asyncio
class TestPytestRunner:
    """Test suite for PytestRunner."""

    async def test_initialization(self, runner, test_suite_dir):
        """Test runner initialization and working directory."""
        assert runner.working_dir == test_suite_dir
        assert runner._current_session is None

    async def test_successful_test_execution(self, runner, test_suite_dir):
        """Test execution of a passing test with output capture."""
        # Create the test file
        test_path = test_suite_dir / "test_passing.py"
        test_path.write_text("""
def test_simple_pass():
    assert 1 + 1 == 2
    print("stdout capture")
""")
        
        # Run the test
        result = await runner.run_test(test_path=test_path)
        
        # Verify results
        assert result.exit_code == ExitCode.OK, f"Test execution failed: {result.collection_errors}"
        assert result.passed == 1, f"Expected 1 passed test, got {result.passed}"
        assert result.failed == 0, f"Expected 0 failed tests, got {result.failed}"
        assert result.total_collected == 1, f"Expected 1 collected test, got {result.total_collected}"
        
        # Check test result details
        assert len(result.test_results) == 1, "Expected one test result"
        test_result = next(iter(result.test_results.values()))
        assert test_result.passed, "Test should have passed"
        assert test_result.stdout and "stdout capture" in test_result.stdout
        assert test_result.duration > 0, "Test duration should be positive"

    async def test_fixture_handling(self, runner, test_suite_dir):
        """Test proper fixture setup/teardown and data passing."""
        test_path = test_suite_dir / "test_setup.py"
        test_path.write_text("""
import pytest

@pytest.fixture
def setup_data():
    print("Setting up")
    yield "test data"
    print("Tearing down")

def test_with_fixture(setup_data):
    assert setup_data == "test data"
""")
        
        result = await runner.run_test(test_path=test_path)
        
        assert result.exit_code == ExitCode.OK, f"Test execution failed: {result.collection_errors}"
        assert result.total_collected == 1, f"Expected 1 test, got {result.total_collected}"
        assert result.passed == 1, f"Expected 1 passed test, got {result.passed}"
        
        test_result = next(iter(result.test_results.values()))
        assert test_result.passed
        assert "Setting up" in (test_result.stdout or '')
        assert "Tearing down" in (test_result.stdout or '')

    async def test_parameterized_execution(self, runner, test_suite_dir):
        """Test handling of parameterized tests including xfail."""
        test_path = test_suite_dir / "test_params.py"
        test_path.write_text("""
import pytest

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 3),
    pytest.param(3, 5, marks=pytest.mark.xfail),
])
def test_increment(input, expected):
    assert input + 1 == expected
""")
        
        result = await runner.run_test(test_path=test_path)
        
        assert result.total_collected == 3, f"Expected 3 test cases, got {result.total_collected}"
        assert result.passed == 2, f"Expected 2 passed tests, got {result.passed}"
        assert result.xfailed == 1, f"Expected 1 xfailed test, got {result.xfailed}"
        assert result.failed == 0, f"Expected 0 failed tests, got {result.failed}"

    async def test_report_hook_handling(self, runner, mock_test_report):
        """Test pytest hook processing."""
        runner._current_session = SessionResult(
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.0,
            exit_code=ExitCode.OK
        )

        # Test all phases
        for phase in ['setup', 'call', 'teardown']:
            mock_test_report.when = phase
            runner.pytest_runtest_logreport(mock_test_report)

        result = runner._current_session.test_results[mock_test_report.nodeid]
        assert result.setup_outcome == "passed"
        assert result.call_outcome == "passed"
        assert result.teardown_outcome == "passed"
        assert result.stdout == "Test output"

    async def test_verify_fix_workflow(self, runner, test_suite_dir):
        """Test the complete fix verification workflow."""
        test_file = test_suite_dir / "test_to_fix.py"
        
        # Create failing test
        test_file.write_text("""
def test_needs_fix():
    assert False, "This test should fail"
""")
        
        # Verify initial failure
        fixed = await runner.verify_fix(test_file, "test_needs_fix")
        assert not fixed, "Test should fail initially"
        
        # Fix the test
        test_file.write_text("""
def test_needs_fix():
    assert True, "Test is fixed"
""")
        
        # Verify the fix works
        fixed = await runner.verify_fix(test_file, "test_needs_fix")
        assert fixed, "Test should pass after fix"

    def test_report_formatting(self, runner):
        """Test report generation with various scenarios."""
        session = SessionResult(
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            exit_code=ExitCode.TESTS_FAILED,
            passed=2,
            failed=1,
            skipped=1,
            xfailed=1,
            total_collected=5
        )

        failed_test = TestResult(
            nodeid="test_fail.py::test_failure",
            error_message="Expected failure",
            longrepr="Detailed traceback"
        )
        failed_test.failed = True
        session.test_results["test_fail.py::test_failure"] = failed_test

        report = runner.format_report(session)

        assert "Test Execution Report" in report
        assert "Total Tests: 5" in report
        assert "Passed: 2" in report
        assert "Failed: 1" in report
        assert "Skipped: 1" in report
        assert "XFailed: 1" in report
        assert "Expected failure" in report
        assert "Detailed traceback" in report