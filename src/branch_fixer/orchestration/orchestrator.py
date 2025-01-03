# src/branch_fixer/orchestration/orchestrator.py
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from branch_fixer.core.models import TestError
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.pytest.runner import TestRunner

# If you need them, we keep references to recovery-related imports:
from branch_fixer.storage.recovery import CheckpointError, RecoveryManager

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

    # NEW numeric fields for test session counts
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0

    # Example for storing environment info or other metadata
    environment_info: Dict[str, Any] = field(default_factory=dict)

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
            "current_error": self.current_error.to_dict()
            if self.current_error
            else None,
            "retry_count": self.retry_count,
            "error_count": self.error_count,
            "modified_files": [str(f) for f in self.modified_files],
            "git_branch": self.git_branch,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "environment_info": self.environment_info,
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
            completed_errors=[
                TestError.from_dict(ce) for ce in data.get("completed_errors", [])
            ],
            current_error=(
                TestError.from_dict(data["current_error"])
                if data.get("current_error")
                else None
            ),
            retry_count=data.get("retry_count", 0),
            error_count=data.get("error_count", 0),
            modified_files=[Path(p) for p in data.get("modified_files", [])],
            git_branch=data.get("git_branch"),
            total_tests=data.get("total_tests", 0),
            passed_tests=data.get("passed_tests", 0),
            failed_tests=data.get("failed_tests", 0),
            environment_info=data.get("environment_info", {}),
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
        session_store=None,  # NEW: optional session_store for saving
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
            session_store: Optional store for persisting the session
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

        # NEW: store the session_store so we can do save_session(...)
        self.session_store = session_store

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
            errors=errors, error_count=len(errors), state=FixSessionState.INITIALIZING
        )

        # Transition session to RUNNING
        session.state = FixSessionState.RUNNING
        self._session = session

        logger.info(f"Session {session.id} started with {len(errors)} errors.")
        return session

    def _validate_session(self, session_id: UUID) -> None:
        """
        Validate session existence and state.
        Raises RuntimeError if any validation fails.
        """
        if not self._session or self._session.id != session_id:
            raise RuntimeError("Session not found or not started")

        if self._session.state != FixSessionState.RUNNING:
            raise RuntimeError(f"Cannot run session in state {self._session.state}")

        logger.info(f"Running session {session_id}")

    def _handle_error_fix(self, error: TestError) -> bool:
        """
        Handle a single TestError:
        - Skip already-fixed errors.
        - Attempt to fix; on failure, mark session as FAILED.
        - Return True if successful, False otherwise.
        """
        if error.status == "fixed":
            return True  # skip already-fixed

        success = self.fix_error(error)
        if not success:
            # Mark session as FAILED if an error is irreparable
            self._session.state = FixSessionState.FAILED
            return False

        return True

    def run_session(
        self,
        session_id: UUID,
        total_tests: int = 0,
        environment_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Run an existing fix session synchronously.

        - For each error, call self.fix_error(...) with multi-retries.
        - If any error cannot be fixed, mark the session FAILED.
        - If no errors fail, mark the session COMPLETED.
        - Always save the session data to the session_store if present.

        Args:
            session_id: The session UUID
            total_tests: Optional total test count from the test run
            environment_info: Optional dict of environment details

        Returns:
            bool indicating if all errors were eventually fixed
        """
        self._validate_session(session_id)

        # Record extra info if provided
        if environment_info:
            self._session.environment_info.update(environment_info)
        self._session.total_tests = total_tests

        # Process each error
        for error in self._session.errors:
            if not self._handle_error_fix(error):
                # Save session if needed
                if self.session_store:
                    self.session_store.save_session(self._session)
                return False

        # If we reach here, presumably all errors are fixed
        # so we can set passed/failed counts
        self._session.failed_tests = sum(
            1 for e in self._session.errors if e.status != "fixed"
        )
        self._session.passed_tests = self._session.error_count - self._session.failed_tests

        # If no errors remain unfixed, mark as COMPLETED
        if self._session.failed_tests == 0:
            self._session.state = FixSessionState.COMPLETED
        else:
            self._session.state = FixSessionState.FAILED

        # Always save session
        if self.session_store:
            self.session_store.save_session(self._session)
        return self._session.state == FixSessionState.COMPLETED

    def fix_error(self, error: TestError) -> bool:
        """
        Attempt multiple fix attempts for a single error,
        bumping temperature each time if it fails.

        Returns:
            bool indicating if fix succeeded after max_retries.
        """
        if not self._session:
            raise RuntimeError("No active session")

        current_temp = self.initial_temp
        for attempt_index in range(self.max_retries):
            logger.info(
                f"[Session {self._session.id}] Attempt #{attempt_index+1} for test '{error.test_function}' "
                f"at temperature={current_temp}"
            )

            from branch_fixer.orchestration.fix_service import FixService

            fix_service = FixService(
                ai_manager=self.ai_manager,
                test_runner=self.test_runner,
                change_applier=self.change_applier,
                git_repo=self.git_repo,
                dev_force_success=False,  # or some logic
                session_store=None,       # Not storing partial attempts here
                state_manager=None,
                session=self._session,
            )

            success = fix_service.attempt_fix(error, temperature=current_temp)
            if success:
                return True

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

        if self.recovery_manager:
            context = {"current_state": self._session.state.value}
            try:
                recovered = self.recovery_manager.handle_failure(
                    error, self._session, context
                )
                if recovered:
                    logger.info("Recovery succeeded, session can continue.")
                    return True
            except Exception as e:
                logger.error(f"Recovery manager failed: {e}")
                return False

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
                if self._session.current_error
                else None
            ),
            retry_count=self._session.retry_count,
            current_temperature=self.initial_temp,
        )

    def _change_session_state(
        self,
        current_required_state: FixSessionState,
        new_state: FixSessionState,
        action: str,
    ) -> bool:
        """
        Generic helper for changing session state.
        Raises a RuntimeError if session is missing or in the wrong state.
        """
        if not self._session:
            raise RuntimeError(f"No active session to {action}")

        if self._session.state != current_required_state:
            raise RuntimeError(
                f"Cannot {action} session in state {self._session.state}"
            )

        self._session.state = new_state
        logger.info(f"Session {self._session.id} {action}d.")
        return True

    def pause_session(self) -> bool:
        """
        Pause current fix session.
        """
        return self._change_session_state(
            current_required_state=FixSessionState.RUNNING,
            new_state=FixSessionState.PAUSED,
            action="pause",
        )

    def resume_session(self) -> bool:
        """
        Resume paused fix session.
        """
        return self._change_session_state(
            current_required_state=FixSessionState.PAUSED,
            new_state=FixSessionState.RUNNING,
            action="resume",
        )

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