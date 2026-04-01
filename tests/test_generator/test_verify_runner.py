"""Unit tests for src/dev/test_generator/verify/runner.py"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.dev.test_generator.verify.runner import (
    TestFailure,
    VerificationResult,
    VerificationRunner,
    _find_summary_line,
    _resolve_test_file,
    parse_pytest_output,
)


# ---------------------------------------------------------------------------
# TestFailure value object
# ---------------------------------------------------------------------------


class TestTestFailure:
    def test_is_frozen(self, tmp_path):
        f = TestFailure(
            test_file=tmp_path / "test_foo.py",
            test_id="TestFoo::test_bar",
            error_output="AssertionError: assert 1 == 2",
        )
        with pytest.raises((AttributeError, TypeError)):
            f.test_id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# VerificationResult
# ---------------------------------------------------------------------------


class TestVerificationResult:
    def test_all_passed_true_when_no_failures(self, tmp_path):
        r = VerificationResult(output_dir=tmp_path, passed=3, failed=0)
        assert r.all_passed is True

    def test_all_passed_false_when_failures_present(self, tmp_path):
        f = TestFailure(tmp_path / "t.py", "test_x", "err")
        r = VerificationResult(output_dir=tmp_path, passed=1, failed=1, failures=[f])
        assert r.all_passed is False

    def test_all_passed_false_when_failed_count_nonzero(self, tmp_path):
        r = VerificationResult(output_dir=tmp_path, passed=0, failed=1)
        assert r.all_passed is False


# ---------------------------------------------------------------------------
# parse_pytest_output — the pure parsing function
# ---------------------------------------------------------------------------


class TestParsePytestOutput:
    def test_parses_failed_line(self, tmp_path):
        output = (
            "FAILED test_ops.py::TestOps::test_add - AssertionError: assert 5 == 6\n"
            "1 failed in 0.1s\n"
        )
        result = parse_pytest_output(output, tmp_path)
        assert result.failed == 1
        assert len(result.failures) == 1
        assert result.failures[0].test_id == "TestOps::test_add"
        assert "assert 5 == 6" in result.failures[0].error_output

    def test_parses_passed_count_from_summary(self, tmp_path):
        output = "3 passed in 0.5s\n"
        result = parse_pytest_output(output, tmp_path)
        assert result.passed == 3
        assert result.failed == 0

    def test_parses_mixed_pass_fail_summary(self, tmp_path):
        output = (
            "FAILED test_foo.py::TestFoo::test_x - ValueError: bad\n"
            "1 failed, 5 passed in 0.8s\n"
        )
        result = parse_pytest_output(output, tmp_path)
        assert result.failed == 1
        assert result.passed == 5

    def test_multiple_failures_extracted(self, tmp_path):
        output = (
            "FAILED test_foo.py::A::test_one - AssertionError: 1\n"
            "FAILED test_foo.py::A::test_two - AssertionError: 2\n"
            "2 failed in 0.2s\n"
        )
        result = parse_pytest_output(output, tmp_path)
        assert len(result.failures) == 2
        ids = {f.test_id for f in result.failures}
        assert ids == {"A::test_one", "A::test_two"}

    def test_returns_zero_failures_on_clean_output(self, tmp_path):
        output = "3 passed in 0.3s\n"
        result = parse_pytest_output(output, tmp_path)
        assert result.failures == []
        assert result.all_passed is True

    def test_raw_output_preserved(self, tmp_path):
        output = "some pytest output\n"
        result = parse_pytest_output(output, tmp_path)
        assert result.raw_output == output

    def test_output_dir_stored(self, tmp_path):
        result = parse_pytest_output("", tmp_path)
        assert result.output_dir == tmp_path


# ---------------------------------------------------------------------------
# _find_summary_line
# ---------------------------------------------------------------------------


class TestFindSummaryLine:
    def test_finds_last_summary_line(self):
        output = "some output\n3 passed in 0.1s\n"
        assert "passed" in _find_summary_line(output)

    def test_returns_none_on_empty_output(self):
        assert _find_summary_line("") is None

    def test_returns_none_when_no_summary(self):
        assert _find_summary_line("collecting ...\n") is None


# ---------------------------------------------------------------------------
# _resolve_test_file
# ---------------------------------------------------------------------------


class TestResolveTestFile:
    def test_returns_absolute_path_as_is(self, tmp_path):
        abs_path = str(tmp_path / "test_foo.py")
        result = _resolve_test_file(abs_path, tmp_path)
        assert result == Path(abs_path)

    def test_resolves_relative_to_output_dir(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("")
        result = _resolve_test_file("test_foo.py", tmp_path)
        assert result == test_file.resolve()


# ---------------------------------------------------------------------------
# VerificationRunner.run (mocked subprocess)
# ---------------------------------------------------------------------------


class TestVerificationRunnerRun:
    def _completed(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        r = MagicMock(spec=subprocess.CompletedProcess)
        r.stdout = stdout
        r.stderr = stderr
        r.returncode = returncode
        return r

    def test_run_returns_verification_result(self, tmp_path):
        runner = VerificationRunner()
        with patch("subprocess.run", return_value=self._completed(stdout="2 passed in 0.1s\n")):
            result = runner.run(tmp_path)
        assert isinstance(result, VerificationResult)
        assert result.passed == 2

    def test_run_includes_extra_pythonpath_in_env(self, tmp_path):
        runner = VerificationRunner(extra_pythonpath="/my/src")
        captured = {}

        def capture(cmd, **kwargs):
            captured["env"] = kwargs.get("env", {})
            return self._completed(stdout="1 passed in 0.1s\n")

        with patch("subprocess.run", side_effect=capture):
            runner.run(tmp_path)

        assert "/my/src" in captured["env"].get("PYTHONPATH", "")

    def test_run_passes_output_dir_to_pytest(self, tmp_path):
        runner = VerificationRunner()
        captured = {}

        def capture(cmd, **kwargs):
            captured["cmd"] = cmd
            return self._completed(stdout="1 passed in 0.1s\n")

        with patch("subprocess.run", side_effect=capture):
            runner.run(tmp_path)

        assert str(tmp_path) in captured["cmd"]
