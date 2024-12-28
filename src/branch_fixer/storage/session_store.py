# src/branch_fixer/storage/session_store.py
import os
from pathlib import Path
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from tinydb import TinyDB, Query

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
        Initialize session store with TinyDB backend.

        Args:
            storage_dir: Directory to store session data.

        Raises:
            PermissionError: If directory is not writable.
            ValueError: If path is invalid or parent does not exist.
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
        Persist session state to TinyDB storage.

        Args:
            session: Session to save

        Raises:
            SessionPersistenceError: If saving fails for any reason.
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
                "completed_errors": [str(err.id) for err in session.completed_errors],
                "current_error": str(session.current_error.id) if session.current_error else None,
                # Additional fields as needed
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
        Load session from TinyDB storage.

        Args:
            session_id: ID of session to load.

        Returns:
            The loaded FixSession or None if not found.

        Raises:
            SessionPersistenceError: If loading or deserialization fails.
        """
        try:
            Session = Query()
            session_data = self.sessions.get(Session.id == str(session_id))
            if not session_data:
                return None

            # Build a FixSession object
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
            )
            # We don't have direct references to errors or completed_errors here,
            # so re-attach them as needed if your code handles them externally.
            return fix_session

        except Exception as e:
            raise SessionPersistenceError(
                f"Failed to load session {session_id}: {e}"
            ) from e

    def list_sessions(
        self, status: Optional[FixSessionState] = None
    ) -> List[FixSession]:
        """
        List all stored sessions, optionally filtered by status.

        Args:
            status: Optional status to filter by.

        Returns:
            List of FixSession objects.

        Raises:
            SessionPersistenceError: If listing fails.
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
