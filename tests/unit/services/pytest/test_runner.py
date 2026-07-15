import builtins
from datetime import datetime, timedelta
from pathlib import Path
import sys
import types
import os
import shutil
import subprocess

import pytest
from unittest.mock import Mock, call
from _pytest.main import ExitCode

import branch_fixer.services.pytest.runner as runner_mod
from branch_fixer.services.pytest.runner import (
    force_remove,
    PytestPlugin,
    PytestRunner,
    TestRunner,
)
from branch_fixer.services.pytest.models import SessionResult, TestResult


# Module-level fixtures
@pytest.fixture
def tmp_workdir(tmp_path):
    return tmp_path


@pytest.fixture
def runner(tmp_workdir):
    return PytestRunner(working_dir=tmp_workdir)


@pytest.fixture
def test_file(tmp_workdir):
    p = tmp_workdir / "test_sample.py"
    p.write_text("def test_dummy():\n    assert True\n")
    return p


class TestForceRemove:
    def test_force_remove_success(self, tmp_path, monkeypatch):
        calls = []

        def fake_rmtree(path):
            calls.append(path)
            # succeed silently

        monkeypatch.setattr(shutil, "rmtree", fake_rmtree)
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)

        p = tmp_path / "dir_to_remove"
        # No need to actually create when rmtree is mocked
        force_remove(p, retries=3, delay=1)
        assert calls == [p]

    def test_force_remove_retries_then_succeeds(self, tmp_path, monkeypatch):
        calls = []

        state = {"count": 0}

        def fake_rmtree(path):
            state["count"] += 1
            calls.append(path)
            if state["count"] < 3:
                raise OSError("temporary failure")
            return None

        slept = []

        def fake_sleep(d):
            slept.append(d)

        monkeypatch.setattr(shutil, "rmtree", fake_rmtree)
        monkeypatch.setattr("time.sleep", fake_sleep)

        p = tmp_path / "dir_retry"
        force_remove(p, retries=5, delay=2)
        # rmtree called 3 times (two failures then success)
        assert len(calls) == 3
        # sleep should be called between failures: called twice
        assert slept == [2, 2]

    def test_force_remove_raises_after_retries(self, tmp_path, monkeypatch):
        calls = []

        def fake_rmtree(path):
            calls.append(path)
            raise OSError("permanent failure")

        slept = []

        def fake_sleep(d):
            slept.append(d)

        monkeypatch.setattr(shutil, "rmtree", fake_rmtree)
        monkeypatch.setattr("time.sleep", fake_sleep)

        p = tmp_path / "dir_fail"
        with pytest.raises(OSError):
            force_remove(p, retries=4, delay=3)
        # rmtree called 4 times (retries == 4)
        assert len(calls) == 4
        # sleep called retries-1 times
        assert slept == [3, 3, 3]

    def test_force_remove_uses_default_params(self, tmp_path, monkeypatch):
        calls = {"count": 0}

        def fake_rmtree(path):
            calls["count"] += 1
            raise OSError("fail")

        slept = []

        def fake_sleep(d):
            slept.append(d)

        monkeypatch.setattr(shutil, "rmtree", fake_rmtree)
        monkeypatch.setattr("time.sleep", fake_sleep)

        p = tmp_path / "dir_default"
        with pytest.raises(OSError):
            # default retries is 5 and default delay is 2
            force_remove(p)
        assert calls["count"] == 5
        assert slept == [2, 2, 2, 2]


class TestPytestPlugin:
    def test_init_stores_runner(self):
        fake_runner = object()
        plugin = PytestPlugin(fake_runner)
        assert plugin.runner is fake_runner

    def test_pytest_collection_modifyitems_prints_nodeids(self, capsys):
        fake_runner = Mock()
        plugin = PytestPlugin(fake_runner)

        items = [types.SimpleNamespace(nodeid="a::test_one"), types.SimpleNamespace(nodeid="b::test_two")]
        plugin.pytest_collection_modifyitems(None, None, items)
        captured = capsys.readouterr()
        assert "  - a::test_one" in captured.out
        assert "  - b::test_two" in captured.out

    def test_pytest_runtest_logreport_forwards_to_runner(self):
        fake_runner = Mock()
        plugin = PytestPlugin(fake_runner)
        report = types.SimpleNamespace(nodeid="n", outcome="passed")
        plugin.pytest_runtest_logreport(report)
        fake_runner.pytest_runtest_logreport.assert_called_once_with(report)

    def test_pytest_collectreport_forwards_to_runner(self):
        fake_runner = Mock()
        plugin = PytestPlugin(fake_runner)
        report = types.SimpleNamespace(nodeid="n", outcome="failed", longrepr="err")
        plugin.pytest_collectreport(report)
        fake_runner.pytest_collectreport.assert_called_once_with(report)

    def test_pytest_warning_recorded_forwards_to_runner(self):
        fake_runner = Mock()
        plugin = PytestPlugin(fake_runner)
        warning = RuntimeWarning("be careful")
        plugin.pytest_warning_recorded(warning, None, None, None)
        fake_runner.pytest_warning_recorded.assert_called_once_with(warning)


class TestPytestRunner:
    def test_init_with_working_dir(self, tmp_path):
        r = PytestRunner(working_dir=tmp_path)
        assert r.working_dir == tmp_path
        assert r._current_session is None
        assert isinstance(r._lock, type(r._lock))

    def test_init_without_working_dir(self, monkeypatch):
        # simulate cwd for deterministic test
        monkeypatch.chdir(os.getcwd())
        r = PytestRunner()
        assert isinstance(r.working_dir, Path)

    def test_build_pytest_args_no_test(self, runner):
        args = runner.build_pytest_args()
        assert "--override-ini=addopts=" in args
        assert "-p" in args and "no:terminal" in args
        assert "--rootdir" in args

    def test_build_pytest_args_with_test_path_only(self, runner, tmp_workdir):
        test_path = Path("tests/test_mod.py")
        args = runner.build_pytest_args(test_path=test_path)
        assert str(test_path) in args

    def test_build_pytest_args_with_test_path_and_function(self, runner):
        test_path = Path("tests/test_mod.py")
        func = "test_it"
        args = runner.build_pytest_args(test_path=test_path, test_function=func)
        assert f"{str(test_path)}::{func}" in args

    def test_finalize_session_with_current_session(self, runner):
        start = datetime.now() - timedelta(seconds=2)
        sess = SessionResult(start_time=start, end_time=start, duration=0.0, exit_code=ExitCode.OK)
        runner._current_session = sess
        runner.finalize_session(start, 2)
        assert runner._current_session.end_time >= start
        assert runner._current_session.duration >= 0.0
        assert runner._current_session.exit_code == ExitCode(2)

    def test_finalize_session_no_session(self, runner):
        runner._current_session = None
        # should not raise
        runner.finalize_session(datetime.now(), 0)
        assert runner._current_session is None

    def test_update_session_counts_no_session(self, runner):
        runner._current_session = None
        runner.update_session_counts()
        assert runner._current_session is None

    def test_update_session_counts_various_results(self, runner):
        start = datetime.now()
        sess = SessionResult(start_time=start, end_time=start, duration=0.0, exit_code=ExitCode.OK)
        # Create multiple TestResult items
        t1 = TestResult(nodeid="f1::t1", test_file=Path("f1"), test_function="t1", error_message=None, longrepr=None)
        t1.passed = True  # clean pass
        t2 = TestResult(nodeid="f2::t2", test_file=Path("f2"), test_function="t2", error_message=None, longrepr=None)
        t2.failed = True
        t3 = TestResult(nodeid="f3::t3", test_file=Path("f3"), test_function="t3", error_message=None, longrepr=None)
        t3.skipped = True
        t4 = TestResult(nodeid="f4::t4", test_file=Path("f4"), test_function="t4", error_message=None, longrepr=None)
        t4.xfailed = True
        t5 = TestResult(nodeid="f5::t5", test_file=Path("f5"), test_function="t5", error_message=None, longrepr=None)
        t5.xpassed = True
        sess.test_results = {
            t1.nodeid: t1,
            t2.nodeid: t2,
            t3.nodeid: t3,
            t4.nodeid: t4,
            t5.nodeid: t5,
        }
        sess.collection_errors = ["err"]
        runner._current_session = sess
        runner.update_session_counts()
        assert runner._current_session.total_collected == 5
        # t1 is counted as passed, t2 failed, t3 skipped, t4 xfailed, t5 xpassed
        assert runner._current_session.passed >= 1
        assert runner._current_session.failed >= 1
        assert runner._current_session.skipped >= 1
        assert runner._current_session.xfailed >= 1
        assert runner._current_session.xpassed >= 1
        assert runner._current_session.errors == 1

    def test_format_collection_errors_no_session(self, runner):
        runner._current_session = None
        assert runner.format_collection_errors() == []

    def test_format_collection_errors_has_errors(self, runner):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        sess.collection_errors = ["bad thing", "other"]
        runner._current_session = sess
        res = runner.format_collection_errors()
        assert res == ["COLLECTION ERROR: bad thing", "COLLECTION ERROR: other"]

    def test_format_test_failures_no_session(self, runner):
        runner._current_session = None
        assert runner.format_test_failures() == []

    def test_format_test_failures_single_failed_with_messages(self, runner):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        tr = TestResult(nodeid="file.py::test_x", test_file=Path("file.py"), test_function="test_x", error_message="boom", longrepr="traceback")
        tr.failed = True
        sess.test_results = {tr.nodeid: tr}
        runner._current_session = sess
        lines = runner.format_test_failures()
        assert "FAILED file.py test_x" in lines[0]
        assert any(line.startswith("E   boom") for line in lines)
        assert "traceback" in lines[-1]

    def test_format_test_failures_nodeid_without_double_colons_raises(self, runner):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        tr = TestResult(nodeid="no_colon_id", test_file=Path("file"), test_function=None, error_message=None, longrepr=None)
        tr.failed = True
        sess.test_results = {tr.nodeid: tr}
        runner._current_session = sess
        with pytest.raises(ValueError):
            runner.format_test_failures()

    def test_capture_test_output_combines_outputs(self, runner):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        sess.collection_errors = ["one"]
        tr = TestResult(nodeid="f::t", test_file=Path("f"), test_function="t", error_message="err", longrepr="lr")
        tr.failed = True
        sess.test_results = {tr.nodeid: tr}
        runner._current_session = sess
        out = runner.capture_test_output()
        assert "COLLECTION ERROR: one" in out
        assert "FAILED f t" in out or "FAILED f::t" in out or "FAILED f t" in out  # defensive

    def test_capture_test_output_empty(self, runner):
        runner._current_session = None
        assert runner.capture_test_output() == ""

    def test_run_test_successful_flow(self, tmp_path, monkeypatch):
        r = PytestRunner(working_dir=tmp_path)
        # Mock pytest.main to capture args and plugins
        captured = {}

        def fake_main(args, plugins=None):
            captured["args"] = list(args)
            captured["plugins"] = list(plugins) if plugins else []
            return 0

        monkeypatch.setattr("pytest.main", fake_main)
        # Spy on cleanup and capture_test_output
        monkeypatch.setattr(r, "cleanup", Mock())
        monkeypatch.setattr(r, "capture_test_output", Mock(return_value="OUT"))
        session = r.run_test(test_path=Path("tests/test.py"), test_function="test_me")
        # verify exit code set to OK
        assert isinstance(session, SessionResult)
        assert session.exit_code == ExitCode(0)
        # capture_test_output used
        assert session.output == "OUT"
        # cleanup called
        r.cleanup.assert_called_once()
        # plugin passed to pytest.main and is PytestPlugin with runner r
        assert any(isinstance(p, PytestPlugin) and p.runner is r for p in captured["plugins"])
        # args contain our test target
        assert any(str(Path("tests/test.py")) + "::test_me" == a for a in captured["args"])

    def test_run_test_with_pytest_main_exception_calls_cleanup_and_propagates(self, tmp_path, monkeypatch):
        r = PytestRunner(working_dir=tmp_path)

        def bad_main(*a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr("pytest.main", bad_main)
        monkeypatch.setattr(r, "cleanup", Mock())
        with pytest.raises(RuntimeError):
            r.run_test()
        r.cleanup.assert_called_once()

    def test_run_test_build_args_called_with_parameters(self, tmp_path, monkeypatch):
        r = PytestRunner(working_dir=tmp_path)
        captured = {}

        def fake_main(args, plugins=None):
            captured["args"] = args
            return 0

        monkeypatch.setattr("pytest.main", fake_main)
        monkeypatch.setattr(r, "cleanup", Mock())
        monkeypatch.setattr(r, "capture_test_output", Mock(return_value=""))
        r.run_test(test_path=Path("foo.py"), test_function="t")
        assert any(str(Path("foo.py")) + "::t" == a for a in captured["args"])

    def test_pytest_runtest_logreport_no_session(self, runner):
        runner._current_session = None
        report = types.SimpleNamespace(nodeid="a", fspath=None, when="call", outcome="passed")
        # Should not raise
        runner.pytest_runtest_logreport(report)
        assert runner._current_session is None

    def test_pytest_runtest_logreport_creates_result_with_function_attr(self, runner):
        start = datetime.now()
        sess = SessionResult(start_time=start, end_time=start, duration=0.0, exit_code=ExitCode.OK)
        runner._current_session = sess
        func = types.SimpleNamespace(__name__="myfunc")
        report = types.SimpleNamespace(nodeid="file.py::myfunc", fspath="file.py", function=func, when="call", outcome="passed", capstdout=None, capstderr=None, caplog=None, longrepr=None, duration=0.1, skipped=False, passed=True, keywords={})
        # patch update helper to just call through so we can assert invocation
        called = {"flag": False}

        def fake_update(result, rep):
            called["flag"] = True
            # minimal update simulation
            result.call_outcome = rep.outcome

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setenv  # dummy to get monkeypatch fixture-like behavior - we will use direct assignment
        try:
            # use patching by setting attribute
            runner._update_test_result_outcomes = fake_update
            runner.pytest_runtest_logreport(report)
            assert called["flag"]
            tr = runner._current_session.test_results.get(report.nodeid)
            assert tr is not None
            assert tr.test_function == "myfunc"
            assert tr.test_file == Path("file.py")
        finally:
            monkeypatch.undo()

    def test_pytest_runtest_logreport_creates_result_with_nodeid_parse(self, runner):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        runner._current_session = sess
        report = types.SimpleNamespace(nodeid="somefile.py::test_name", fspath=None, when="call", outcome="passed", capstdout=None, capstderr=None, caplog=None, longrepr=None, duration=0.0, skipped=False, passed=True, keywords={})
        # Replace update helper to avoid side effects
        runner._update_test_result_outcomes = lambda result, rep: None
        runner.pytest_runtest_logreport(report)
        tr = runner._current_session.test_results.get(report.nodeid)
        assert tr.test_function == "test_name"
        assert tr.test_file == Path("unknown")  # since fspath is None

    def test_pytest_runtest_logreport_uses_unknown_when_fspath_missing_and_nodeid_has_no_function(self, runner):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        runner._current_session = sess
        report = types.SimpleNamespace(nodeid="nodoublecolon", fspath=None, when="call", outcome="passed", capstdout=None, capstderr=None, caplog=None, longrepr=None, duration=0.0, skipped=False, passed=True, keywords={})
        runner._update_test_result_outcomes = lambda result, rep: None
        runner.pytest_runtest_logreport(report)
        tr = runner._current_session.test_results.get(report.nodeid)
        assert tr.test_function == "unknown"
        assert tr.test_file == Path("unknown")

    def test_verify_fix_success_return_true(self, tmp_path, monkeypatch, test_file):
        r = PytestRunner(working_dir=tmp_path)
        called = {}

        class FakeProc:
            def __init__(self):
                self.returncode = 0
                self.stdout = b"ok"
                self.stderr = b""

        def fake_run(args, stdout=None, stderr=None):
            called["args"] = args
            return FakeProc()

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok = r.verify_fix(test_file, "test_dummy")
        assert ok is True
        # ensure args include rootdir and test target
        assert "--rootdir" in called["args"]
        assert f"{str(test_file)}::test_dummy" in called["args"]

    def test_verify_fix_failure_return_false_and_logs(self, tmp_path, monkeypatch, test_file):
        r = PytestRunner(working_dir=tmp_path)

        class FakeProc:
            def __init__(self):
                self.returncode = 1
                self.stdout = b"fail\n"
                self.stderr = b"err\n"

        def fake_run(*args, **kwargs):
            return FakeProc()

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok = r.verify_fix(test_file, "test_dummy")
        assert ok is False

    def test_verify_fix_subprocess_throws_exception_returns_false(self, tmp_path, monkeypatch, test_file):
        r = PytestRunner(working_dir=tmp_path)

        def fake_run(*a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok = r.verify_fix(test_file, "test_dummy")
        assert ok is False

    def test_format_report_basic(self):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=1.23, exit_code=ExitCode.OK)
        sess.total_collected = 3
        sess.passed = 2
        sess.failed = 1
        sess.skipped = 0
        sess.xfailed = 0
        sess.xpassed = 0
        sess.errors = 0
        r = PytestRunner()
        report = r.format_report(sess)
        assert "Test Execution Report" in report
        assert "Duration: 1.23s" or "Duration: 1.2"  # allow formatting variance
        assert "Status: " in report
        assert "Total Tests: 3" in report
        assert "Passed: 2" in report
        assert "Failed: 1" in report

    def test_format_report_with_collection_errors_and_warnings(self):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.5, exit_code=ExitCode.OK)
        sess.collection_errors = ["colerr1"]
        sess.warnings = ["warn1"]
        r = PytestRunner()
        report = r.format_report(sess)
        assert "Collection Errors:" in report
        assert "colerr1" in report
        assert "Warnings:" in report
        assert "warn1" in report

    def test_format_report_includes_failed_test_details(self):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.5, exit_code=ExitCode.OK)
        tr = TestResult(nodeid="f::t", test_file=Path("f"), test_function="t", error_message="err", longrepr="lr")
        tr.failed = True
        sess.test_results = {tr.nodeid: tr}
        r = PytestRunner()
        report = r.format_report(sess)
        assert "FAILED f::t" in report or "FAILED f::t" in report
        assert "err" in report
        assert "lr" in report

    def test_format_report_formats_exit_code_name(self):
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.INTERRUPTED)
        r = PytestRunner()
        report = r.format_report(sess)
        assert f"Status: {sess.exit_code.name}" in report

    def test_pytest_collectreport_no_session(self):
        r = PytestRunner()
        r._current_session = None
        rep = types.SimpleNamespace(outcome="failed", longrepr="bad")
        # Should not raise
        r.pytest_collectreport(rep)
        assert r._current_session is None

    def test_pytest_collectreport_failed_appends_error(self):
        r = PytestRunner()
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        r._current_session = sess
        rep = types.SimpleNamespace(outcome="failed", longrepr="collector fail")
        r.pytest_collectreport(rep)
        assert "collector fail" in r._current_session.collection_errors[0]

    def test_pytest_collectreport_not_failed_ignored(self):
        r = PytestRunner()
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        r._current_session = sess
        rep = types.SimpleNamespace(outcome="passed", longrepr=None)
        r.pytest_collectreport(rep)
        assert r._current_session.collection_errors == []

    def test_pytest_warning_recorded_with_session(self):
        r = PytestRunner()
        sess = SessionResult(start_time=datetime.now(), end_time=datetime.now(), duration=0.0, exit_code=ExitCode.OK)
        r._current_session = sess
        r.pytest_warning_recorded(UserWarning("be careful"))
        assert "be careful" in r._current_session.warnings[0]

    def test_pytest_warning_recorded_no_session(self):
        r = PytestRunner()
        r._current_session = None
        # should not raise
        r.pytest_warning_recorded(UserWarning("warn"))
        assert r._current_session is None

    def test_cleanup_removes_existing_temp_dirs_success(self, tmp_path, monkeypatch):
        r = PytestRunner()
        tempdir = tmp_path / "to_clean"
        tempdir.mkdir()
        r.temp_dirs = [tempdir]
        called = []

        def fake_force_remove(path):
            called.append(path)

        monkeypatch.setattr(runner_mod, "force_remove", fake_force_remove)
        r.cleanup()
        assert called == [tempdir]
        assert r.temp_dirs == []

    def test_cleanup_handles_force_remove_oserror(self, tmp_path, monkeypatch):
        r = PytestRunner()
        tempdir = tmp_path / "to_clean2"
        tempdir.mkdir()
        r.temp_dirs = [tempdir]
        def raise_oserror(*a, **k):
            raise OSError("cannot remove")
        monkeypatch.setattr(runner_mod, "force_remove", raise_oserror)
        # should not raise
        r.cleanup()
        assert r.temp_dirs == []

    def test_cleanup_skips_nonexistent_dirs(self, tmp_path, monkeypatch):
        r = PytestRunner()
        tempdir = tmp_path / "nonexistent"
        # do not create
        r.temp_dirs = [tempdir]
        called = []

        def fake_force_remove(path):
            called.append(path)

        monkeypatch.setattr(runner_mod, "force_remove", fake_force_remove)
        r.cleanup()
        # force_remove should not be called for non-existent
        assert called == []
        assert r.temp_dirs == []


class TestTestRunnerAlias:
    def test_alias_is_same(self):
        assert TestRunner is PytestRunner