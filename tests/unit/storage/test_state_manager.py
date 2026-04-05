"""Tests for StateManager — state transition validation and history tracking."""
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from branch_fixer.orchestration.orchestrator import FixSession, FixSessionState
from branch_fixer.storage.state_manager import (
    StateManager,
    StateTransitionError,
    StateValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_session(state: FixSessionState = FixSessionState.INITIALIZING) -> FixSession:
    s = FixSession()
    s.state = state
    return s


# ---------------------------------------------------------------------------
# validate_transition
# ---------------------------------------------------------------------------

class TestValidateTransition:
    def test_initializing_to_running_is_valid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.INITIALIZING, FixSessionState.RUNNING) is True

    def test_initializing_to_failed_is_valid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.INITIALIZING, FixSessionState.FAILED) is True

    def test_running_to_completed_is_valid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.RUNNING, FixSessionState.COMPLETED) is True

    def test_running_to_paused_is_valid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.RUNNING, FixSessionState.PAUSED) is True

    def test_running_to_failed_is_valid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.RUNNING, FixSessionState.FAILED) is True

    def test_running_to_error_is_valid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.RUNNING, FixSessionState.ERROR) is True

    def test_paused_to_running_is_valid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.PAUSED, FixSessionState.RUNNING) is True

    def test_error_to_running_is_valid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.ERROR, FixSessionState.RUNNING) is True

    def test_completed_is_terminal(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.COMPLETED, FixSessionState.RUNNING) is False

    def test_failed_is_terminal(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.FAILED, FixSessionState.RUNNING) is False

    def test_initializing_to_completed_is_invalid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.INITIALIZING, FixSessionState.COMPLETED) is False

    def test_paused_to_completed_is_invalid(self):
        sm = StateManager()
        assert sm.validate_transition(FixSessionState.PAUSED, FixSessionState.COMPLETED) is False


# ---------------------------------------------------------------------------
# transition_state
# ---------------------------------------------------------------------------

class TestTransitionState:
    def test_valid_transition_updates_session_state(self):
        sm = StateManager()
        session = make_session(FixSessionState.INITIALIZING)
        sm.transition_state(session, FixSessionState.RUNNING)
        assert session.state == FixSessionState.RUNNING

    def test_invalid_transition_raises(self):
        sm = StateManager()
        session = make_session(FixSessionState.COMPLETED)
        with pytest.raises(StateTransitionError):
            sm.transition_state(session, FixSessionState.RUNNING)

    def test_forced_transition_bypasses_validation(self):
        sm = StateManager()
        session = make_session(FixSessionState.COMPLETED)
        result = sm.transition_state(session, FixSessionState.RUNNING, force=True)
        assert result is True
        assert session.state == FixSessionState.RUNNING

    def test_transition_records_history(self):
        sm = StateManager()
        session = make_session(FixSessionState.INITIALIZING)
        sm.transition_state(session, FixSessionState.RUNNING)
        history = sm.get_transition_history(session.id)
        assert len(history) == 1
        assert history[0].from_state == FixSessionState.INITIALIZING
        assert history[0].to_state == FixSessionState.RUNNING

    def test_transition_stores_metadata(self):
        sm = StateManager()
        session = make_session(FixSessionState.INITIALIZING)
        sm.transition_state(session, FixSessionState.RUNNING, metadata={"reason": "started"})
        history = sm.get_transition_history(session.id)
        assert history[0].metadata == {"reason": "started"}

    def test_transition_calls_session_store_if_present(self):
        mock_store = MagicMock()
        sm = StateManager(session_store=mock_store)
        session = make_session(FixSessionState.INITIALIZING)
        sm.transition_state(session, FixSessionState.RUNNING)
        mock_store.save_session.assert_called_once_with(session)

    def test_transition_returns_true_on_success(self):
        sm = StateManager()
        session = make_session(FixSessionState.INITIALIZING)
        assert sm.transition_state(session, FixSessionState.RUNNING) is True

    def test_multiple_transitions_all_recorded(self):
        sm = StateManager()
        session = make_session(FixSessionState.INITIALIZING)
        sm.transition_state(session, FixSessionState.RUNNING)
        sm.transition_state(session, FixSessionState.PAUSED)
        sm.transition_state(session, FixSessionState.RUNNING)
        assert len(sm.get_transition_history(session.id)) == 3


# ---------------------------------------------------------------------------
# get_transition_history
# ---------------------------------------------------------------------------

class TestGetTransitionHistory:
    def test_empty_history_for_unknown_session(self):
        sm = StateManager()
        assert sm.get_transition_history(uuid4()) == []

    def test_history_is_ordered(self):
        sm = StateManager()
        session = make_session(FixSessionState.INITIALIZING)
        sm.transition_state(session, FixSessionState.RUNNING)
        sm.transition_state(session, FixSessionState.COMPLETED)
        history = sm.get_transition_history(session.id)
        assert history[0].to_state == FixSessionState.RUNNING
        assert history[1].to_state == FixSessionState.COMPLETED


# ---------------------------------------------------------------------------
# validate_session_state
# ---------------------------------------------------------------------------

class TestValidateSessionState:
    def test_running_session_is_valid(self):
        sm = StateManager()
        session = make_session(FixSessionState.RUNNING)
        assert sm.validate_session_state(session) is True

    def test_completed_with_all_errors_fixed_is_valid(self):
        from branch_fixer.core.models import TestError, ErrorDetails
        sm = StateManager()
        session = make_session(FixSessionState.COMPLETED)
        error = TestError(
            test_file=pytest.importorskip("pathlib").Path("test_foo.py"),
            test_function="test_foo",
            error_details=ErrorDetails(error_type="AssertionError", message="fail"),
        )
        session.errors = [error]
        session.completed_errors = [error]
        assert sm.validate_session_state(session) is True

    def test_completed_with_unfixed_errors_raises(self):
        from branch_fixer.core.models import TestError, ErrorDetails
        from pathlib import Path
        sm = StateManager()
        session = make_session(FixSessionState.COMPLETED)
        error = TestError(
            test_file=Path("test_foo.py"),
            test_function="test_foo",
            error_details=ErrorDetails(error_type="AssertionError", message="fail"),
        )
        session.errors = [error]
        session.completed_errors = []
        with pytest.raises(StateValidationError):
            sm.validate_session_state(session)
