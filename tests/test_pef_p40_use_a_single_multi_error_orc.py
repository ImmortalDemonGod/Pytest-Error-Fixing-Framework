"""RED test for finding F16/F82.

Bug: src/branch_fixer/utils/cli.py:210 — `_generate_and_apply_fix` calls
`self.orchestrator.start_session([error])` on every invocation. Because
`_process_all_errors` calls `_generate_and_apply_fix` once per error in its
loop, a run over N errors creates N orchestrator sessions instead of the one
session the orchestrator was designed to track multi-error state through.
"""
from pathlib import Path
from unittest.mock import Mock

import pytest

from branch_fixer.core.models import ErrorDetails, TestError
from branch_fixer.utils.cli import CLI


def _make_error(name):
    return TestError(
        test_file=Path(f"test_{name}.py"),
        test_function=f"test_{name}",
        error_details=ErrorDetails(error_type="AssertionError", message="assert failed"),
    )


@pytest.fixture
def cli():
    return CLI()


@pytest.fixture
def mock_service():
    svc = Mock()
    git_repo = Mock()
    git_repo.main_branch = "main"
    git_repo.get_current_branch = Mock(return_value="main")
    git_repo.run_command = Mock(return_value=None)
    git_repo.create_pull_request_sync = Mock(return_value=True)
    git_repo.push = Mock(return_value=True)
    branch_manager = Mock()
    branch_manager.create_fix_branch = Mock(return_value=True)
    branch_manager.cleanup_fix_branch = Mock(return_value=True)
    git_repo.branch_manager = branch_manager
    svc.git_repo = git_repo
    return svc


class TestMultiErrorRunUsesSingleOrchestratorSession:
    def test_process_errors_over_multiple_errors_starts_one_orchestrator_session(
        self, cli, mock_service
    ):
        """A run over N errors must use one session id: start_session should be
        called exactly once for the whole run, not once per error."""
        errors = [_make_error("a"), _make_error("b"), _make_error("c")]

        mock_orch = Mock()
        mock_orch.fix_error = Mock(return_value=True)

        cli.service = mock_service
        cli.orchestrator = mock_orch

        from unittest.mock import patch

        with patch.object(CLI, "setup_signal_handlers", return_value=None):
            cli.process_errors(errors, interactive=False)

        assert mock_orch.start_session.call_count == 1, (
            "a run over N errors must reuse a single orchestrator session, but "
            f"start_session was called {mock_orch.start_session.call_count} times "
            f"for {len(errors)} errors"
        )
