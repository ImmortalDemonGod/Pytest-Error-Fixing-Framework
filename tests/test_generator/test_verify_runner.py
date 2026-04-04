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
# VerificationResult.all_passed uses exit_code, not counts
# ---------------------------------------------------------------------------


class TestVerificationResult:
    def test_all_passed_true_on_exit_code_zero(self, tmp_path):
        r = VerificationResult(output_dir=tmp_path, exit_code=0)
        assert r.all_passed is True

    def test_all_passed_true_on_exit_code_five_no_tests_collected(self, tmp_path):
        # exit code 5 = no tests collected — acceptable
        r = VerificationResult(output_dir=tmp_path, exit_code=5)
        assert r.all_passed is True

    def test_all_passed_false_on_exit_code_one(self, tmp_path):
        r = VerificationResult(output_dir=tmp_path, exit_code=1)
        assert r.all_passed is False

    def test_all_passed_false_even_with_zero_parsed_failures_on_nonzero_exit(self, tmp_path):
        # Regression: parser used to return all_passed=True when it failed to
        # parse any FAILED lines but the exit code was 1 (real failures present)
        r = VerificationResult(output_dir=tmp_path, failed=0, failures=[], exit_code=1)
        assert r.all_passed is False


# ---------------------------------------------------------------------------
# parse_pytest_output — pure parsing function
# ---------------------------------------------------------------------------


class TestParsePytestOutput:
    def test_parses_failed_line_with_error_suffix(self, tmp_path):
        output = (
            "FAILED test_ops.py::TestOps::test_add - AssertionError: assert 5 == 6\n"
            "1 failed in 0.1s\n"
        )
        result = parse_pytest_output(output, tmp_path, exit_code=1)
        assert result.failed == 1
        assert len(result.failures) == 1
        assert result.failures[0].test_id == "TestOps::test_add"
        assert "assert 5 == 6" in result.failures[0].error_output

    def test_parses_failed_line_without_error_suffix(self, tmp_path):
        # Parametrized tests often have no " - error" suffix in -q mode
        output = (
            "FAILED test_ops.py::TestOps::test_add[param-value]\n"
            "1 failed in 0.1s\n"
        )
        result = parse_pytest_output(output, tmp_path, exit_code=1)
        assert len(result.failures) == 1
        assert "test_add[param-value]" in result.failures[0].test_id

    def test_parses_error_lines(self, tmp_path):
        # ERROR at setup/teardown also indicates failure
        output = (
            "ERROR test_ops.py::TestOps::test_setup\n"
            "1 error in 0.1s\n"
        )
        result = parse_pytest_output(output, tmp_path, exit_code=1)
        assert len(result.failures) == 1

    def test_parses_passed_count_from_summary(self, tmp_path):
        output = "3 passed in 0.5s\n"
        result = parse_pytest_output(output, tmp_path, exit_code=0)
        assert result.passed == 3
        assert result.failed == 0

    def test_parses_mixed_pass_fail_summary(self, tmp_path):
        output = (
            "FAILED test_foo.py::TestFoo::test_x - ValueError: bad\n"
            "1 failed, 5 passed in 0.8s\n"
        )
        result = parse_pytest_output(output, tmp_path, exit_code=1)
        assert result.failed == 1
        assert result.passed == 5

    def test_multiple_failures_extracted(self, tmp_path):
        output = (
            "FAILED test_foo.py::A::test_one - AssertionError: 1\n"
            "FAILED test_foo.py::A::test_two - AssertionError: 2\n"
            "2 failed in 0.2s\n"
        )
        result = parse_pytest_output(output, tmp_path, exit_code=1)
        assert len(result.failures) == 2
        ids = {f.test_id for f in result.failures}
        assert ids == {"A::test_one", "A::test_two"}

    def test_exit_code_zero_gives_all_passed_true(self, tmp_path):
        output = "3 passed in 0.3s\n"
        result = parse_pytest_output(output, tmp_path, exit_code=0)
        assert result.all_passed is True

    def test_pytest_warning_garbage_does_not_corrupt_result(self, tmp_path):
        # Regression: PytestWarning lines contain "(rm_rf) error removing"
        # which matched the old "error" in stripped check, poisoning the summary.
        garbage = (
            "15 failed, 16 passed, 20 errors in 0.13s\n"
            "/path/_pytest/pathlib.py:96: PytestWarning: (rm_rf) error removing /tmp/garbage\n"
            "<class 'OSError'>: [Errno 66] Directory not empty: '/tmp/garbage'\n"
            "  warnings.warn(\n"
        ) * 10  # simulate many warning lines after the real summary
        result = parse_pytest_output(garbage, tmp_path, exit_code=1)
        assert result.failed == 15
        assert result.passed == 16

    def test_raw_output_preserved(self, tmp_path):
        output = "some pytest output\n"
        result = parse_pytest_output(output, tmp_path)
        assert result.raw_output == output

    def test_exit_code_stored(self, tmp_path):
        result = parse_pytest_output("", tmp_path, exit_code=1)
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# _find_summary_line — must require "in Xs" suffix
# ---------------------------------------------------------------------------


class TestFindSummaryLine:
    def test_finds_real_summary(self):
        output = "some output\n3 passed in 0.1s\n"
        assert "passed" in _find_summary_line(output)

    def test_ignores_pytestwarning_error_lines(self):
        # Lines containing "error" that are NOT summary lines
        output = (
            "2 failed in 0.5s\n"
            "/path/pathlib.py: PytestWarning: (rm_rf) error removing /tmp/x\n"
            "  warnings.warn(\n"
        )
        result = _find_summary_line(output)
        assert result is not None
        assert "failed" in result
        assert "rm_rf" not in result

    def test_returns_none_on_empty_output(self):
        assert _find_summary_line("") is None

    def test_returns_none_when_no_real_summary(self):
        # Only warning lines — no real pytest summary
        output = "/path/pathlib.py: PytestWarning: (rm_rf) error removing /x\n"
        assert _find_summary_line(output) is None


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
        """
        Create a mock subprocess.CompletedProcess with specified stdout, stderr, and return code.
        
        Parameters:
            stdout (str): Text to set on the mock's `stdout` attribute.
            stderr (str): Text to set on the mock's `stderr` attribute.
            returncode (int): Integer to set on the mock's `returncode` attribute.
        
        Returns:
            MagicMock: A MagicMock instance with `spec=subprocess.CompletedProcess` and the provided attributes set.
        """
        r = MagicMock(spec=subprocess.CompletedProcess)
        r.stdout = stdout
        r.stderr = stderr
        r.returncode = returncode
        return r

    def test_run_returns_verification_result(self, tmp_path):
        runner = VerificationRunner()
        with patch("subprocess.run",
                   return_value=self._completed(stdout="2 passed in 0.1s\n", returncode=0)):
            result = runner.run(tmp_path)
        assert isinstance(result, VerificationResult)
        assert result.passed == 2
        assert result.all_passed is True

    def test_run_propagates_exit_code(self, tmp_path):
        runner = VerificationRunner()
        with patch("subprocess.run",
                   return_value=self._completed(stdout="1 failed in 0.1s\n", returncode=1)):
            result = runner.run(tmp_path)
        assert result.exit_code == 1
        assert result.all_passed is False

    def test_run_includes_extra_pythonpath_in_env(self, tmp_path):
        runner = VerificationRunner(extra_pythonpath="/my/src")
        captured = {}

        def capture(cmd, **kwargs):
            """
            Capture the command environment passed to a subprocess mock and return a completed-process stub indicating one passing test.
            
            Parameters:
                cmd: The command that would have been executed (ignored by the stub).
                **kwargs: Keyword arguments forwarded to the subprocess call; the `env` mapping, if present, is stored for inspection.
            
            Returns:
                completed (object): A stubbed completed-process object whose `stdout` equals "1 passed in 0.1s\n".
            """
            captured["env"] = kwargs.get("env", {})
            return self._completed(stdout="1 passed in 0.1s\n")

        with patch("subprocess.run", side_effect=capture):
            runner.run(tmp_path)

        assert "/my/src" in captured["env"].get("PYTHONPATH", "")

    def test_run_passes_output_dir_to_pytest(self, tmp_path):
        runner = VerificationRunner()
        captured = {}

        def capture(cmd, **kwargs):
            """
            Record the invoked command and return a canned completed-process result indicating one passing test.
            
            Parameters:
            	cmd: The command (string or sequence) that would be executed; this value is stored in `captured["cmd"]`.
            	**kwargs: Additional keyword arguments are accepted but ignored.
            
            Returns:
            	A completed-process-like object whose `stdout` is the string "1 passed in 0.1s\n".
            """
            captured["cmd"] = cmd
            return self._completed(stdout="1 passed in 0.1s\n")

        with patch("subprocess.run", side_effect=capture):
            runner.run(tmp_path)

        assert str(tmp_path) in captured["cmd"]
