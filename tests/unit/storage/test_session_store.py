"""Tests for SessionStore — TinyDB-backed session persistence with full round-trip."""
import pytest
from pathlib import Path
from uuid import uuid4

from branch_fixer.core.models import TestError, ErrorDetails
from branch_fixer.orchestration.orchestrator import FixSession, FixSessionState
from branch_fixer.storage.session_store import SessionStore, SessionPersistenceError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    return SessionStore(storage_dir=tmp_path / "sessions")


def make_error(name: str = "test_foo") -> TestError:
    return TestError(
        test_file=Path(f"tests/{name}.py"),
        test_function=name,
        error_details=ErrorDetails(error_type="AssertionError", message="fail"),
    )


def make_session(state: FixSessionState = FixSessionState.RUNNING) -> FixSession:
    s = FixSession()
    s.state = state
    return s


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_creates_storage_dir(self, tmp_path):
        target = tmp_path / "sessions"
        SessionStore(storage_dir=target)
        assert target.exists()

    def test_raises_if_parent_missing(self, tmp_path):
        with pytest.raises(ValueError):
            SessionStore(storage_dir=tmp_path / "ghost" / "deep" / "sessions")

    def test_creates_sessions_json(self, tmp_path):
        store = SessionStore(storage_dir=tmp_path / "sessions")
        assert (tmp_path / "sessions" / "sessions.json").exists()


# ---------------------------------------------------------------------------
# save_session / load_session round-trip
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def test_load_returns_none_for_unknown_id(self, store):
        assert store.load_session(uuid4()) is None

    def test_save_then_load_preserves_state(self, store):
        session = make_session(FixSessionState.COMPLETED)
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.state == FixSessionState.COMPLETED

    def test_save_then_load_preserves_errors(self, store):
        session = make_session()
        error = make_error("test_add")
        session.errors = [error]
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert len(loaded.errors) == 1
        assert loaded.errors[0].test_function == "test_add"

    def test_save_then_load_preserves_completed_errors(self, store):
        session = make_session()
        error = make_error()
        session.errors = [error]
        session.completed_errors = [error]
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert len(loaded.completed_errors) == 1

    def test_save_then_load_preserves_current_error(self, store):
        session = make_session()
        error = make_error("test_current")
        session.current_error = error
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.current_error is not None
        assert loaded.current_error.test_function == "test_current"

    def test_save_then_load_current_error_none(self, store):
        session = make_session()
        session.current_error = None
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.current_error is None

    def test_save_then_load_preserves_numeric_fields(self, store):
        session = make_session()
        session.total_tests = 10
        session.passed_tests = 8
        session.failed_tests = 2
        session.retry_count = 3
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.total_tests == 10
        assert loaded.passed_tests == 8
        assert loaded.failed_tests == 2
        assert loaded.retry_count == 3

    def test_save_then_load_preserves_environment_info(self, store):
        session = make_session()
        session.environment_info = {"os": "darwin", "python": "3.13"}
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.environment_info == {"os": "darwin", "python": "3.13"}

    def test_save_then_load_preserves_warnings(self, store):
        session = make_session()
        session.warnings = ["DeprecationWarning: foo"]
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.warnings == ["DeprecationWarning: foo"]

    def test_save_then_load_preserves_git_branch(self, store):
        session = make_session()
        session.git_branch = "fix/test-add-123"
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.git_branch == "fix/test-add-123"

    def test_save_then_load_preserves_modified_files(self, store):
        session = make_session()
        session.modified_files = [Path("tests/test_foo.py")]
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.modified_files == [Path("tests/test_foo.py")]

    def test_update_overwrites_existing_session(self, store):
        session = make_session(FixSessionState.RUNNING)
        store.save_session(session)
        session.state = FixSessionState.COMPLETED
        store.save_session(session)
        loaded = store.load_session(session.id)
        assert loaded.state == FixSessionState.COMPLETED
        # Should not have created a duplicate
        assert len(store.list_sessions()) == 1


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------

class TestListSessions:
    def test_empty_store_returns_empty_list(self, store):
        assert store.list_sessions() == []

    def test_lists_all_sessions(self, store):
        s1 = make_session(FixSessionState.RUNNING)
        s2 = make_session(FixSessionState.COMPLETED)
        store.save_session(s1)
        store.save_session(s2)
        assert len(store.list_sessions()) == 2

    def test_filter_by_state(self, store):
        s1 = make_session(FixSessionState.RUNNING)
        s2 = make_session(FixSessionState.COMPLETED)
        store.save_session(s1)
        store.save_session(s2)
        completed = store.list_sessions(status=FixSessionState.COMPLETED)
        assert len(completed) == 1
        assert completed[0].state == FixSessionState.COMPLETED

    def test_filter_returns_empty_if_no_match(self, store):
        session = make_session(FixSessionState.RUNNING)
        store.save_session(session)
        assert store.list_sessions(status=FixSessionState.FAILED) == []


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------

class TestDeleteSession:
    def test_delete_existing_returns_true(self, store):
        session = make_session()
        store.save_session(session)
        assert store.delete_session(session.id) is True

    def test_delete_removes_session(self, store):
        session = make_session()
        store.save_session(session)
        store.delete_session(session.id)
        assert store.load_session(session.id) is None

    def test_delete_nonexistent_returns_false(self, store):
        assert store.delete_session(uuid4()) is False
