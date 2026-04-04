# src/branch_fixer/storage/session_store.py
import os
from pathlib import Path
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from tinydb import TinyDB, Query
from branch_fixer.core.models import TestError
from branch_fixer.orchestration.orchestrator import FixSession, FixSessionState


class StorageError(Exception):
    """Base exception for storage errors."""

    pass


class SessionPersistenceError(StorageError):
    """Raised when session persistence operations fail."""

    pass


class SessionStore:
    """
    Handles persistent storage of fix sessions using TinyDB.

    Each session is stored in a 'sessions.json' database file under the specified storage_dir.
    CRUD operations are provided to manage the sessions.
    """

    def __init__(self, storage_dir: Path):
        """
        Set up a SessionStore backed by a TinyDB file located under the provided storage directory.
        
        Creates the storage directory if needed, verifies the provided path has an existing parent and is writable, and initializes the TinyDB database file "sessions.json" and its "sessions" table.
        
        Parameters:
            storage_dir (Path): Directory where session data and the TinyDB file will be stored.
        
        Raises:
            ValueError: If the parent of `storage_dir` does not exist.
            PermissionError: If `storage_dir` is not writable.
        """
        if not storage_dir.parent.exists():
            raise ValueError(f"Parent directory does not exist: {storage_dir.parent}")

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        if not os.access(self.storage_dir, os.W_OK):
            raise PermissionError(f"Storage directory not writable: {storage_dir}")

        db_path = self.storage_dir / "sessions.json"
        self.db = TinyDB(db_path)
        self.sessions = self.db.table("sessions")

    def save_session(self, session: FixSession) -> None:
        """
        Persist a FixSession into the sessions storage, inserting a new record or updating an existing one by session id.
        
        Parameters:
            session (FixSession): The session to persist; its full state (identifiers, timestamps, file lists, test/error data, environment info, and warnings) will be written.
        
        Raises:
            SessionPersistenceError: If the session cannot be saved.
        """
        try:
            Session = Query()
            session_data = {
                "id": str(session.id),
                "state": session.state.value,
                "start_time": session.start_time.isoformat(),
                "error_count": session.error_count,
                "retry_count": session.retry_count,
                "git_branch": session.git_branch,
                "modified_files": [str(p) for p in session.modified_files],
                "errors": [err.to_dict() for err in session.errors],
                "completed_errors": [err.to_dict() for err in session.completed_errors],
                "current_error": session.current_error.to_dict()
                if session.current_error
                else None,
                "total_tests": session.total_tests,
                "passed_tests": session.passed_tests,
                "failed_tests": session.failed_tests,
                "environment_info": session.environment_info,
                "warnings": session.warnings,
            }

            existing = self.sessions.get(Session.id == str(session.id))
            if existing:
                self.sessions.update(session_data, Session.id == str(session.id))
            else:
                self.sessions.insert(session_data)

        except Exception as e:
            raise SessionPersistenceError(
                f"Failed to save session {session.id}: {e}"
            ) from e

    def load_session(self, session_id: UUID) -> Optional[FixSession]:
        """
        Retrieve and deserialize a FixSession with the given UUID from TinyDB.
        
        Parameters:
            session_id (UUID): UUID of the session to load.
        
        Returns:
            FixSession | None: The deserialized FixSession if found, otherwise None.
        
        Raises:
            SessionPersistenceError: If loading from the database or deserialization fails.
        """
        try:
            Session = Query()
            session_data = self.sessions.get(Session.id == str(session_id))
            if not session_data or not isinstance(session_data, dict):
                return None

            fix_session = FixSession(
                id=session_id,
                state=FixSessionState(session_data["state"]),
                start_time=datetime.fromisoformat(session_data["start_time"]),
                error_count=session_data.get("error_count", 0),
                retry_count=session_data.get("retry_count", 0),
                git_branch=session_data.get("git_branch"),
                modified_files=[
                    Path(p) for p in session_data.get("modified_files", [])
                ],
                errors=[TestError.from_dict(e) for e in session_data.get("errors", [])],
                completed_errors=[
                    TestError.from_dict(e)
                    for e in session_data.get("completed_errors", [])
                ],
                current_error=(
                    TestError.from_dict(session_data["current_error"])
                    if session_data.get("current_error")
                    else None
                ),
                total_tests=session_data.get("total_tests", 0),
                passed_tests=session_data.get("passed_tests", 0),
                failed_tests=session_data.get("failed_tests", 0),
                environment_info=session_data.get("environment_info", {}),
                warnings=session_data.get("warnings", []),
            )
            return fix_session

        except Exception as e:
            raise SessionPersistenceError(
                f"Failed to load session {session_id}: {e}"
            ) from e

    def list_sessions(
        self, status: Optional[FixSessionState] = None
    ) -> List[FixSession]:
        """
        List stored FixSession objects, optionally filtered by session state.
        
        Parameters:
            status (Optional[FixSessionState]): If provided, only sessions whose state equals this value are returned.
        
        Returns:
            sessions_list (List[FixSession]): Deserialized FixSession objects matching the filter.
        
        Raises:
            SessionPersistenceError: If listing or deserialization of sessions fails.
        """
        try:
            Session = Query()
            if status is not None:
                results = self.sessions.search(Session.state == status.value)
            else:
                results = self.sessions.all()

            sessions_list = []
            for data in results:
                s_id = UUID(data["id"])
                fix_session = FixSession(
                    id=s_id,
                    state=FixSessionState(data["state"]),
                    start_time=datetime.fromisoformat(data["start_time"]),
                    error_count=data.get("error_count", 0),
                    retry_count=data.get("retry_count", 0),
                    git_branch=data.get("git_branch"),
                    modified_files=[Path(p) for p in data.get("modified_files", [])],
                    errors=[TestError.from_dict(e) for e in data.get("errors", [])],
                    completed_errors=[
                        TestError.from_dict(e) for e in data.get("completed_errors", [])
                    ],
                    current_error=(
                        TestError.from_dict(data["current_error"])
                        if data.get("current_error")
                        else None
                    ),
                    total_tests=data.get("total_tests", 0),
                    passed_tests=data.get("passed_tests", 0),
                    failed_tests=data.get("failed_tests", 0),
                    environment_info=data.get("environment_info", {}),
                    warnings=data.get("warnings", []),
                )
                sessions_list.append(fix_session)

            return sessions_list
        except Exception as e:
            raise SessionPersistenceError(f"Failed to list sessions: {e}") from e

    def delete_session(self, session_id: UUID) -> bool:
        """
        Delete a session from storage.

        Args:
            session_id: ID of session to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            SessionPersistenceError: If deletion fails.
        """
        try:
            Session = Query()
            removed = self.sessions.remove(Session.id == str(session_id))
            return len(removed) > 0
        except Exception as e:
            raise SessionPersistenceError(
                f"Failed to delete session {session_id}: {e}"
            ) from e
