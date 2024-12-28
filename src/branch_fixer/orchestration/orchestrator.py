# src/branch_fixer/orchestration/orchestrator.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncIterator
from uuid import UUID, uuid4
import logging
import asyncio

from branch_fixer.core.models import TestError, FixAttempt
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository

# NEW: We import RecoveryManager & exceptions if we want to call them
from branch_fixer.storage.recovery import (
    RecoveryManager,
    RecoveryError,
    CheckpointError,
    RestoreError
)

logger = logging.getLogger(__name__)

class FixSessionState(Enum):
    """Possible states for a fix session"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class FixProgress:
    """Tracks progress of fix operations"""
    total_errors: int
    fixed_count: int
    current_error: Optional[str]
    retry_count: int
    current_temperature: float
    last_error: Optional[str] = None

@dataclass
class FixSession:
    """Tracks state for a test fixing session"""
    id: UUID = field(default_factory=uuid4)
    state: FixSessionState = FixSessionState.INITIALIZING
    start_time: datetime = field(default_factory=datetime.now)
    errors: List[TestError] = field(default_factory=list)
    completed_errors: List[TestError] = field(default_factory=list)
    current_error: Optional[TestError] = None
    retry_count: int = 0
    error_count: int = 0
    modified_files: List[Path] = field(default_factory=list)
    git_branch: Optional[str] = None

    def create_snapshot(self) -> Dict[str, Any]:
        """Create serializable snapshot of current state (legacy placeholder)."""
        # Implementation example: just return the to_dict
        return self.to_dict()

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "state": self.state.value,
            "start_time": self.start_time.isoformat(),
            "errors": [e.to_dict() for e in self.errors],
            "completed_errors": [ce.to_dict() for ce in self.completed_errors],
            "current_error": self.current_error.to_dict() if self.current_error else None,
            "retry_count": self.retry_count,
            "error_count": self.error_count,
            "modified_files": [str(f) for f in self.modified_files],
            "git_branch": self.git_branch,
        }

    @staticmethod
    def from_dict(data: dict) -> "FixSession":
        fs = FixSession(
            id=UUID(data["id"]),
            state=FixSessionState(data["state"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            errors=[TestError.from_dict(e) for e in data.get("errors", [])],
            completed_errors=[TestError.from_dict(ce) for ce in data.get("completed_errors", [])],
            current_error=TestError.from_dict(data["current_error"]) if data.get("current_error") else None,
            retry_count=data.get("retry_count", 0),
            error_count=data.get("error_count", 0),
            modified_files=[Path(p) for p in data.get("modified_files", [])],
            git_branch=data.get("git_branch"),
        )
        return fs

class FixOrchestrator:
    """Orchestrates test fixing workflow with state management and error handling"""

    def __init__(self,
                 ai_manager: AIManager,
                 test_runner: TestRunner,
                 change_applier: ChangeApplier,
                 git_repo: GitRepository,
                 *,
                 max_retries: int = 3,
                 initial_temp: float = 0.4,
                 temp_increment: float = 0.1,
                 interactive: bool = True,
                 recovery_manager: Optional[RecoveryManager] = None):
        """
        Initialize orchestrator with required components and settings
        
        Args:
            ai_manager: AI service for generating fixes
            test_runner: Test execution service
            change_applier: Code change service
            git_repo: Git operations service
            max_retries: Maximum fix attempts per error
            initial_temp: Initial temperature for AI
            temp_increment: Temperature increase per retry
            interactive: Whether to enable interactive mode
            recovery_manager: Optional RecoveryManager for checkpoint/restore
            
        Raises:
            ValueError: If invalid parameters provided
            RuntimeError: If component initialization fails
        """
        # Example simple implementation
        self.ai_manager = ai_manager
        self.test_runner = test_runner
        self.change_applier = change_applier
        self.git_repo = git_repo
        self.max_retries = max_retries
        self.initial_temp = initial_temp
        self.temp_increment = temp_increment
        self.interactive = interactive
        self._session: Optional[FixSession] = None

        # NEW: optionally store the recovery manager
        self.recovery_manager = recovery_manager

    async def start_session(self, errors: List[TestError]) -> FixSession:
        """
        Start a new fix session

        Args:
            errors: List of errors to fix
            
        Returns:
            New FixSession instance
            
        Raises:
            ValueError: If errors list is empty
        """
        if not errors:
            raise ValueError("Cannot start a session with no errors")
        
        session = FixSession(
            errors=errors,
            error_count=len(errors),
            state=FixSessionState.INITIALIZING
        )
        # Possibly create a checkpoint here, if we like
        await self._create_checkpoint_if_needed(session, "initial_session")

        # Transition session to RUNNING
        session.state = FixSessionState.RUNNING
        self._session = session

        logger.info(f"Session {session.id} started with {len(errors)} errors.")
        return session

    async def run_session(self, session_id: UUID) -> bool:
        """
        Run an existing fix session

        Args:
            session_id: ID of session to run
            
        Returns:
            bool indicating if all errors were fixed
        """
        if not self._session or self._session.id != session_id:
            raise RuntimeError("Session not found or not started")
        if self._session.state != FixSessionState.RUNNING:
            raise RuntimeError(f"Cannot run session in state {self._session.state}")
        
        logger.info(f"Running session {session_id}")
        
        # Example: For each error, call fix_error
        # If any fix fails, we can do a restore
        for error in self._session.errors:
            if error.status == "fixed":
                continue  # Already fixed
            try:
                success = await self.fix_error(error)
                if not success:
                    # Mark session as FAILED if an error is irreparable
                    self._session.state = FixSessionState.FAILED
                    return False
            except Exception as e:
                logger.error(f"Exception while fixing error {error.test_function}: {e}")
                self._session.state = FixSessionState.ERROR
                # Attempt recovery
                handled = await self.handle_error(e)
                if not handled:
                    return False
        
        # If we reach here, all errors are presumably fixed or we forcibly ended
        self._session.state = FixSessionState.COMPLETED
        return True

    async def fix_error(self, error: TestError) -> bool:
        """
        Attempt to fix a single test error
        
        Returns:
            bool indicating if fix succeeded
        """
        if not self._session:
            raise RuntimeError("No active session")

        # Potentially create a checkpoint before we try
        await self._create_checkpoint_if_needed(self._session, f"before_fix_{error.test_function}")

        logger.info(f"Attempting to fix error: {error.test_function}")
        # We might call FixService or do direct logic:
        # For demonstration, let's do simple logic:
        # Simulate success if error_function doesn't match "fail"
        if "fail" in error.test_function.lower():
            # Arbitrary simulation: it fails
            logger.info("Simulating a fix failure")
            return False
        else:
            # Mark as fixed
            error.status = "fixed"
            self._session.completed_errors.append(error)
            logger.info(f"Marked error {error.test_function} as fixed")
            return True

    async def get_progress(self) -> AsyncIterator[FixProgress]:
        """
        Stream progress updates for current session
        """
        if not self._session:
            raise RuntimeError("No active session for progress")

        # Potentially yield multiple updates while session is RUNNING
        # For demonstration, yield once
        yield FixProgress(
            total_errors=self._session.error_count,
            fixed_count=len(self._session.completed_errors),
            current_error=(self._session.current_error.test_function 
                           if self._session.current_error else None),
            retry_count=self._session.retry_count,
            current_temperature=self.initial_temp
        )

    def pause_session(self) -> bool:
        """
        Pause current fix session
        """
        if not self._session:
            raise RuntimeError("No active session to pause")
        if self._session.state != FixSessionState.RUNNING:
            raise RuntimeError(f"Cannot pause session in state {self._session.state}")
        
        self._session.state = FixSessionState.PAUSED
        logger.info(f"Session {self._session.id} paused.")
        return True

    async def resume_session(self) -> bool:
        """
        Resume paused fix session
        """
        if not self._session:
            raise RuntimeError("No active session to resume")
        if self._session.state != FixSessionState.PAUSED:
            raise RuntimeError(f"Cannot resume session in state {self._session.state}")
        
        self._session.state = FixSessionState.RUNNING
        logger.info(f"Session {self._session.id} resumed.")
        return True

    async def handle_error(self, error: Exception) -> bool:
        """
        Handle errors during fix process
        """
        if not self._session:
            raise RuntimeError("No active session for handling errors")
        logger.warning(f"Handling error: {error}")

        # Attempt to call RecoveryManager if present
        if self.recovery_manager:
            context = {"current_state": self._session.state.value}
            recovered = await self.recovery_manager.handle_failure(
                error, self._session, context
            )
            if recovered:
                logger.info("Recovery succeeded, session can continue.")
                return True
        
        # If we cannot handle it, mark session as ERROR
        self._session.state = FixSessionState.ERROR
        return False

    # NEW: internal helper to create checkpoint if RecoveryManager is available
    async def _create_checkpoint_if_needed(self, session: FixSession, label: str) -> None:
        """
        Create a checkpoint with the recovery manager (if present).
        """
        if not self.recovery_manager:
            return

        # Minimal example
        try:
            metadata = {"label": label, "timestamp": datetime.now().isoformat()}
            checkpoint = await self.recovery_manager.create_checkpoint(session, metadata)
            logger.info(f"Created checkpoint {checkpoint.id} for session {session.id} - {label}")
        except CheckpointError as e:
            logger.warning(f"Checkpoint creation failed: {e}")
