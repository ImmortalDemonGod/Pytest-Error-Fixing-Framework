"""Tests for PytestRunner — argument building, result formatting, verify_fix subprocess."""
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from _pytest.main import ExitCode

from branch_fixer.services.pytest.models import SessionResult, TestResult
from branch_fixer.services.pytest.runner import PytestRunner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    return PytestRunner(working_dir=Path("/project"))


def make_session() -> SessionResult:
    now = datetime.now()
    return SessionResult(start_time=now, end_time=now, duration=0.0, exit_code=ExitCode.OK)


def make_test_result(nodeid: str, passed: bool = False, failed: bool = False) -> TestResult:
    return TestResult(
        nodeid=nodeid,
        test_file=Path("tests/test_foo.py"),
        test_function="test_foo",
        passed=passed,
        failed=failed,
    )


# ---------------------------------------------------------------------------
# build_pytest_args
# ---------------------------------------------------------------------------

class TestBuildPytestArgs:
    def test_includes_override_ini(self, runner):
        args = runner.build_pytest_args()
        assert "--override-ini=addopts=" in args

    def test_includes_no_terminal(self, runner):
        args = runner.build_pytest_args()
        assert "no:terminal" in args

    def test_includes_rootdir(self, runner):
        args = runner.build_pytest_args()
        assert "--rootdir" in args
        assert "/project" in args

    def test_no_test_path_no_path_appended(self, runner):
        args = runner.build_pytest_args()
        # Should not contain a bare path segment
        assert not any(a.endswith(".py") for a in args)

    def test_test_path_without_function(self, runner):
        args = runner.build_pytest_args(test_path=Path("tests/test_foo.py"))
        assert "tests/test_foo.py" in args

    def test_test_path_with_function(self, runner):
        args = runner.build_pytest_args(
            test_path=Path("tests/test_foo.py"), test_function="test_bar"
        )
        assert "tests/test_foo.py::test_bar" in args

    def test_defaults_to_cwd_when_no_working_dir(self):
        # working_dir=None falls back to Path.cwd() — rootdir is always present
        runner_no_dir = PytestRunner(working_dir=None)
        args = runner_no_dir.build_pytest_args()
        assert "--rootdir" in args


# ---------------------------------------------------------------------------
# finalize_session
# ---------------------------------------------------------------------------

class TestFinalizeSession:
    def test_sets_exit_code(self, runner):
        runner._current_session = make_session()
        runner.finalize_session(datetime.now(), 1)
        assert runner._current_session.exit_code == ExitCode.TESTS_FAILED

    def test_sets_duration_positive(self, runner):
        runner._current_session = make_session()
        start = datetime.now()
        runner.finalize_session(start, 0)
        assert runner._current_session.duration >= 0.0

    def test_noop_when_no_session(self, runner):
        # Should not raise
        runner.finalize_session(datetime.now(), 0)


# ---------------------------------------------------------------------------
# update_session_counts
# ---------------------------------------------------------------------------

class TestUpdateSessionCounts:
    def test_counts_passed(self, runner):
        session = make_session()
        session.test_results["t1"] = make_test_result("t1", passed=True)
        runner._current_session = session
        runner.update_session_counts()
        assert session.passed == 1

    def test_counts_failed(self, runner):
        session = make_session()
        session.test_results["t1"] = make_test_result("t1", failed=True)
        runner._current_session = session
        runner.update_session_counts()
        assert session.failed == 1

    def test_total_collected_matches_results(self, runner):
        session = make_session()
        session.test_results["t1"] = make_test_result("t1", passed=True)
        session.test_results["t2"] = make_test_result("t2", failed=True)
        runner._current_session = session
        runner.update_session_counts()
        assert session.total_collected == 2

    def test_errors_from_collection_errors(self, runner):
        session = make_session()
        session.collection_errors = ["err1", "err2"]
        runner._current_session = session
        runner.update_session_counts()
        assert session.errors == 2

    def test_noop_when_no_session(self, runner):
        runner.update_session_counts()  # Should not raise


# ---------------------------------------------------------------------------
# format_collection_errors / format_test_failures
# ---------------------------------------------------------------------------

class TestFormatOutput:
    def test_format_collection_errors_empty(self, runner):
        runner._current_session = make_session()
        assert runner.format_collection_errors() == []

    def test_format_collection_errors_has_prefix(self, runner):
        session = make_session()
        session.collection_errors = ["ImportError: no module"]
        runner._current_session = session
        lines = runner.format_collection_errors()
        assert lines[0].startswith("COLLECTION ERROR:")

    def test_format_test_failures_empty(self, runner):
        runner._current_session = make_session()
        assert runner.format_test_failures() == []

    def test_format_test_failures_includes_failed(self, runner):
        session = make_session()
        result = make_test_result("tests/test_foo.py::test_bar", failed=True)
        result.error_message = "AssertionError: fail"
        session.test_results["tests/test_foo.py::test_bar"] = result
        runner._current_session = session
        lines = runner.format_test_failures()
        assert any("FAILED" in line for line in lines)

    def test_format_test_failures_excludes_passed(self, runner):
        session = make_session()
        session.test_results["t1"] = make_test_result("t1", passed=True)
        runner._current_session = session
        lines = runner.format_test_failures()
        assert lines == []

    def test_no_session_returns_empty(self, runner):
        assert runner.format_collection_errors() == []
        assert runner.format_test_failures() == []


# ---------------------------------------------------------------------------
# capture_test_output
# ---------------------------------------------------------------------------

class TestCaptureTestOutput:
    def test_combines_errors_and_failures(self, runner):
        session = make_session()
        session.collection_errors = ["SyntaxError"]
        result = make_test_result("tests/test_foo.py::test_bar", failed=True)
        result.error_message = "AssertionError"
        session.test_results["tests/test_foo.py::test_bar"] = result
        runner._current_session = session
        output = runner.capture_test_output()
        assert "COLLECTION ERROR" in output
        assert "FAILED" in output


# ---------------------------------------------------------------------------
# pytest_warning_recorded
# ---------------------------------------------------------------------------

class TestWarningRecorded:
    def test_appends_warning_to_session(self, runner):
        runner._current_session = make_session()
        runner.pytest_warning_recorded(UserWarning("deprecated"))
        assert len(runner._current_session.warnings) == 1

    def test_noop_without_session(self, runner):
        runner.pytest_warning_recorded(UserWarning("no session"))  # Should not raise


# ---------------------------------------------------------------------------
# pytest_collectreport
# ---------------------------------------------------------------------------

class TestCollectReport:
    def test_collection_failure_appended(self, runner):
        runner._current_session = make_session()
        report = MagicMock()
        report.outcome = "failed"
        report.longrepr = "ImportError: missing module"
        runner.pytest_collectreport(report)
        assert len(runner._current_session.collection_errors) == 1

    def test_passed_collection_not_appended(self, runner):
        runner._current_session = make_session()
        report = MagicMock()
        report.outcome = "passed"
        runner.pytest_collectreport(report)
        assert len(runner._current_session.collection_errors) == 0


# ---------------------------------------------------------------------------
# verify_fix
# ---------------------------------------------------------------------------

class TestVerifyFix:
    def test_returns_true_on_zero_exit_code(self, runner, tmp_path):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert runner.verify_fix(tmp_path / "test_foo.py", "test_foo") is True

    def test_returns_false_on_nonzero_exit_code(self, runner, tmp_path):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = b""
        mock_result.stderr = b""
        with patch("subprocess.run", return_value=mock_result):
            assert runner.verify_fix(tmp_path / "test_foo.py", "test_foo") is False

    def test_returns_false_on_subprocess_exception(self, runner, tmp_path):
        with patch("subprocess.run", side_effect=OSError("not found")):
            assert runner.verify_fix(tmp_path / "test_foo.py", "test_foo") is False

    def test_uses_sys_executable(self, runner, tmp_path):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.verify_fix(tmp_path / "test_foo.py", "test_foo")
        args_passed = mock_run.call_args[0][0]
        assert args_passed[0] == sys.executable

    def test_includes_test_nodeid(self, runner, tmp_path):
        test_file = tmp_path / "test_foo.py"
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.verify_fix(test_file, "test_bar")
        args_passed = mock_run.call_args[0][0]
        assert any("test_bar" in a for a in args_passed)


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------

class TestFormatReport:
    def test_includes_duration(self, runner):
        session = make_session()
        session.duration = 1.23
        report = runner.format_report(session)
        assert "1.23" in report

    def test_includes_total_tests(self, runner):
        session = make_session()
        session.total_collected = 10
        report = runner.format_report(session)
        assert "10" in report

    def test_includes_failed_test_nodeid(self, runner):
        session = make_session()
        result = make_test_result("tests/test_foo.py::test_bar", failed=True)
        session.test_results["tests/test_foo.py::test_bar"] = result
        report = runner.format_report(session)
        assert "tests/test_foo.py::test_bar" in report
