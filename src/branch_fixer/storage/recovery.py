# branch_fixer/storage/recovery.py
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from uuid import UUID
import hashlib
import time
import json
import os

if TYPE_CHECKING:
    from src.branch_fixer.storage.session_store import SessionStore
    from src.branch_fixer.services.git.repository import GitRepository
    from src.branch_fixer.orchestration.orchestrator import FixSession


@dataclass
class RecoveryPoint:
    """
    Snapshot of recoverable state with metadata and file tracking.

    Attributes:
        id: Unique identifier for the recovery point
        session_id: ID of the associated fix session
        timestamp: Unix timestamp of creation
        git_branch: Name of Git branch at snapshot time
        modified_files: List of files modified in session
        metadata: Additional context and recovery data
    """

    id: str  # Hash of session_id + timestamp
    session_id: UUID
    timestamp: float
    git_branch: str
    modified_files: List[Path]
    metadata: Dict[str, Any]

    @staticmethod
    def create(
        session_id: UUID,
        git_branch: str,
        modified_files: List[Path],
        metadata: Dict[str, Any],
    ) -> "RecoveryPoint":
        """
        Create a RecoveryPoint for the given session, capturing the current time and a unique identifier.
        
        Parameters:
            session_id (UUID): Identifier of the fix session the recovery point belongs to.
            git_branch (str): Git branch name at the time of checkpoint creation.
            modified_files (List[Path]): Paths of files recorded as modified in the session.
            metadata (Dict[str, Any]): Additional context to store with the recovery point.
        
        Returns:
            RecoveryPoint: A recovery point whose `timestamp` is the creation time and whose `id` is the first 12 hex chars of SHA-256(session_id + timestamp).
        """
        timestamp = time.time()
        point_id = hashlib.sha256(f"{session_id}{timestamp}".encode()).hexdigest()[:12]
        return RecoveryPoint(
            id=point_id,
            session_id=session_id,
            timestamp=timestamp,
            git_branch=git_branch,
            modified_files=modified_files,
            metadata=metadata,
        )

    def to_json(self) -> Dict[str, Any]:
        """
        Serialize the recovery point to a JSON-compatible dictionary.
        
        Converts `session_id` to its string form and each `Path` in `modified_files` to a string; `metadata` is included as-is.
        
        Returns:
            dict: A mapping with keys:
                - "id" (str): truncated hex identifier.
                - "session_id" (str): UUID as a string.
                - "timestamp" (float): creation time as Unix timestamp.
                - "git_branch" (str): branch name.
                - "modified_files" (List[str]): file paths as strings.
                - "metadata" (Dict[str, Any]): additional recovery context.
        """
        return {
            "id": self.id,
            "session_id": str(self.session_id),
            "timestamp": self.timestamp,
            "git_branch": self.git_branch,
            "modified_files": [str(f) for f in self.modified_files],
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "RecoveryPoint":
        """
        Deserialize a RecoveryPoint from a JSON-compatible dictionary.
        
        Parameters:
            data (Dict[str, Any]): Dictionary with keys produced by `RecoveryPoint.to_json()`:
                - "id": hex identifier string
                - "session_id": UUID string
                - "timestamp": numeric Unix timestamp
                - "git_branch": branch name string
                - "modified_files": list of file path strings
                - "metadata": dictionary of additional metadata
        
        Returns:
            RecoveryPoint: Instance populated from `data`; `session_id` is converted to a `UUID` and entries in `modified_files` are converted to `Path` objects.
        """
        return cls(
            id=data["id"],
            session_id=UUID(data["session_id"]),
            timestamp=data["timestamp"],
            git_branch=data["git_branch"],
            modified_files=[Path(f) for f in data["modified_files"]],
            metadata=data["metadata"],
        )


class RecoveryError(Exception):
    """Base exception for recovery operations."""

    pass


class CheckpointError(RecoveryError):
    """Raised when checkpoint operations fail."""

    pass


class RestoreError(RecoveryError):
    """Raised when restore operations fail."""

    pass


class RecoveryManager:
    """
    Handles recovery from failures during fix attempts.

    Manages creation and restoration of recovery points, including
    file backups and git state.
    """

    def __init__(
        self, session_store: "SessionStore", git_repo: "GitRepository", backup_dir: Path
    ):
        """
        Initialize the RecoveryManager and prepare the backup directory.
        
        Parameters:
            backup_dir (Path): Directory where recovery index and recovery point files are stored.
        
        Raises:
            ValueError: If backup_dir's parent directory does not exist.
            PermissionError: If backup_dir is not writable.
        """
        if not backup_dir.parent.exists():
            raise ValueError(f"Parent directory does not exist: {backup_dir.parent}")
        self.session_store = session_store
        self.git_repo = git_repo
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Verify backup directory is writable
        if not os.access(self.backup_dir, os.W_OK):
            raise PermissionError(f"Backup directory not writable: {backup_dir}")

        # We'll store RecoveryPoints in JSON files under backup_dir
        self.recovery_index_file = self.backup_dir / "recovery_points.json"
        if not self.recovery_index_file.exists():
            self.recovery_index_file.write_text("[]", encoding="utf-8")

    async def create_checkpoint(
        self, session: "FixSession", metadata: Optional[Dict] = None
    ) -> RecoveryPoint:
        """
        Create recovery checkpoint for current state.

        Args:
            session: Current fix session
            metadata: Additional recovery metadata

        Returns:
            RecoveryPoint for later restoration

        Raises:
            CheckpointError: If checkpoint creation fails
        """
        try:
            # 1) Gather modified files. For simplicity, we can read session.modified_files
            # 2) Create a RecoveryPoint
            metadata = metadata or {}
            rp = RecoveryPoint.create(
                session_id=session.id,
                git_branch=self.git_repo.get_current_branch(),
                modified_files=session.modified_files,
                metadata=metadata,
            )

            # 3) Save the RecoveryPoint as JSON
            self._save_recovery_point(rp)

            # Optionally also store the session state in the SessionStore
            # so we can load it if we want to revert to an older session
            self.session_store.save_session(session)

            return rp

        except Exception as e:
            raise CheckpointError(f"Failed to create checkpoint: {e}") from e

    async def restore_checkpoint(
        self, checkpoint_id: str, cleanup: bool = True
    ) -> bool:
        """
        Restore a session to a previously recorded recovery point.
        
        Parameters:
            checkpoint_id (str): Identifier of the recovery point to restore.
            cleanup (bool): If True, remove the recovery point from the index after a successful restore.
        
        Returns:
            `true` if the restore completed successfully, `false` otherwise.
        
        Raises:
            RestoreError: If the recovery point is not found or the restore operation fails.
        """
        try:
            rp = self._load_recovery_point(checkpoint_id)
            if not rp:
                raise RestoreError(f"Recovery point {checkpoint_id} not found")

            # 1) Check out the correct branch if needed
            current_branch = self.git_repo.get_current_branch()
            if current_branch != rp.git_branch:
                # Attempt to checkout rp.git_branch
                result = self.git_repo.run_command(["checkout", rp.git_branch])
                if result.failed:
                    raise RestoreError(
                        f"Failed to checkout {rp.git_branch}: {result.stderr}"
                    )

            # 2) Restore each modified file from backups if you want to store them
            #    For now, we assume they've already been partially undone by `ChangeApplier`.
            #    In a real scenario, you'd keep track of file backups in a separate directory.
            #
            #    Simplified approach: do nothing or just log
            for fpath in rp.modified_files:
                # e.g. we might revert from some backup: `_restore_file(fpath, rp.id)`
                pass

            # If cleanup, remove the checkpoint from the index
            if cleanup:
                self._remove_recovery_point(checkpoint_id)

            return True

        except Exception as e:
            raise RestoreError(
                f"Failed to restore checkpoint {checkpoint_id}: {e}"
            ) from e

    async def handle_failure(
        self, error: Exception, session: "FixSession", context: Dict[str, Any]
    ) -> bool:
        """
        Attempt to recover a fix session by restoring its most recent recovery point.
        
        Logs the failure, retrieves recovery points for the provided session, and attempts to restore the most recent checkpoint without removing it from the index.
        
        Parameters:
            error (Exception): The exception that triggered failure handling.
            session (FixSession): The current fix session whose recovery points will be inspected.
            context (Dict[str, Any]): Additional context to include in logs.
        
        Returns:
            bool: `True` if the restore succeeded, `False` otherwise.
        """
        # Example: always attempt to restore the last checkpoint
        # Or pick which checkpoint to restore
        logger_string = f"Handling failure for session {session.id}: {error}"
        if context:
            logger_string += f" | context={context}"
        print(logger_string)  # Or log it

        # For demonstration, let's restore the *most recent* checkpoint, if any
        # This is a simplistic approach:
        checkpoints = self._list_recovery_points_for_session(session.id)
        if not checkpoints:
            print("No recovery points to restore.")
            return False

        # Sort by timestamp descending, pick the last
        checkpoints.sort(key=lambda rp: rp.timestamp, reverse=True)
        latest_rp = checkpoints[0]

        try:
            print(f"Attempting to restore last checkpoint {latest_rp.id}")
            restored = await self.restore_checkpoint(latest_rp.id, cleanup=False)
            print(f"Restore result: {restored}")
            return restored
        except RestoreError as e:
            print(f"Restore failed: {e}")
            return False

    # ---------------------
    # Internal helper methods
    # ---------------------

    def _save_recovery_point(self, rp: RecoveryPoint) -> None:
        """
        Append a recovery point to the on-disk recovery index.
        
        Reads the JSON list from the index file, appends the given recovery point's
        serializable representation, and writes the updated list back (pretty-printed
        with an indentation of 2, using UTF-8 encoding). Overwrites the existing file.
        """
        data = json.loads(self.recovery_index_file.read_text(encoding="utf-8"))
        data.append(rp.to_json())
        self.recovery_index_file.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def _load_recovery_point(self, rp_id: str) -> Optional[RecoveryPoint]:
        """
        Return the recovery point with the given ID from the on-disk recovery index.
        
        Parameters:
            rp_id (str): Recovery point identifier (hex string, typically the 12-character truncated SHA).
        
        Returns:
            RecoveryPoint | None: The matching RecoveryPoint if found, `None` if no entry with `rp_id` exists.
        """
        data = json.loads(self.recovery_index_file.read_text(encoding="utf-8"))
        for rp_json in data:
            if rp_json["id"] == rp_id:
                return RecoveryPoint.from_json(rp_json)
        return None

    def _remove_recovery_point(self, rp_id: str) -> None:
        """
        Remove the recovery point with the given id from the recovery index file.
        
        Reads the recovery index JSON, removes any entries whose `"id"` equals `rp_id`, and overwrites the index file with the updated list.
        
        Parameters:
            rp_id (str): Identifier of the recovery point to remove.
        """
        data = json.loads(self.recovery_index_file.read_text(encoding="utf-8"))
        new_data = [rp for rp in data if rp["id"] != rp_id]
        self.recovery_index_file.write_text(
            json.dumps(new_data, indent=2), encoding="utf-8"
        )

    def _list_recovery_points_for_session(
        self, session_id: UUID
    ) -> List[RecoveryPoint]:
        """
        List recovery points recorded for the specified session.
        
        Parameters:
            session_id (UUID): The session identifier to filter recovery points by.
        
        Returns:
            List[RecoveryPoint]: RecoveryPoint objects associated with the given session, in the order they appear in the index.
        """
        data = json.loads(self.recovery_index_file.read_text(encoding="utf-8"))
        results = []
        for rp_json in data:
            if rp_json["session_id"] == str(session_id):
                rp = RecoveryPoint.from_json(rp_json)
                results.append(rp)
        return results
