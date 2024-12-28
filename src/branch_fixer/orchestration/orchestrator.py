from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import logging
import snoop

from branch_fixer.core.models import TestError
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository

# If you need them, we keep references to recovery-related imports:
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
class FixSession:
    """
    Tracks state for a test fixing session
    """
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
        """
        Create serializable snapshot of current state (legacy placeholder).
        By default, just returns self.to_dict().
        """
        return self.to_dict()

    def to_dict(self) -> dict:
        """
        Convert the session to a dictionary form. 
        This includes errors, completed_errors, etc.
        """
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
        """
        Construct a FixSession object from a dictionary.
        """
        session = FixSession(
            id=UUID(data["id"]),
            state=FixSessionState(data["state"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            errors=[TestError.from_dict(e) for e in data.get("errors", [])],
            completed_errors=[TestError.from_dict(ce) for ce in data.get("completed_errors", [])],
            current_error=(
                TestError.from_dict(data["current_error"])
                if data.get("current_error") else None
            ),
            retry_count=data.get("retry_count", 0),
            error_count=data.get("error_count", 0),
            modified_files=[Path(p) for p in data.get("modified_files", [])],
            git_branch=data.get("git_branch"),
        )
        return session

@dataclass
class FixProgress:
    """
    Tracks progress of fix operations, if you need
    a structured way to represent it for a UI/logging.
    """
    total_errors: int
    fixed_count: int
    current_error: Optional[str]
    retry_count: int
    current_temperature: float
    last_error: Optional[str] = None

class FixOrchestrator:
    """
    Orchestrates test fixing workflow with state management and error handling.
    Now fully synchronous, with multi-retry logic included.
    """

    def __init__(
        self,
        ai_manager: AIManager,
        test_runner: TestRunner,
        change_applier: ChangeApplier,
        git_repo: GitRepository,
        *,
        max_retries: int = 3,
        initial_temp: float = 0.4,
        temp_increment: float = 0.1,
        interactive: bool = True,
        recovery_manager: Optional[RecoveryManager] = None,
    ):
        """
        Initialize orchestrator with required components and settings.
        
        Args:
            ai_manager: AI service for generating fixes
            test_runner: Test execution service
            change_applier: Code change service
            git_repo: Git operations service
            max_retries: Maximum fix attempts per error
            initial_temp: Initial temperature for AI
            temp_increment: Temperature increase per retry
            interactive: Whether to enable interactive mode (unused in single-run logic, but kept for future)
            recovery_manager: Optional RecoveryManager for checkpoint/restore
        """
        self.ai_manager = ai_manager
        self.test_runner = test_runner
        self.change_applier = change_applier
        self.git_repo = git_repo
        self.max_retries = max_retries
        self.initial_temp = initial_temp
        self.temp_increment = temp_increment
        self.interactive = interactive
        self._session: Optional[FixSession] = None

        # If you want to handle advanced rollbacks or error handling
        self.recovery_manager = recovery_manager

        # You might create or inject an actual FixService instance. 
        # Alternatively, you can do so externally and pass it in.

    def start_session(self, errors: List[TestError]) -> FixSession:
        """
        Start a new fix session synchronously.
        
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

        # Transition session to RUNNING
        session.state = FixSessionState.RUNNING
        self._session = session

        logger.info(f"Session {session.id} started with {len(errors)} errors.")
        return session

    def run_session(self, session_id: UUID) -> bool:
        """
        Run an existing fix session synchronously.

        - For each error, we call fix_error(...) with multi-retries.
        - If any error cannot be fixed, we mark the session FAILED.
        
        Returns:
            bool indicating if all errors were eventually fixed
        """
        if not self._session or self._session.id != session_id:
            raise RuntimeError("Session not found or not started")
        if self._session.state != FixSessionState.RUNNING:
            raise RuntimeError(f"Cannot run session in state {self._session.state}")
        
        logger.info(f"Running session {session_id}")
        
        for error in self._session.errors:
            if error.status == "fixed":
                continue  # skip already-fixed

            success = self.fix_error(error)
            if not success:
                # Mark session as FAILED if an error is irreparable
                self._session.state = FixSessionState.FAILED
                return False

        # If we reach here, all errors are presumably fixed or we forcibly ended
        self._session.state = FixSessionState.COMPLETED
        return True

    @snoop
    def fix_error(self, error: TestError) -> bool:
        """
        Attempt multiple fix attempts for a single error, 
        bumping temperature each time if it fails.
        
        Returns:
            bool indicating if fix succeeded after max_retries.
        """
        if not self._session:
            raise RuntimeError("No active session")

        # Potentially create a checkpoint before we try
        # If you wish to do so, call _create_checkpoint_if_needed(...)
        # We'll skip that for now, or you can adapt as needed.

        current_temp = self.initial_temp
        for attempt_index in range(self.max_retries):
            logger.info(
                f"[Session {self._session.id}] Attempt #{attempt_index+1} for test '{error.test_function}' "
                f"at temperature={current_temp}"
            )

            # We might call a separate FixService that does one attempt at a time:
            from branch_fixer.orchestration.fix_service import FixService
            fix_service = FixService(
                ai_manager=self.ai_manager,
                test_runner=self.test_runner,
                change_applier=self.change_applier,
                git_repo=self.git_repo,
                dev_force_success=False,  # or some logic
                session_store=None,       # or attach a store if you want
                state_manager=None,       # or attach if you have one
                session=self._session
            )

            success = fix_service.attempt_fix(error, temperature=current_temp)
            if success:
                # If it’s fixed, we can stop retrying for this error
                return True

            # If not successful, increment temperature & try again
            current_temp += self.temp_increment

        return False

    def handle_error(self, error: Exception) -> bool:
        """
        Handle errors during fix process. 
        If a RecoveryManager is present, attempt to do a restore. 
        Otherwise, just log the error.
        
        Returns:
            bool indicating if recovery or handling succeeded
        """
        if not self._session:
            raise RuntimeError("No active session for handling errors")
        logger.warning(f"Handling orchestrator-level error: {error}")

        # If we have a RecoveryManager, attempt to handle it
        if self.recovery_manager:
            context = {"current_state": self._session.state.value}
            try:
                recovered = self.recovery_manager.handle_failure(error, self._session, context)
                if recovered:
                    logger.info("Recovery succeeded, session can continue.")
                    return True
            except Exception as e:
                logger.error(f"Recovery manager failed: {e}")
                return False

        # If we cannot handle it, mark session as ERROR
        self._session.state = FixSessionState.ERROR
        return False

    def get_progress(self) -> FixProgress:
        """
        Return a snapshot of the session's progress if needed. 
        No concurrency: just a direct method returning progress.
        """
        if not self._session:
            raise RuntimeError("No active session for progress")

        return FixProgress(
            total_errors=self._session.error_count,
            fixed_count=len(self._session.completed_errors),
            current_error=(
                self._session.current_error.test_function
                if self._session.current_error else None
            ),
            retry_count=self._session.retry_count,
            current_temperature=self.initial_temp
        )

    def pause_session(self) -> bool:
        """
        Pause current fix session.
        """
        if not self._session:
            raise RuntimeError("No active session to pause")
        if self._session.state != FixSessionState.RUNNING:
            raise RuntimeError(f"Cannot pause session in state {self._session.state}")

        self._session.state = FixSessionState.PAUSED
        logger.info(f"Session {self._session.id} paused.")
        return True

    def resume_session(self) -> bool:
        """
        Resume paused fix session.
        """
        if not self._session:
            raise RuntimeError("No active session to resume")
        if self._session.state != FixSessionState.PAUSED:
            raise RuntimeError(f"Cannot resume session in state {self._session.state}")

        self._session.state = FixSessionState.RUNNING
        logger.info(f"Session {self._session.id} resumed.")
        return True

    # If you’d like advanced checkpointing:
    def _create_checkpoint_if_needed(self, session: FixSession, label: str) -> None:
        """
        Possibly create a checkpoint with the recovery manager (if present).
        """
        if not self.recovery_manager:
            return

        try:
            metadata = {"label": label, "timestamp": datetime.now().isoformat()}
            checkpoint = self.recovery_manager.create_checkpoint(session, metadata)
            logger.info(
                f"Created checkpoint {checkpoint.id} for session {session.id} - {label}"
            )
        except CheckpointError as e:
            logger.warning(f"Checkpoint creation failed: {e}")
