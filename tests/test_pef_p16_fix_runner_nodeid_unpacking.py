"""RED test for finding pef-p16-fix-runner-nodeid-unpacking (F1, F2).

F1: PytestRunner.format_test_failures() must not raise when a failed test's
    nodeid has no '::' separator; it should still produce a report line.
F2: A @pytest.mark.skip test must be counted into SessionResult.skipped,
    not SessionResult.passed.
"""
from datetime import datetime
from pathlib import Path

from _pytest.main import ExitCode

from branch_fixer.services.pytest.runner import PytestRunner
from branch_fixer.services.pytest.models import SessionResult, TestResult


def test_format_test_failures_nodeid_without_double_colons_handled_gracefully():
    runner = PytestRunner(working_dir=Path.cwd())
    sess = SessionResult(
        start_time=datetime.now(),
        end_time=datetime.now(),
        duration=0.0,
        exit_code=ExitCode.OK,
    )
    no_colon_id = "no_colon_id"
    tr = TestResult(
        nodeid=no_colon_id,
        test_file=Path("file"),
        test_function=None,
        error_message=None,
        longrepr=None,
    )
    tr.failed = True
    sess.test_results = {tr.nodeid: tr}
    runner._current_session = sess

    lines = runner.format_test_failures()

    assert any(no_colon_id in line for line in lines)


def test_marker_skip_counted_as_skipped_not_passed(tmp_path):
    test_path = tmp_path / "test_skip_marker.py"
    test_path.write_text(
        "import pytest\n"
        "\n"
        "@pytest.mark.skip(reason='deliberately skipped')\n"
        "def test_skipped_case():\n"
        "    assert False\n"
    )

    runner = PytestRunner(working_dir=tmp_path)
    session = runner.run_test(test_path=test_path)

    assert session.skipped == 1
    assert session.passed == 0
