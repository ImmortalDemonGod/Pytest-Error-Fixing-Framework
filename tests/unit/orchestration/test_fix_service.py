"""Tests for FixService — single-error fix orchestration, backup restore, session updates."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from branch_fixer.core.models import CodeChanges, ErrorDetails, TestError
from branch_fixer.orchestration.exceptions import FixServiceError
from branch_fixer.orchestration.fix_service import FixService
from branch_fixer.orchestration.orchestrator import FixSession, FixSessionState
from branch_fixer.storage.state_manager import StateManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_error(tmp_path: Path, name: str = "test_foo") -> TestError:
    f = tmp_path / f"{name}.py"
    f.write_text("def test_foo():\n    assert False\n")
    return TestError(
        test_file=f,
        test_function=name,
        error_details=ErrorDetails(error_type="AssertionError", message="fail"),
    )


def make_service(
    ai_success=True,
    apply_success=True,
    verify_success=True,
    dev_force_success=False,
    session=None,
    session_store=None,
    state_manager=None,
) -> FixService:
    ai = MagicMock()
    ai.generate_fix.return_value = CodeChanges(original_code="old", modified_code="new")

    applier = MagicMock()
    applier.apply_changes_with_backup.return_value = (apply_success, Path("/tmp/backup.bak"))
    applier.restore_backup.return_value = True

    runner = MagicMock()
    runner.verify_fix.return_value = verify_success

    git = MagicMock()

    with patch("branch_fixer.orchestration.fix_service.WorkspaceValidator") as mock_wv:
        mock_wv.return_value.validate_workspace.return_value = None
        mock_wv.return_value.check_dependencies.return_value = None
        svc = FixService(
            ai_manager=ai,
            test_runner=runner,
            change_applier=applier,
            git_repo=git,
            dev_force_success=dev_force_success,
            session=session,
            session_store=session_store,
            state_manager=state_manager,
        )
    svc.validator = MagicMock()
    svc.validator.validate_workspace.return_value = None
    svc.validator.check_dependencies.return_value = None
    return svc


# ---------------------------------------------------------------------------
# __init__ parameter validation
# ---------------------------------------------------------------------------

class TestInit:
    def test_rejects_zero_max_retries(self):
        with pytest.raises(ValueError):
            FixService(
                ai_manager=MagicMock(), test_runner=MagicMock(),
                change_applier=MagicMock(), git_repo=MagicMock(),
                max_retries=0,
            )

    def test_rejects_negative_max_retries(self):
        with pytest.raises(ValueError):
            FixService(
                ai_manager=MagicMock(), test_runner=MagicMock(),
                change_applier=MagicMock(), git_repo=MagicMock(),
                max_retries=-1,
            )

    def test_rejects_initial_temp_below_zero(self):
        with pytest.raises(ValueError):
            FixService(
                ai_manager=MagicMock(), test_runner=MagicMock(),
                change_applier=MagicMock(), git_repo=MagicMock(),
                initial_temp=-0.1,
            )

    def test_rejects_initial_temp_above_one(self):
        with pytest.raises(ValueError):
            FixService(
                ai_manager=MagicMock(), test_runner=MagicMock(),
                change_applier=MagicMock(), git_repo=MagicMock(),
                initial_temp=1.1,
            )

    def test_rejects_zero_temp_increment(self):
        with pytest.raises(ValueError):
            FixService(
                ai_manager=MagicMock(), test_runner=MagicMock(),
                change_applier=MagicMock(), git_repo=MagicMock(),
                temp_increment=0,
            )


# ---------------------------------------------------------------------------
# attempt_fix — happy path
# ---------------------------------------------------------------------------

class TestAttemptFixSuccess:
    def test_returns_true_on_success(self, tmp_path):
        svc = make_service()
        error = make_error(tmp_path)
        assert svc.attempt_fix(error, temperature=0.4) is True

    def test_marks_error_as_fixed(self, tmp_path):
        svc = make_service()
        error = make_error(tmp_path)
        svc.attempt_fix(error, temperature=0.4)
        assert error.status == "fixed"

    def test_creates_fix_attempt(self, tmp_path):
        svc = make_service()
        error = make_error(tmp_path)
        svc.attempt_fix(error, temperature=0.4)
        assert len(error.fix_attempts) == 1


# ---------------------------------------------------------------------------
# attempt_fix — apply failure
# ---------------------------------------------------------------------------

class TestAttemptFixApplyFailure:
    def test_returns_false_when_apply_fails(self, tmp_path):
        svc = make_service(apply_success=False)
        error = make_error(tmp_path)
        assert svc.attempt_fix(error, temperature=0.4) is False

    def test_marks_attempt_failed_when_apply_fails(self, tmp_path):
        svc = make_service(apply_success=False)
        error = make_error(tmp_path)
        svc.attempt_fix(error, temperature=0.4)
        assert error.fix_attempts[0].status == "failed"


# ---------------------------------------------------------------------------
# attempt_fix — verify failure triggers restore
# ---------------------------------------------------------------------------

class TestAttemptFixVerifyFailure:
    def test_returns_false_when_verify_fails(self, tmp_path):
        svc = make_service(verify_success=False)
        error = make_error(tmp_path)
        assert svc.attempt_fix(error, temperature=0.4) is False

    def test_restore_called_when_verify_fails(self, tmp_path):
        svc = make_service(verify_success=False)
        error = make_error(tmp_path)
        svc.attempt_fix(error, temperature=0.4)
        svc.change_applier.restore_backup.assert_called_once()

    def test_restore_called_when_verify_raises(self, tmp_path):
        svc = make_service()
        svc.test_runner.verify_fix.side_effect = RuntimeError("runner crashed")
        error = make_error(tmp_path)
        with pytest.raises(FixServiceError):
            svc.attempt_fix(error, temperature=0.4)
        svc.change_applier.restore_backup.assert_called_once()

    def test_error_not_marked_fixed_when_verify_fails(self, tmp_path):
        svc = make_service(verify_success=False)
        error = make_error(tmp_path)
        svc.attempt_fix(error, temperature=0.4)
        assert error.status != "fixed"


# ---------------------------------------------------------------------------
# attempt_fix — workspace failure
# ---------------------------------------------------------------------------

class TestAttemptFixWorkspaceFailure:
    def test_raises_fix_service_error_on_workspace_failure(self, tmp_path):
        svc = make_service()
        svc.validator.validate_workspace.side_effect = RuntimeError("bad workspace")
        error = make_error(tmp_path)
        with pytest.raises(FixServiceError):
            svc.attempt_fix(error, temperature=0.4)


# ---------------------------------------------------------------------------
# attempt_manual_fix
# ---------------------------------------------------------------------------

class TestAttemptManualFix:
    def test_returns_true_when_test_passes(self, tmp_path):
        svc = make_service(verify_success=True)
        error = make_error(tmp_path)
        assert svc.attempt_manual_fix(error) is True

    def test_marks_error_fixed_when_test_passes(self, tmp_path):
        svc = make_service(verify_success=True)
        error = make_error(tmp_path)
        svc.attempt_manual_fix(error)
        assert error.status == "fixed"

    def test_returns_false_when_test_fails(self, tmp_path):
        svc = make_service(verify_success=False)
        error = make_error(tmp_path)
        assert svc.attempt_manual_fix(error) is False

    def test_does_not_mark_fixed_when_test_fails(self, tmp_path):
        svc = make_service(verify_success=False)
        error = make_error(tmp_path)
        svc.attempt_manual_fix(error)
        assert error.status != "fixed"


# ---------------------------------------------------------------------------
# _update_session_if_present
# ---------------------------------------------------------------------------

class TestUpdateSessionIfPresent:
    def test_no_session_is_noop(self, tmp_path):
        svc = make_service()
        error = make_error(tmp_path)
        # Should not raise
        svc._update_session_if_present(error)

    def test_fixed_error_added_to_completed(self, tmp_path):
        session = FixSession()
        error = make_error(tmp_path)
        session.errors = [error]
        svc = make_service(session=session)
        attempt = error.start_fix_attempt(0.4)
        error.mark_fixed(attempt)
        svc._update_session_if_present(error)
        assert error in session.completed_errors

    def test_not_added_twice(self, tmp_path):
        session = FixSession()
        error = make_error(tmp_path)
        session.errors = [error]
        svc = make_service(session=session)
        attempt = error.start_fix_attempt(0.4)
        error.mark_fixed(attempt)
        svc._update_session_if_present(error)
        svc._update_session_if_present(error)
        assert session.completed_errors.count(error) == 1

    def test_session_store_saved_when_present(self, tmp_path):
        session = FixSession()
        mock_store = MagicMock()
        error = make_error(tmp_path)
        session.errors = [error]
        svc = make_service(session=session, session_store=mock_store)
        svc._update_session_if_present(error)
        mock_store.save_session.assert_called_once_with(session)
