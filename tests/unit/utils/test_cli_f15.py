"""
RED tests for F15: success_count never incremented in CLI._process_all_errors.

Finding source:
  https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/
  697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L11

Root cause:
  _process_all_errors (cli.py:519) initialises success_count = 0 and never
  increments it. _process_non_interactive_error calls run_fix_workflow but
  discards the bool return value (returns None). So process_errors always
  returns exit-code 1 when >= 1 error is processed, even if every fix succeeds.

These tests are intentionally RED until the fix is implemented.
"""

from unittest.mock import patch

import pytest

from branch_fixer.core.models import ErrorDetails, TestError
from branch_fixer.utils.cli import CLI


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cli():
    return CLI()


@pytest.fixture
def sample_error(tmp_path):
    p = tmp_path / "test_sample.py"
    p.write_text("def test_dummy():\n    assert True\n", encoding="utf-8")
    details = ErrorDetails(
        error_type="AssertionError", message="assert failed", stack_trace=None
    )
    return TestError(test_file=p, test_function="test_dummy", error_details=details)


# ---------------------------------------------------------------------------
# Unit layer: _process_all_errors
# Caller-supplied input (run_fix_workflow outcome) is set explicitly here.
# ---------------------------------------------------------------------------


class TestProcessAllErrorsSuccessCount:
    """
    Guards against: success_count stays 0 regardless of run_fix_workflow outcome.

    The caller of _process_all_errors supplies the fix outcome indirectly via
    run_fix_workflow.  These tests set that input explicitly at the unit boundary
    (patch run_fix_workflow) and assert the aggregate success_count returned.
    """

    def test_success_count_is_one_when_single_non_interactive_fix_succeeds(
        self, cli, sample_error
    ):
        """
        Guards against: success_count not incremented when run_fix_workflow returns True.

        When run_fix_workflow returns True for one error in non-interactive mode,
        _process_all_errors must return success_count == 1.

        RED: currently returns success_count == 0 because _process_non_interactive_error
        discards the return value of run_fix_workflow (cli.py:463-470).
        """
        with patch.object(CLI, "run_fix_workflow", return_value=True):
            total, success = cli._process_all_errors([sample_error], interactive=False)

        assert total == 1
        assert success == 1  # RED: currently 0

    def test_success_count_is_zero_when_single_non_interactive_fix_fails(
        self, cli, sample_error
    ):
        """
        Guards against: success_count incremented even when run_fix_workflow returns False.

        When run_fix_workflow returns False, success_count must remain 0.

        This test passes even with the bug (success_count is always 0), so it serves
        as a contract pin for the failure case once the fix is applied.
        """
        with patch.object(CLI, "run_fix_workflow", return_value=False):
            total, success = cli._process_all_errors([sample_error], interactive=False)

        assert total == 1
        assert success == 0  # GREEN even with bug; pins the correct failure-case value

    def test_success_count_tracks_partial_successes_across_multiple_errors(
        self, cli, sample_error
    ):
        """
        Guards against: success_count not tracking mixed fix outcomes.

        With 3 errors where the first and third succeed and the second fails,
        success_count must be 2.

        RED: currently returns success_count == 0 for all outcomes.
        """
        outcomes = [True, False, True]
        with patch.object(CLI, "run_fix_workflow", side_effect=outcomes):
            total, success = cli._process_all_errors(
                [sample_error, sample_error, sample_error], interactive=False
            )

        assert total == 3
        assert success == 2  # RED: currently 0

    def test_success_count_equals_total_when_all_fixes_succeed(
        self, cli, sample_error
    ):
        """
        Guards against: success_count != total_processed when all fixes succeed.

        When every fix succeeds, success_count must equal total_processed so that
        the caller (process_errors) can return exit-code 0.

        RED: currently success_count == 0 while total_processed == 2.
        """
        with patch.object(CLI, "run_fix_workflow", return_value=True):
            total, success = cli._process_all_errors(
                [sample_error, sample_error], interactive=False
            )

        assert total == success  # RED: 2 != 0


# ---------------------------------------------------------------------------
# Integration layer: process_errors exit code
# Asserts the exit-code produced when the caller-supplied fix outcomes are
# provided via run_fix_workflow (not mocked at _process_all_errors level).
# ---------------------------------------------------------------------------


class TestProcessErrorsExitCode:
    """
    Guards against: process_errors always returning exit-code 1 when fixes succeed.

    process_errors returns 0 only when success_count == total_processed (cli.py:509).
    Because success_count never grows past 0, the condition is only ever true when
    total_processed == 0 (nothing was processed), which returns 1 anyway via the
    earlier guard (cli.py:504).
    """

    def test_exit_code_0_when_all_fixes_succeed_non_interactive(
        self, cli, sample_error
    ):
        """
        Guards against: exit-code 1 returned even when every fix succeeded.

        When run_fix_workflow returns True for every error in non-interactive mode,
        process_errors must return 0.

        RED: currently returns 1 because success_count stays 0, so
        0 == total_processed evaluates to False.
        """
        with (
            patch.object(CLI, "setup_signal_handlers", return_value=None),
            patch.object(CLI, "run_fix_workflow", return_value=True),
            patch.object(CLI, "cleanup", return_value=None),
        ):
            result = cli.process_errors([sample_error], interactive=False)

        assert result == 0  # RED: currently 1

    def test_exit_code_1_when_all_fixes_fail_non_interactive(
        self, cli, sample_error
    ):
        """
        Guards against: exit-code 0 returned when all fixes failed.

        When run_fix_workflow returns False for every error, process_errors must
        return 1.

        GREEN even with the bug (success_count stays 0, so 0 != 1 → returns 1).
        Pins the correct failure-case contract.
        """
        with (
            patch.object(CLI, "setup_signal_handlers", return_value=None),
            patch.object(CLI, "run_fix_workflow", return_value=False),
            patch.object(CLI, "cleanup", return_value=None),
        ):
            result = cli.process_errors([sample_error], interactive=False)

        assert result == 1  # GREEN; pins failure-case exit code

    def test_exit_code_1_when_partial_fixes_succeed_non_interactive(
        self, cli, sample_error
    ):
        """
        Guards against: exit-code 0 when only some fixes succeeded.

        With 2 errors where one succeeds and one fails, process_errors must return 1
        (partial success is still failure from the caller's perspective).

        RED for the wrong reason: with the bug, this returns 1 because
        success_count stays 0 (not because 1 != 2). After the fix, it should
        still return 1 because success_count (1) != total_processed (2).
        """
        outcomes = [True, False]
        with (
            patch.object(CLI, "setup_signal_handlers", return_value=None),
            patch.object(CLI, "run_fix_workflow", side_effect=outcomes),
            patch.object(CLI, "cleanup", return_value=None),
        ):
            result = cli.process_errors(
                [sample_error, sample_error], interactive=False
            )

        assert result == 1  # GREEN (currently and after fix); pins partial-success → 1
