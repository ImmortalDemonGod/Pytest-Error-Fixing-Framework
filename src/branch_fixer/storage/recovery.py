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
    def create(session_id: UUID, 
              git_branch: str,
              modified_files: List[Path], 
              metadata: Dict[str, Any]) -> 'RecoveryPoint':
        timestamp = time.time()
        point_id = hashlib.sha256(
            f"{session_id}{timestamp}".encode()
        ).hexdigest()[:12]
        return RecoveryPoint(
            id=point_id,
            session_id=session_id,
            timestamp=timestamp,
            git_branch=git_branch,
            modified_files=modified_files,
            metadata=metadata
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'session_id': str(self.session_id),
            'timestamp': self.timestamp,
            'git_branch': self.git_branch,
            'modified_files': [str(f) for f in self.modified_files],
            'metadata': self.metadata
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'RecoveryPoint':
        return cls(
            id=data['id'],
            session_id=UUID(data['session_id']),
            timestamp=data['timestamp'],
            git_branch=data['git_branch'],
            modified_files=[Path(f) for f in data['modified_files']],
            metadata=data['metadata']
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
    
    def __init__(self, 
                 session_store: 'SessionStore',
                 git_repo: 'GitRepository',
                 backup_dir: Path):
        """
        Initialize recovery manager.

        Args:
            session_store: For accessing session data
            git_repo: For Git operations
            backup_dir: Directory for backups

        Raises:
            ValueError: If arguments invalid
            PermissionError: If backup_dir not writable
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

    async def create_checkpoint(self, 
                                session: 'FixSession',
                                metadata: Optional[Dict] = None) -> RecoveryPoint:
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
                metadata=metadata
            )

            # 3) Save the RecoveryPoint as JSON
            self._save_recovery_point(rp)

            # Optionally also store the session state in the SessionStore
            # so we can load it if we want to revert to an older session
            self.session_store.save_session(session)

            return rp

        except Exception as e:
            raise CheckpointError(f"Failed to create checkpoint: {e}") from e

    async def restore_checkpoint(self, 
                                 checkpoint_id: str,
                                 cleanup: bool = True) -> bool:
        """
        Restore session state from checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore
            cleanup: Whether to remove checkpoint after restore

        Returns:
            bool indicating successful restore

        Raises:
            RestoreError: If restore fails
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
                    raise RestoreError(f"Failed to checkout {rp.git_branch}: {result.stderr}")

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
            raise RestoreError(f"Failed to restore checkpoint {checkpoint_id}: {e}") from e

    async def handle_failure(self, 
                             error: Exception,
                             session: 'FixSession',
                             context: Dict[str, Any]) -> bool:
        """
        Handle specific failure types.

        Args:
            error: The exception that occurred
            session: Current fix session
            context: Additional error context

        Returns:
            bool indicating if recovery succeeded
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
        """Append the recovery point JSON to the index file"""
        data = json.loads(self.recovery_index_file.read_text(encoding="utf-8"))
        data.append(rp.to_json())
        self.recovery_index_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_recovery_point(self, rp_id: str) -> Optional[RecoveryPoint]:
        """Load one recovery point from index by ID"""
        data = json.loads(self.recovery_index_file.read_text(encoding="utf-8"))
        for rp_json in data:
            if rp_json["id"] == rp_id:
                return RecoveryPoint.from_json(rp_json)
        return None

    def _remove_recovery_point(self, rp_id: str) -> None:
        """Remove recovery point from index file by ID"""
        data = json.loads(self.recovery_index_file.read_text(encoding="utf-8"))
        new_data = [rp for rp in data if rp["id"] != rp_id]
        self.recovery_index_file.write_text(json.dumps(new_data, indent=2), encoding="utf-8")

    def _list_recovery_points_for_session(self, session_id: UUID) -> List[RecoveryPoint]:
        """Return all recovery points for a given session"""
        data = json.loads(self.recovery_index_file.read_text(encoding="utf-8"))
        results = []
        for rp_json in data:
            if rp_json["session_id"] == str(session_id):
                rp = RecoveryPoint.from_json(rp_json)
                results.append(rp)
        return results
