"""Unit tests for src/dev/test_generator/verify/fixer.py"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src.dev.test_generator.verify.fixer import (
    GeneratedTestFixer,
    _group_by_file,
    _make_test_error,
)
from src.dev.test_generator.verify.runner import TestFailure, VerificationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _failure(test_file: Path, test_id: str = "TestFoo::test_bar") -> TestFailure:
    return TestFailure(
        test_file=test_file,
        test_id=test_id,
        error_output="AssertionError: assert 1 == 2",
    )


def _result(output_dir: Path, failures=(), passed=0, failed=0, exit_code: int = -1) -> VerificationResult:
    actual_failures = list(failures)
    actual_failed = failed or len(actual_failures)
    # Default exit_code: 1 if there are failures, 0 if not
    if exit_code == -1:
        exit_code = 1 if actual_failed else 0
    return VerificationResult(
        output_dir=output_dir,
        passed=passed,
        failed=actual_failed,
        failures=actual_failures,
        exit_code=exit_code,
    )


def _make_fixer(max_attempts=2):
    """Return a GeneratedTestFixer with fully mocked dependencies."""
    ai_manager = MagicMock()
    from branch_fixer.core.models import CodeChanges
    ai_manager.generate_fix.return_value = CodeChanges(
        original_code="", modified_code="# fixed code\n" + "x = 1\n" * 20
    )

    change_applier = MagicMock()
    change_applier.apply_changes_with_backup.return_value = (True, Path("/backup"))

    return GeneratedTestFixer(ai_manager, change_applier, max_attempts=max_attempts), \
           ai_manager, change_applier


def _make_runner(next_result: VerificationResult) -> MagicMock:
    runner = MagicMock()
    runner.run.return_value = next_result
    return runner


def _mock_verify_pass():
    """Context manager: subprocess.run returns exit code 0 (fix verified)."""
    proc = MagicMock()
    proc.returncode = 0
    return patch("src.dev.test_generator.verify.fixer.subprocess.run", return_value=proc)


def _mock_verify_fail():
    """Context manager: subprocess.run returns exit code 1 (fix not verified)."""
    proc = MagicMock()
    proc.returncode = 1
    return patch("src.dev.test_generator.verify.fixer.subprocess.run", return_value=proc)


# ---------------------------------------------------------------------------
# GeneratedTestFixer.fix_failures
# ---------------------------------------------------------------------------


class TestFixFailures:
    def test_returns_unchanged_result_when_all_passed(self, tmp_path):
        fixer, _, _ = _make_fixer()
        runner = _make_runner(_result(tmp_path))
        passing = _result(tmp_path, passed=3, failed=0)

        result = fixer.fix_failures(passing, runner)

        assert result is passing  # same object, short-circuited
        runner.run.assert_not_called()

    def test_calls_ai_manager_for_failing_file(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("# broken\n")
        fixer, ai, _ = _make_fixer(max_attempts=1)
        failing = _result(tmp_path, failures=(_failure(test_file),), failed=1)
        runner = _make_runner(_result(tmp_path, passed=1))

        with _mock_verify_pass():
            fixer.fix_failures(failing, runner)

        ai.generate_fix.assert_called_once()

    def test_calls_change_applier_with_ai_output(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("# broken\n")
        fixer, ai, applier = _make_fixer(max_attempts=1)
        failing = _result(tmp_path, failures=(_failure(test_file),), failed=1)
        runner = _make_runner(_result(tmp_path, passed=1))

        with _mock_verify_pass():
            fixer.fix_failures(failing, runner)

        applier.apply_changes_with_backup.assert_called_once()
        call_args = applier.apply_changes_with_backup.call_args[0]
        assert call_args[0] == test_file

    def test_reruns_verification_after_fixes(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("# broken\n")
        fixer, _, _ = _make_fixer(max_attempts=1)
        failing = _result(tmp_path, failures=(_failure(test_file),), failed=1)
        re_run_result = _result(tmp_path, passed=1)
        runner = _make_runner(re_run_result)

        with _mock_verify_pass():
            result = fixer.fix_failures(failing, runner)

        runner.run.assert_called_once_with(tmp_path)
        assert result is re_run_result

    def test_stops_after_successful_fix(self, tmp_path):
        """If apply_changes succeeds and pytest passes, should not retry."""
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("# broken\n")
        fixer, ai, applier = _make_fixer(max_attempts=3)
        failing = _result(tmp_path, failures=(_failure(test_file),), failed=1)
        runner = _make_runner(_result(tmp_path, passed=1))

        with _mock_verify_pass():
            fixer.fix_failures(failing, runner)

        assert ai.generate_fix.call_count == 1

    def test_retries_up_to_max_attempts_on_apply_failure(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("# broken\n")
        fixer, ai, applier = _make_fixer(max_attempts=2)
        applier.apply_changes_with_backup.return_value = (False, None)  # always fails
        failing = _result(tmp_path, failures=(_failure(test_file),), failed=1)
        runner = _make_runner(_result(tmp_path))

        with _mock_verify_fail():
            fixer.fix_failures(failing, runner)

        assert ai.generate_fix.call_count == 2

    def test_retries_when_verify_fails_after_apply(self, tmp_path):
        """Apply succeeds but pytest still fails → should retry up to max_attempts."""
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("# broken\n")
        fixer, ai, applier = _make_fixer(max_attempts=3)
        failing = _result(tmp_path, failures=(_failure(test_file),), failed=1)
        runner = _make_runner(_result(tmp_path))
        runner.capture_error_output.return_value = "still failing"

        with _mock_verify_fail():
            fixer.fix_failures(failing, runner)

        assert ai.generate_fix.call_count == 3

    def test_rejects_fix_that_removes_all_tests(self, tmp_path):
        """Exit code 5 (no tests collected) must NOT be accepted as a verified fix."""
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("# broken\n")
        fixer, ai, applier = _make_fixer(max_attempts=1)
        failing = _result(tmp_path, failures=(_failure(test_file),), failed=1)
        runner = _make_runner(_result(tmp_path))

        proc_no_tests = MagicMock()
        proc_no_tests.returncode = 5  # no tests collected
        with patch("src.dev.test_generator.verify.fixer.subprocess.run", return_value=proc_no_tests):
            fixer.fix_failures(failing, runner)

        # Backup must be restored since exit code 5 is not acceptable
        applier.restore_backup.assert_called_once()

    def test_groups_failures_by_file(self, tmp_path):
        """Multiple failures in the same file → one fix attempt sequence."""
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("# broken\n")
        failures = [
            _failure(test_file, "TestFoo::test_one"),
            _failure(test_file, "TestFoo::test_two"),
        ]
        fixer, ai, _ = _make_fixer(max_attempts=1)
        failing = _result(tmp_path, failures=failures, failed=2)
        runner = _make_runner(_result(tmp_path, passed=2))

        with _mock_verify_pass():
            fixer.fix_failures(failing, runner)

        # Both failures in same file → only one fix attempt (first failure used)
        assert ai.generate_fix.call_count == 1


# ---------------------------------------------------------------------------
# _group_by_file helper
# ---------------------------------------------------------------------------


class TestGroupByFile:
    def test_groups_same_file_together(self, tmp_path):
        f = tmp_path / "test_foo.py"
        failures = [_failure(f, "test_a"), _failure(f, "test_b")]
        groups = _group_by_file(failures)
        assert len(groups) == 1
        assert len(groups[f]) == 2

    def test_separates_different_files(self, tmp_path):
        f1 = tmp_path / "test_foo.py"
        f2 = tmp_path / "test_bar.py"
        groups = _group_by_file([_failure(f1), _failure(f2)])
        assert len(groups) == 2

    def test_empty_list_returns_empty_dict(self):
        assert _group_by_file([]) == {}


# ---------------------------------------------------------------------------
# _make_test_error helper
# ---------------------------------------------------------------------------


class TestMakeTestError:
    def test_test_file_preserved(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        failure = _failure(test_file, "TestFoo::test_x")
        error = _make_test_error(test_file, failure)
        assert error.test_file == test_file

    def test_test_function_is_test_id(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        failure = _failure(test_file, "TestFoo::test_x")
        error = _make_test_error(test_file, failure)
        assert error.test_function == "TestFoo::test_x"

    def test_error_output_in_error_details(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        failure = TestFailure(test_file, "test_x", "AssertionError: 1 != 2")
        error = _make_test_error(test_file, failure)
        assert "AssertionError" in error.error_details.message

    def test_message_contains_test_file_instruction(self, tmp_path):
        """The error message must tell the AI to produce a TEST FILE, not source code."""
        test_file = tmp_path / "test_foo.py"
        failure = _failure(test_file)
        error = _make_test_error(test_file, failure)
        msg = error.error_details.message.upper()
        assert "TEST FILE" in msg

    def test_raw_error_preferred_over_failure_output(self, tmp_path):
        test_file = tmp_path / "test_foo.py"
        failure = TestFailure(test_file, "test_x", "short error")
        error = _make_test_error(test_file, failure, raw_error="long detailed traceback")
        assert "long detailed traceback" in error.error_details.message
