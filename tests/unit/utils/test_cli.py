import os
import signal
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from branch_fixer.utils.cli import CLI, ComponentSettings
from branch_fixer.core.models import TestError, ErrorDetails


# Module-level fixtures
@pytest.fixture
def cli():
    return CLI()


@pytest.fixture
def test_file(tmp_path):
    p = tmp_path / "test_sample.py"
    p.write_text("def test_dummy():\n    assert True\n", encoding="utf-8")
    return p


@pytest.fixture
def sample_error(test_file):
    details = ErrorDetails(error_type="AssertionError", message="assert failed", stack_trace=None)
    return TestError(test_file=test_file, test_function="test_dummy", error_details=details)


@pytest.fixture
def mock_service():
    svc = Mock()
    # git_repo with nested branch_manager
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
    svc.initial_temp = 0.5
    svc.attempt_fix = Mock(return_value=True)
    svc.attempt_manual_fix = Mock(return_value=True)
    svc.validator = Mock()
    svc.validator.validate_workspace = Mock()
    svc.validator.check_dependencies = Mock()
    return svc


class TestComponentSettings:
    def test_default_values(self):
        cfg = ComponentSettings(api_key="secret-key")
        assert cfg.api_key == "secret-key"
        assert cfg.max_retries == 3
        assert pytest.approx(cfg.initial_temp, 0.001) == 0.5
        assert pytest.approx(cfg.temp_increment, 0.001) == 0.1
        assert cfg.dev_force_success is False

    def test_custom_values(self):
        cfg = ComponentSettings(
            api_key="abc",
            max_retries=7,
            initial_temp=0.2,
            temp_increment=0.05,
            dev_force_success=True,
        )
        assert cfg.api_key == "abc"
        assert cfg.max_retries == 7
        assert cfg.initial_temp == 0.2
        assert cfg.temp_increment == 0.05
        assert cfg.dev_force_success is True


class TestCLI:
    # Happy path: initialization
    def test_cli_init_defaults(self, cli):
        assert cli.service is None
        assert cli.orchestrator is None
        assert isinstance(cli.created_branches, set)
        assert cli._exit_requested is False

    # setup_signal_handlers
    def test_setup_signal_handlers_registers_and_handler_sets_flag(self, cli):
        captured = {}

        def fake_signal(sig, handler):
            # store handler associated with signal name to allow calling it
            captured[sig] = handler

        with patch("branch_fixer.utils.cli.signal.signal", side_effect=fake_signal) as _:
            cli.setup_signal_handlers()
            # Ensure both SIGINT and SIGTERM registered
            assert signal.SIGINT in captured
            assert signal.SIGTERM in captured

            # Call the handler to simulate signal delivery
            handler = captured[signal.SIGINT]
            # before invoking, flag false
            assert not cli._exit_requested
            # invoke handler
            handler(None, None)
            assert cli._exit_requested is True

    # _cleanup_branches
    def test__cleanup_branches_success(self, cli, mock_service):
        cli.service = mock_service
        cli.created_branches.add("fix-something-1")
        errors = []
        cli._cleanup_branches(errors)
        mock_service.git_repo.branch_manager.cleanup_fix_branch.assert_called_with("fix-something-1", force=True)
        assert errors == []

    def test__cleanup_branches_failure_appends_error(self, cli, mock_service, caplog):
        # make cleanup raise
        def raise_err(*args, **kwargs):
            raise RuntimeError("boom")
        mock_service.git_repo.branch_manager.cleanup_fix_branch.side_effect = raise_err
        cli.service = mock_service
        cli.created_branches.add("fix-somefail")
        errors = []
        cli._cleanup_branches(errors)
        assert errors, "errors list should have been appended to"
        assert any("Failed to cleanup branch fix-somefail" in e for e in errors)

    # _checkout_main
    def test__checkout_main_success(self, cli, mock_service):
        cli.service = mock_service
        errors = []
        cli._checkout_main(errors)
        mock_service.git_repo.run_command.assert_called_with(["checkout", mock_service.git_repo.main_branch])
        assert errors == []

    def test__checkout_main_run_command_raises_appends_error(self, cli, mock_service):
        def raise_cmd(*args, **kwargs):
            raise RuntimeError("nope")
        mock_service.git_repo.run_command.side_effect = raise_cmd
        cli.service = mock_service
        errors = []
        cli._checkout_main(errors)
        assert errors
        assert "Failed to checkout main branch" in errors[0]

    # _create_fix_branch
    def test__create_fix_branch_success(self, cli, sample_error, mock_service):
        cli.service = mock_service
        # Make uuid deterministic
        with patch("branch_fixer.utils.cli.uuid.uuid4", return_value=Mock(__str__=lambda self: "deadbeef12345678")):
            branch = cli._create_fix_branch(sample_error)
            assert branch is not None
            assert branch in cli.created_branches
            mock_service.git_repo.branch_manager.create_fix_branch.assert_called_with(branch)

    def test__create_fix_branch_returns_none_when_create_fails(self, cli, sample_error, mock_service):
        mock_service.git_repo.branch_manager.create_fix_branch.return_value = False
        cli.service = mock_service
        branch = cli._create_fix_branch(sample_error)
        assert branch is None

    def test__create_fix_branch_handles_exception_and_returns_none(self, cli, sample_error, mock_service):
        def raise_err(*args, **kwargs):
            raise RuntimeError("boom")
        mock_service.git_repo.branch_manager.create_fix_branch.side_effect = raise_err
        cli.service = mock_service
        branch = cli._create_fix_branch(sample_error)
        assert branch is None

    def test__create_fix_branch_with_no_service_returns_none(self, cli, sample_error):
        cli.service = None
        branch = cli._create_fix_branch(sample_error)
        assert branch is None

    # _generate_and_apply_fix
    def test__generate_and_apply_fix_success(self, cli, sample_error, mock_service):
        mock_service.attempt_fix.return_value = True
        cli.service = mock_service
        assert cli._generate_and_apply_fix(sample_error) is True

    def test__generate_and_apply_fix_failure_returns_false(self, cli, sample_error, mock_service):
        mock_service.attempt_fix.return_value = False
        cli.service = mock_service
        assert cli._generate_and_apply_fix(sample_error) is False

    def test__generate_and_apply_fix_no_service_returns_false(self, cli, sample_error):
        cli.service = None
        assert cli._generate_and_apply_fix(sample_error) is False

    def test__generate_and_apply_fix_attempt_raises_propagates(self, cli, sample_error, mock_service):
        def raise_err(*args, **kwargs):
            raise ValueError("boom")
        mock_service.attempt_fix.side_effect = raise_err
        cli.service = mock_service
        with pytest.raises(ValueError):
            cli._generate_and_apply_fix(sample_error)

    # _create_and_push_pr
    def test__create_and_push_pr_pr_and_push_success(self, cli, sample_error, mock_service):
        cli.service = mock_service
        mock_service.git_repo.create_pull_request_sync.return_value = True
        mock_service.git_repo.push.return_value = True
        res = cli._create_and_push_pr("fix-branch", sample_error)
        assert res is True
        mock_service.git_repo.create_pull_request_sync.assert_called_with("fix-branch", sample_error)
        mock_service.git_repo.push.assert_called_with("fix-branch")

    def test__create_and_push_pr_pr_success_push_fails(self, cli, sample_error, mock_service):
        cli.service = mock_service
        mock_service.git_repo.create_pull_request_sync.return_value = True
        mock_service.git_repo.push.return_value = False
        res = cli._create_and_push_pr("fix-branch", sample_error)
        assert res is False

    def test__create_and_push_pr_pr_creation_returns_false_considered_success(self, cli, sample_error, mock_service):
        cli.service = mock_service
        mock_service.git_repo.create_pull_request_sync.return_value = False
        res = cli._create_and_push_pr("fix-branch", sample_error)
        assert res is True

    def test__create_and_push_pr_pr_creation_raises_propagates(self, cli, sample_error, mock_service):
        def raise_err(*args, **kwargs):
            raise RuntimeError("pr failed")
        mock_service.git_repo.create_pull_request_sync.side_effect = raise_err
        cli.service = mock_service
        with pytest.raises(RuntimeError):
            cli._create_and_push_pr("fix-branch", sample_error)

    # run_fix_workflow - high level flows
    def test_run_fix_workflow_no_service_returns_false(self, cli, sample_error):
        cli.service = None
        assert cli.run_fix_workflow(sample_error, interactive=False) is False

    def test_run_fix_workflow_branch_creation_fails_returns_false(self, cli, sample_error, mock_service):
        cli.service = mock_service
        # ensure create_fix_branch returns None
        with patch.object(CLI, "_create_fix_branch", return_value=None):
            # get_current_branch will be called at start; ensure consistent returns
            mock_service.git_repo.get_current_branch.return_value = "main"
            res = cli.run_fix_workflow(sample_error, interactive=False)
            assert res is False

    def test_run_fix_workflow_noninteractive_success_checks_out_original_branch(self, cli, sample_error, mock_service):
        cli.service = mock_service
        # patch create_fix_branch and generate/apply and create_and_push_pr
        with patch.object(CLI, "_create_fix_branch", return_value="fix-branch") as p1, \
             patch.object(CLI, "_generate_and_apply_fix", return_value=True) as p2, \
             patch.object(CLI, "_create_and_push_pr", return_value=True) as p3:
            # make get_current_branch return original then different current branch to trigger checkout in finally
            mock_service.git_repo.get_current_branch.side_effect = ["main", "fix-branch"]
            res = cli.run_fix_workflow(sample_error, interactive=False)
            assert res is True
            mock_service.git_repo.run_command.assert_called_with(["checkout", "main"])

    def test_run_fix_workflow_interactive_user_declines_pr_returns_true(self, cli, sample_error, mock_service):
        cli.service = mock_service
        with patch.object(CLI, "_create_fix_branch", return_value="fix-branch"), \
             patch.object(CLI, "_generate_and_apply_fix", return_value=True), \
             patch("branch_fixer.utils.cli.click.confirm", return_value=False) as mock_confirm, \
             patch.object(CLI, "_create_and_push_pr", return_value=True) as mock_pr:
            # user declines, so _create_and_push_pr should NOT be called
            mock_service.git_repo.get_current_branch.side_effect = ["main", "main"]
            res = cli.run_fix_workflow(sample_error, interactive=True)
            assert res is True
            mock_confirm.assert_called_once()
            mock_pr.assert_not_called()

    def test_run_fix_workflow_generate_apply_raises_returns_false_and_attempts_checkout(self, cli, sample_error, mock_service):
        cli.service = mock_service
        with patch.object(CLI, "_create_fix_branch", return_value="fix-branch"), \
             patch.object(CLI, "_generate_and_apply_fix", side_effect=RuntimeError("boom")):
            # get_current_branch returns main then different to force checkout attempt
            mock_service.git_repo.get_current_branch.side_effect = ["main", "fix-branch"]
            res = cli.run_fix_workflow(sample_error, interactive=False)
            assert res is False
            mock_service.git_repo.run_command.assert_called_with(["checkout", "main"])

    # run_manual_fix_workflow
    def test_run_manual_fix_workflow_branch_creation_fails_returns_skip(self, cli, sample_error):
        with patch.object(CLI, "_create_fix_branch", return_value=None):
            res = cli.run_manual_fix_workflow(sample_error)
            assert res == "skip"

    def test_run_manual_fix_workflow_user_skips(self, cli, sample_error, mock_service):
        cli.service = mock_service
        with patch.object(CLI, "_create_fix_branch", return_value="fix-branch"), \
             patch("branch_fixer.utils.cli.click.prompt", return_value="s"):
            res = cli.run_manual_fix_workflow(sample_error)
            assert res == "skip"

    def test_run_manual_fix_workflow_user_quits(self, cli, sample_error, mock_service, capsys):
        cli.service = mock_service
        with patch.object(CLI, "_create_fix_branch", return_value="fix-branch"), \
             patch("branch_fixer.utils.cli.click.prompt", return_value="q"):
            res = cli.run_manual_fix_workflow(sample_error)
            assert res == "quit"

    def test_run_manual_fix_workflow_user_fixes_on_first_try(self, cli, sample_error, mock_service, capsys):
        cli.service = mock_service
        mock_service.attempt_manual_fix.return_value = True
        with patch.object(CLI, "_create_fix_branch", return_value="fix-branch"), \
             patch("branch_fixer.utils.cli.click.prompt", return_value=""):
            res = cli.run_manual_fix_workflow(sample_error)
            assert res == "fixed"

    def test_run_manual_fix_workflow_retries_then_quit(self, cli, sample_error, mock_service):
        cli.service = mock_service
        mock_service.attempt_manual_fix.return_value = False
        # click.prompt should be called multiple times; simulate Enter five times
        prompts = ["", "", "", "", ""]
        with patch.object(CLI, "_create_fix_branch", return_value="fix-branch"), \
             patch("branch_fixer.utils.cli.click.prompt", side_effect=prompts):
            res = cli.run_manual_fix_workflow(sample_error)
            assert res == "quit"

    # setup_components - success and failure paths
    def test_setup_components_success_initializes_and_returns_true(self, cli, tmp_path):
        cfg = ComponentSettings(api_key="k1", max_retries=2, initial_temp=0.3, temp_increment=0.1, dev_force_success=False)
        # Patch all heavy constructors to simple mocks
        with patch("branch_fixer.utils.cli.AIManager", return_value=Mock()) as mock_ai, \
             patch("branch_fixer.services.pytest.runner.TestRunner", return_value=Mock()) as mock_tr, \
             patch("branch_fixer.services.code.change_applier.ChangeApplier", return_value=Mock()) as mock_ca, \
             patch("branch_fixer.utils.cli.GitRepository", return_value=Mock()) as mock_git, \
             patch("branch_fixer.storage.state_manager.StateManager", return_value=Mock()) as mock_sm, \
             patch("branch_fixer.utils.cli.FixService", return_value=Mock()) as mock_fs, \
             patch("branch_fixer.orchestration.orchestrator.FixOrchestrator", return_value=Mock()) as mock_orch, \
             patch("branch_fixer.storage.session_store.SessionStore", return_value=Mock()) as mock_store:
            # Ensure cwd is a writable tmp path for session_data creation
            cwd = tmp_path / "cwd"
            cwd.mkdir()
            monkey_chdir = patch("branch_fixer.utils.cli.Path.cwd", return_value=cwd)
            with monkey_chdir:
                res = cli.setup_components(cfg)
            assert res is True
            assert cli.service is not None
            assert cli.orchestrator is not None

    def test_setup_components_ai_init_failure_returns_false(self, cli, tmp_path):
        cfg = ComponentSettings(api_key="k1")
        with patch("branch_fixer.utils.cli.AIManager", side_effect=RuntimeError("ai fail")), \
             patch("branch_fixer.services.pytest.runner.TestRunner", return_value=Mock()), \
             patch("branch_fixer.services.code.change_applier.ChangeApplier", return_value=Mock()), \
             patch("branch_fixer.utils.cli.GitRepository", return_value=Mock()), \
             patch("branch_fixer.storage.state_manager.StateManager", return_value=Mock()), \
             patch("branch_fixer.orchestration.orchestrator.FixOrchestrator", return_value=Mock()), \
             patch("branch_fixer.storage.session_store.SessionStore", return_value=Mock()):
            res = cli.setup_components(cfg)
            assert res is False
            assert cli.service is None

    # simple handlers
    def test_handle_quit_choice_returns_false_and_echoes(self, cli, sample_error, capsys):
        res = cli._handle_quit_choice(sample_error)
        assert res is False

    def test_handle_skip_choice_returns_true_and_echoes(self, cli, sample_error):
        res = cli._handle_skip_choice(sample_error)
        assert res is True

    def test_handle_manual_fix_choice_fixed_returns_true(self, cli, sample_error):
        with patch.object(CLI, "run_manual_fix_workflow", return_value="fixed"):
            res = cli._handle_manual_fix_choice(sample_error)
            assert res is True

    def test_handle_manual_fix_choice_quit_returns_false(self, cli, sample_error):
        with patch.object(CLI, "run_manual_fix_workflow", return_value="quit"):
            res = cli._handle_manual_fix_choice(sample_error)
            assert res is False

    def test_handle_ai_fix_choice_success_and_failure(self, cli, sample_error):
        with patch.object(CLI, "run_fix_workflow", return_value=True):
            res = cli._handle_ai_fix_choice(sample_error)
            assert res is True
        with patch.object(CLI, "run_fix_workflow", return_value=False):
            res = cli._handle_ai_fix_choice(sample_error)
            assert res is True

    # _prompt_for_fix
    @pytest.mark.parametrize("choice_input, expected", [
        ("\n", "y"),
        ("", "y"),
        ("y", "y"),
        ("M", "m"),
        ("n", "n"),
        ("q", "q"),
    ])
    def test__prompt_for_fix_accepts_valid_inputs(self, cli, sample_error, choice_input, expected):
        # patch getchar and clear to avoid terminal side effects
        with patch("branch_fixer.utils.cli.click.getchar", return_value=choice_input), \
             patch("branch_fixer.utils.cli.click.clear", return_value=None):
            result = cli._prompt_for_fix(sample_error)
            assert result == expected

    def test__prompt_for_fix_invalid_then_valid(self, cli, sample_error):
        inputs = ["x", "\n"]
        gen = (i for i in inputs)

        def getchar_prompt(prompt=None):
            return next(gen)

        with patch("branch_fixer.utils.cli.click.getchar", side_effect=getchar_prompt), \
             patch("branch_fixer.utils.cli.click.clear", return_value=None):
            result = cli._prompt_for_fix(sample_error)
            assert result == "y"

    # _process_interactive_error
    def test__process_interactive_error_calls_correct_handler(self, cli, sample_error):
        with patch.object(CLI, "_prompt_for_fix", return_value="q"), \
             patch.object(CLI, "_handle_quit_choice", return_value=False) as hq:
            res = cli._process_interactive_error(sample_error)
            assert res is False
            hq.assert_called_once_with(sample_error)

        with patch.object(CLI, "_prompt_for_fix", return_value="n"), \
             patch.object(CLI, "_handle_skip_choice", return_value=True) as hs:
            res = cli._process_interactive_error(sample_error)
            assert res is True
            hs.assert_called_once_with(sample_error)

        with patch.object(CLI, "_prompt_for_fix", return_value="z"), \
             patch.object(CLI, "_handle_ai_fix_choice", return_value=True) as hai:
            res = cli._process_interactive_error(sample_error)
            assert res is True
            hai.assert_called_once_with(sample_error)

    # _process_non_interactive_error
    def test__process_non_interactive_error_prints_messages(self, cli, sample_error):
        with patch.object(CLI, "run_fix_workflow", return_value=True):
            cli._process_non_interactive_error(sample_error)
        with patch.object(CLI, "run_fix_workflow", return_value=False):
            cli._process_non_interactive_error(sample_error)

    # process_errors and helper _process_all_errors and _summarize_results
    def test__process_all_errors_noninteractive_iterates_all(self, cli, sample_error):
        errors = [sample_error, sample_error, sample_error]
        with patch.object(CLI, "_process_non_interactive_error", return_value=None) as pn:
            total_processed, success_count = cli._process_all_errors(errors, interactive=False)
            assert total_processed == 3
            assert success_count == 0
            assert pn.call_count == 3

    def test__process_all_errors_interactive_breaks_on_quit(self, cli, sample_error):
        errors = [sample_error, sample_error]
        with patch.object(CLI, "_process_interactive_error", return_value=False) as pi:
            total_processed, success_count = cli._process_all_errors(errors, interactive=True)
            # first interactive returns False so loop breaks before increment
            assert total_processed == 0
            assert success_count == 0
            pi.assert_called_once()

    def test_process_errors_calls_cleanup_in_finally(self, cli, sample_error):
        errors = [sample_error, sample_error]
        # patch setup_signal_handlers to no-op and _process_all_errors to raise
        with patch.object(CLI, "setup_signal_handlers", return_value=None), \
             patch.object(CLI, "_process_all_errors", side_effect=RuntimeError("boom")), \
             patch.object(CLI, "cleanup", return_value=None) as mock_cleanup:
            with pytest.raises(RuntimeError):
                cli.process_errors(errors, interactive=False)
            # cleanup should have been called in finally
            mock_cleanup.assert_called_once()

    def test_process_errors_returns_0_when_all_processed_and_success_count_equal(self, cli, sample_error):
        errors = [sample_error, sample_error]
        with patch.object(CLI, "setup_signal_handlers", return_value=None), \
             patch.object(CLI, "_process_all_errors", return_value=(2, 2)), \
             patch.object(CLI, "_summarize_results", return_value=None), \
             patch.object(CLI, "cleanup", return_value=None):
            res = cli.process_errors(errors, interactive=False)
            assert res == 0

    def test_process_errors_returns_1_when_partial_or_mismatch(self, cli, sample_error):
        errors = [sample_error, sample_error, sample_error]
        # case: partial processed
        with patch.object(CLI, "setup_signal_handlers", return_value=None), \
             patch.object(CLI, "_process_all_errors", return_value=(1, 0)), \
             patch.object(CLI, "cleanup", return_value=None):
            res = cli.process_errors(errors, interactive=False)
            assert res == 1

    # _summarize_results
    def test__summarize_results_prints_expected_lines(self, cli, capsys):
        cli._summarize_results(total_processed=3, total_errors=5, success_count=2)
        out = capsys.readouterr().out
        assert "Fix attempts complete." in out
        assert "Tests processed: 3/5" in out
        assert "Successfully fixed: 2" in out
        assert "Failed/skipped: 1" in out

    # cleanup integration tests for when service is None vs present
    def test_cleanup_no_service_does_nothing(self, cli, capsys):
        cli.service = None
        # shouldn't raise
        cli.cleanup()
        out = capsys.readouterr().out
        # no "Cleaning up resources..." printed because early return
        assert "Cleaning up resources..." not in out

    def test_cleanup_with_service_calls_helpers(self, cli, mock_service, capsys):
        cli.service = mock_service
        cli.created_branches.add("fix-to-clean")
        # ensure branch cleanup and checkout succeed
        cli.cleanup()
        out = capsys.readouterr().out
        assert "Cleaning up resources..." in out
        assert "Cleanup completed successfully." in out or "Encountered errors during cleanup:" not in out

    # ensure _prompt_for_fix propagates exceptions from getchar
    def test__prompt_for_fix_getchar_raises_propagates(self, cli, sample_error):
        with patch("branch_fixer.utils.cli.click.getchar", side_effect=RuntimeError("no tty")):
            with pytest.raises(RuntimeError):
                cli._prompt_for_fix(sample_error)