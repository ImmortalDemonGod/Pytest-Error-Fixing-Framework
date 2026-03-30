"""Tests for FixOrchestrator — session lifecycle, retry logic, pause/resume, progress."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from branch_fixer.core.models import CodeChanges, ErrorDetails, TestError
from branch_fixer.orchestration.orchestrator import (
    FixOrchestrator,
    FixProgress,
    FixSession,
    FixSessionState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_error(name: str = "test_foo", tmp_path: Path = None) -> TestError:
    if tmp_path:
        f = tmp_path / f"{name}.py"
        f.write_text("def test_foo():\n    assert False\n")
        test_file = f
    else:
        test_file = Path(f"tests/{name}.py")
    return TestError(
        test_file=test_file,
        test_function=name,
        error_details=ErrorDetails(error_type="AssertionError", message="fail"),
    )


def make_orchestrator(fix_succeeds: bool = True, max_retries: int = 3) -> FixOrchestrator:
    """Build an orchestrator whose FixService mock always succeeds or always fails."""
    ai = MagicMock()
    ai.generate_fix.return_value = CodeChanges(original_code="old", modified_code="new")

    applier = MagicMock()
    applier.apply_changes_with_backup.return_value = (True, Path("/tmp/backup.bak"))
    applier.restore_backup.return_value = True

    runner = MagicMock()
    runner.verify_fix.return_value = fix_succeeds

    git = MagicMock()

    orch = FixOrchestrator(
        ai_manager=ai,
        test_runner=runner,
        change_applier=applier,
        git_repo=git,
        max_retries=max_retries,
        initial_temp=0.4,
        temp_increment=0.1,
    )
    return orch


# ---------------------------------------------------------------------------
# start_session
# ---------------------------------------------------------------------------

class TestStartSession:
    def test_raises_on_empty_errors(self):
        orch = make_orchestrator()
        with pytest.raises(ValueError):
            orch.start_session([])

    def test_returns_fix_session(self):
        orch = make_orchestrator()
        error = make_error()
        session = orch.start_session([error])
        assert isinstance(session, FixSession)

    def test_session_state_is_running(self):
        orch = make_orchestrator()
        error = make_error()
        session = orch.start_session([error])
        assert session.state == FixSessionState.RUNNING

    def test_session_contains_errors(self):
        orch = make_orchestrator()
        e1 = make_error("test_a")
        e2 = make_error("test_b")
        session = orch.start_session([e1, e2])
        assert len(session.errors) == 2

    def test_error_count_matches(self):
        orch = make_orchestrator()
        errors = [make_error(f"test_{i}") for i in range(5)]
        session = orch.start_session(errors)
        assert session.error_count == 5

    def test_second_start_replaces_session(self):
        orch = make_orchestrator()
        s1 = orch.start_session([make_error("test_a")])
        s2 = orch.start_session([make_error("test_b")])
        assert orch._session.id == s2.id


# ---------------------------------------------------------------------------
# run_session — session validation
# ---------------------------------------------------------------------------

class TestRunSessionValidation:
    def test_raises_if_session_not_started(self):
        orch = make_orchestrator()
        from uuid import uuid4
        with pytest.raises(RuntimeError):
            orch.run_session(uuid4())

    def test_raises_if_wrong_session_id(self):
        orch = make_orchestrator()
        from uuid import uuid4
        orch.start_session([make_error()])
        with pytest.raises(RuntimeError):
            orch.run_session(uuid4())

    def test_raises_if_session_not_running(self):
        orch = make_orchestrator()
        error = make_error()
        session = orch.start_session([error])
        session.state = FixSessionState.PAUSED
        with pytest.raises(RuntimeError):
            orch.run_session(session.id)


# ---------------------------------------------------------------------------
# run_session — outcomes
# ---------------------------------------------------------------------------

class TestRunSessionOutcomes:
    def test_returns_true_when_all_fixed(self):
        orch = make_orchestrator()
        error = make_error("test_foo")
        session = orch.start_session([error])
        # Mark fixed so run_session's status check sees it
        attempt = error.start_fix_attempt(0.4)
        error.mark_fixed(attempt)
        orch.fix_error = MagicMock(return_value=True)
        result = orch.run_session(session.id)
        assert result is True

    def test_session_state_completed_when_all_fixed(self):
        orch = make_orchestrator()
        error = make_error("test_foo")
        session = orch.start_session([error])
        attempt = error.start_fix_attempt(0.4)
        error.mark_fixed(attempt)
        orch.fix_error = MagicMock(return_value=True)
        orch.run_session(session.id)
        assert session.state == FixSessionState.COMPLETED

    def test_returns_false_when_any_unfixed(self):
        orch = make_orchestrator()
        error = make_error("test_foo")
        session = orch.start_session([error])
        orch.fix_error = MagicMock(return_value=False)
        result = orch.run_session(session.id)
        assert result is False

    def test_session_state_failed_when_unfixed(self):
        orch = make_orchestrator()
        error = make_error("test_foo")
        session = orch.start_session([error])
        orch.fix_error = MagicMock(return_value=False)
        orch.run_session(session.id)
        assert session.state == FixSessionState.FAILED

    def test_saves_to_session_store_on_completion(self):
        mock_store = MagicMock()
        orch = make_orchestrator()
        orch.session_store = mock_store
        error = make_error("test_foo")
        session = orch.start_session([error])
        attempt = error.start_fix_attempt(0.4)
        error.mark_fixed(attempt)
        orch.fix_error = MagicMock(return_value=True)
        orch.run_session(session.id)
        mock_store.save_session.assert_called()

    def test_stores_environment_info(self):
        orch = make_orchestrator()
        error = make_error("test_foo")
        session = orch.start_session([error])
        attempt = error.start_fix_attempt(0.4)
        error.mark_fixed(attempt)
        orch.fix_error = MagicMock(return_value=True)
        orch.run_session(session.id, environment_info={"python": "3.13"})
        assert session.environment_info.get("python") == "3.13"

    def test_skips_already_fixed_errors(self):
        orch = make_orchestrator()
        error = make_error("test_foo")
        attempt = error.start_fix_attempt(0.4)
        error.mark_fixed(attempt)
        session = orch.start_session([error])
        orch.fix_error = MagicMock(return_value=True)
        orch.run_session(session.id)
        orch.fix_error.assert_not_called()


# ---------------------------------------------------------------------------
# fix_error — retry and temperature logic
# ---------------------------------------------------------------------------

class TestFixError:
    def test_returns_true_on_first_attempt_success(self, tmp_path):
        orch = make_orchestrator(max_retries=3)
        error = make_error("test_foo", tmp_path)
        orch.start_session([error])
        with patch("branch_fixer.orchestration.fix_service.FixService") as MockFS:
            mock_svc = MagicMock()
            mock_svc.attempt_fix.return_value = True
            MockFS.return_value = mock_svc
            result = orch.fix_error(error)
        assert result is True

    def test_retries_up_to_max_retries(self, tmp_path):
        orch = make_orchestrator(max_retries=3)
        error = make_error("test_foo", tmp_path)
        orch.start_session([error])
        with patch("branch_fixer.orchestration.fix_service.FixService") as MockFS:
            mock_svc = MagicMock()
            mock_svc.attempt_fix.return_value = False
            MockFS.return_value = mock_svc
            orch.fix_error(error)
        assert mock_svc.attempt_fix.call_count == 3

    def test_returns_false_after_all_attempts_fail(self, tmp_path):
        orch = make_orchestrator(max_retries=2)
        error = make_error("test_foo", tmp_path)
        orch.start_session([error])
        with patch("branch_fixer.orchestration.fix_service.FixService") as MockFS:
            mock_svc = MagicMock()
            mock_svc.attempt_fix.return_value = False
            MockFS.return_value = mock_svc
            result = orch.fix_error(error)
        assert result is False

    def test_succeeds_on_second_attempt(self, tmp_path):
        orch = make_orchestrator(max_retries=3)
        error = make_error("test_foo", tmp_path)
        orch.start_session([error])
        with patch("branch_fixer.orchestration.fix_service.FixService") as MockFS:
            mock_svc = MagicMock()
            mock_svc.attempt_fix.side_effect = [False, True]
            MockFS.return_value = mock_svc
            result = orch.fix_error(error)
        assert result is True
        assert mock_svc.attempt_fix.call_count == 2

    def test_temperature_increases_per_retry(self, tmp_path):
        orch = make_orchestrator(max_retries=3)
        orch.initial_temp = 0.4
        orch.temp_increment = 0.1
        error = make_error("test_foo", tmp_path)
        orch.start_session([error])
        call_temps = []
        with patch("branch_fixer.orchestration.fix_service.FixService") as MockFS:
            svc_instance = MagicMock()
            def attempt_fix_capture(error_arg, temperature):
                call_temps.append(temperature)
                return False
            svc_instance.attempt_fix.side_effect = attempt_fix_capture
            MockFS.return_value = svc_instance
            orch.fix_error(error)
        assert call_temps[0] == pytest.approx(0.4)
        assert call_temps[1] == pytest.approx(0.5)
        assert call_temps[2] == pytest.approx(0.6)

    def test_raises_if_no_session(self):
        orch = make_orchestrator()
        with pytest.raises(RuntimeError):
            orch.fix_error(make_error())

    def test_retry_count_incremented_on_failure(self, tmp_path):
        orch = make_orchestrator(max_retries=2)
        error = make_error("test_foo", tmp_path)
        session = orch.start_session([error])
        with patch("branch_fixer.orchestration.fix_service.FixService") as MockFS:
            mock_svc = MagicMock()
            mock_svc.attempt_fix.return_value = False
            MockFS.return_value = mock_svc
            orch.fix_error(error)
        assert session.retry_count == 2


# ---------------------------------------------------------------------------
# pause_session / resume_session
# ---------------------------------------------------------------------------

class TestPauseResume:
    def test_pause_from_running_succeeds(self):
        orch = make_orchestrator()
        session = orch.start_session([make_error()])
        assert orch.pause_session() is True
        assert session.state == FixSessionState.PAUSED

    def test_resume_from_paused_succeeds(self):
        orch = make_orchestrator()
        session = orch.start_session([make_error()])
        orch.pause_session()
        assert orch.resume_session() is True
        assert session.state == FixSessionState.RUNNING

    def test_pause_when_not_running_raises(self):
        orch = make_orchestrator()
        session = orch.start_session([make_error()])
        session.state = FixSessionState.PAUSED
        with pytest.raises(RuntimeError):
            orch.pause_session()

    def test_resume_when_not_paused_raises(self):
        orch = make_orchestrator()
        orch.start_session([make_error()])
        with pytest.raises(RuntimeError):
            orch.resume_session()

    def test_pause_without_session_raises(self):
        orch = make_orchestrator()
        with pytest.raises(RuntimeError):
            orch.pause_session()

    def test_resume_without_session_raises(self):
        orch = make_orchestrator()
        with pytest.raises(RuntimeError):
            orch.resume_session()


# ---------------------------------------------------------------------------
# get_progress
# ---------------------------------------------------------------------------

class TestGetProgress:
    def test_raises_if_no_session(self):
        orch = make_orchestrator()
        with pytest.raises(RuntimeError):
            orch.get_progress()

    def test_returns_fix_progress(self):
        orch = make_orchestrator()
        orch.start_session([make_error()])
        progress = orch.get_progress()
        assert isinstance(progress, FixProgress)

    def test_total_errors_matches_session(self):
        orch = make_orchestrator()
        errors = [make_error(f"test_{i}") for i in range(3)]
        orch.start_session(errors)
        assert orch.get_progress().total_errors == 3

    def test_fixed_count_reflects_completed(self):
        orch = make_orchestrator()
        e1 = make_error("test_a")
        e2 = make_error("test_b")
        session = orch.start_session([e1, e2])
        session.completed_errors.append(e1)
        assert orch.get_progress().fixed_count == 1

    def test_retry_count_matches_session(self):
        orch = make_orchestrator()
        session = orch.start_session([make_error()])
        session.retry_count = 5
        assert orch.get_progress().retry_count == 5


# ---------------------------------------------------------------------------
# handle_error
# ---------------------------------------------------------------------------

class TestHandleError:
    def test_sets_error_state_without_recovery_manager(self):
        orch = make_orchestrator()
        session = orch.start_session([make_error()])
        orch.handle_error(RuntimeError("boom"))
        assert session.state == FixSessionState.ERROR

    def test_returns_false_without_recovery_manager(self):
        orch = make_orchestrator()
        orch.start_session([make_error()])
        assert orch.handle_error(RuntimeError("boom")) is False

    def test_raises_if_no_session(self):
        orch = make_orchestrator()
        with pytest.raises(RuntimeError):
            orch.handle_error(RuntimeError("boom"))

    def test_calls_recovery_manager_when_present(self):
        orch = make_orchestrator()
        mock_rm = MagicMock()
        mock_rm.handle_failure.return_value = True
        orch.recovery_manager = mock_rm
        session = orch.start_session([make_error()])
        result = orch.handle_error(RuntimeError("boom"))
        assert result is True
        mock_rm.handle_failure.assert_called_once()
