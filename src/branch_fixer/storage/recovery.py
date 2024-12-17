from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from uuid import UUID
import hashlib
import time

if TYPE_CHECKING:
    from src.branch_fixer.storage.session_store import SessionStore
    from src.branch_fixer.git.repository import GitRepository
    from src.branch_fixer.orchestrator import FixSession

@dataclass
class RecoveryPoint:
    """Snapshot of recoverable state"""
    id: str  # Hash of session_id + timestamp
    session_id: UUID
    timestamp: float
    git_branch: str
    modified_files: List[Path]
    metadata: Dict[str, Any]
    
    @staticmethod
    def create(session_id: UUID, git_branch: str, 
               modified_files: List[Path], metadata: Dict[str, Any]) -> 'RecoveryPoint':
        """Create new recovery point with unique ID"""
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

class RecoveryError(Exception):
    """Base exception for recovery operations"""
    pass

class RecoveryManager:
    """Handles recovery from failures during fix attempts"""
    
    def __init__(self, session_store: 'SessionStore',
                 git_repo: 'GitRepository',
                 backup_dir: Path):
        """Initialize recovery manager
        
        Args:
            session_store: For accessing session data
            git_repo: For Git operations 
            backup_dir: Directory for backups
            
        Raises:
            ValueError: If arguments invalid
            PermissionError: If backup_dir not writable
        """
        raise NotImplementedError()

    async def create_checkpoint(self, session: 'FixSession',
                              metadata: Optional[Dict] = None) -> RecoveryPoint:
        """Create recovery checkpoint for current state
        
        Args:
            session: Current fix session
            metadata: Additional recovery metadata
            
        Returns:
            RecoveryPoint for later restoration
            
        Raises:
            RecoveryError: If checkpoint creation fails
            GitError: If Git operations fail
        """
        raise NotImplementedError()

    async def restore_checkpoint(self, checkpoint_id: str,
                               cleanup: bool = True) -> bool:
        """Restore session state from checkpoint
        
        Args:
            checkpoint_id: ID of checkpoint to restore
            cleanup: Whether to remove checkpoint after restore
            
        Returns:
            bool indicating successful restore
            
        Raises:
            RecoveryError: If restore fails
            GitError: If Git restore fails
            FileNotFoundError: If backup files missing
        """
        raise NotImplementedError()

    async def handle_failure(self, error: Exception,
                           session: 'FixSession',
                           context: Dict[str, Any]) -> bool:
        """Handle specific failure types
        
        Args:
            error: The exception that occurred
            session: Current fix session
            context: Additional error context
            
        Returns:
            bool indicating if recovery succeeded
            
        Note:
            Attempts to recover based on error type and context
        """
        raise NotImplementedError()
