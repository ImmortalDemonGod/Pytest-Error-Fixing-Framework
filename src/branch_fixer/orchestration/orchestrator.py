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

# Recovery-related imports retained for potential use
from branch_fixer.storage.recovery import CheckpointError, RecoveryManager
from branch_fixer.storage.state_manager import StateManager

logger = logging.getLogger(__name__)


class FixSessionState(Enum):
    """Possible states for a fix session."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class FixSession:
    """
    Tracks state for a test fixing session.
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

    # Numeric fields for test session counts
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0

    # Storing environment info or other metadata
    environment_info: Dict[str, Any] = field(default_factory=dict)

    # Store any warnings from the test runner
    warnings: List[str] = field(default_factory=list)

    def create_snapshot(self) -> Dict[str, Any]:
        """Create a serializable snapshot of current state."""
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
            "warnings": self.warnings,  # NEW: Included warnings
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
            warnings=data.get("warnings", []),  # NEW: Included warnings
        )
        return session


@dataclass
class FixProgress:
    """
    Tracks progress of fix operations.
    Provides a structured way to represent progress for UI/logging.
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
        session_store: Optional[
            Any
        ] = None,  # Type can be specified based on implementation
        state_manager: Optional[StateManager] = None,
    ):
        """
        Create a FixOrchestrator configured with required services and runtime settings.
        
        Parameters:
            ai_manager (AIManager): AI service used to propose code fixes.
            test_runner (TestRunner): Service that runs tests and reports failures.
            change_applier (ChangeApplier): Service that applies code changes.
            git_repo (GitRepository): Repository helper for git operations.
            max_retries (int): Maximum attempts to fix a single error.
            initial_temp (float): Starting temperature value passed to the AI when generating fixes.
            temp_increment (float): Amount to increase temperature after each failed attempt.
            interactive (bool): If True, enables interactive behaviors (e.g., prompts).
            recovery_manager (Optional[RecoveryManager]): Optional manager for creating/restoring checkpoints.
            session_store (Optional[Any]): Optional persistence store for saving session snapshots.
            state_manager (Optional[StateManager]): Optional manager used to validate or enforce session state transitions.
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
        self.state_manager = state_manager  # Placeholder for state management

        self.recovery_manager = recovery_manager
        self.session_store = session_store  # NEW: Session store for persistence

    def start_session(self, errors: List[TestError]) -> FixSession:
        """
        Start a new fix session synchronously.

        Args:
            errors: List of errors to fix.

        Returns:
            New FixSession instance.

        Raises:
            ValueError: If errors list is empty.
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

    def run_session(
        self,
        session_id: UUID,
        total_tests: int = 0,
        environment_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Execute the fix session identified by `session_id` by attempting fixes for each tracked error and persist the session state when available.
        
        Parameters:
            session_id (UUID): Identifier of the active fix session to run.
            total_tests (int): Total number of tests from the test run to record.
            environment_info (Optional[Dict[str, Any]]): Additional environment details to merge into the session's environment_info.
        
        Returns:
            bool: `True` if the session completed with no remaining failed errors, `False` otherwise.
        """
        self._validate_session(session_id)
        assert self._session is not None

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

        # Update test counts
        self._session.failed_tests = sum(
            1 for e in self._session.errors if e.status != "fixed"
        )
        self._session.passed_tests = (
            self._session.error_count - self._session.failed_tests
        )

        # Determine final state
        if self._session.failed_tests == 0:
            self._session.state = FixSessionState.COMPLETED
        else:
            self._session.state = FixSessionState.FAILED

        # Always save session
        if self.session_store:
            self.session_store.save_session(self._session)
        return self._session.state == FixSessionState.COMPLETED

    def _validate_session(self, session_id: UUID) -> None:
        """
        Validate session existence and state.
        Raises RuntimeError if any validation fails.

        Args:
            session_id: The session UUID.

        Raises:
            RuntimeError: If session is not found or not in the RUNNING state.
        """
        if not self._session or self._session.id != session_id:
            raise RuntimeError("Session not found or not started")

        if self._session.state != FixSessionState.RUNNING:
            raise RuntimeError(f"Cannot run session in state {self._session.state}")

        logger.info(f"Running session {session_id}")

    def _handle_error_fix(self, error: TestError) -> bool:
        """
        Process a TestError by skipping it if already fixed or attempting to fix it otherwise.
        
        Parameters:
            error (TestError): The failing test error to process.
        
        Returns:
            bool: `True` if the error is already fixed or was successfully fixed; `False` if fixing failed (the session state will be set to `FAILED`).
        """
        if error.status == "fixed":
            return True  # Skip already-fixed errors

        success = self.fix_error(error)
        if not success:
            # Mark session as FAILED if an error is irreparable
            assert self._session is not None
            self._session.state = FixSessionState.FAILED
            return False

        assert self._session is not None
        if error not in self._session.completed_errors:
            self._session.completed_errors.append(error)
        return True

    def fix_error(self, error: TestError) -> bool:
        """
        Attempt to fix a single TestError by performing up to the configured number of attempts, increasing the temperature between attempts.
        
        Parameters:
            error (TestError): The failing test error to attempt to fix.
        
        Returns:
            bool: `True` if the error was fixed within the retry limit, `False` otherwise.
        
        Raises:
            RuntimeError: If there is no active session.
        """
        if not self._session:
            raise RuntimeError("No active session")
        assert self._session is not None

        current_temp = self.initial_temp
        for attempt_index in range(self.max_retries):
            logger.info(
                f"[Session {self._session.id}] Attempt #{attempt_index + 1} for test '{error.test_function}' "
                f"at temperature={current_temp}"
            )

            from branch_fixer.orchestration.fix_service import FixService

            fix_service = FixService(
                ai_manager=self.ai_manager,
                test_runner=self.test_runner,
                change_applier=self.change_applier,
                git_repo=self.git_repo,
                dev_force_success=False,  # Placeholder for logic
                session_store=self.session_store,
                state_manager=self.state_manager,
                session=self._session,
            )

            success = fix_service.attempt_fix(error, temperature=current_temp)
            if success:
                logger.info(
                    f"Successfully fixed error '{error.test_function}' on attempt {attempt_index + 1}."
                )
                return True

            current_temp += self.temp_increment
            self._session.retry_count += 1
            logger.warning(
                f"Failed to fix error '{error.test_function}' on attempt {attempt_index + 1}. "
                f"Increasing temperature to {current_temp}."
            )

        logger.error(f"All attempts to fix error '{error.test_function}' have failed.")
        return False

    def handle_error(self, error: Exception) -> bool:
        """
        Handle errors during the fix process.
        If a RecoveryManager is present, attempt to perform a restore.
        Otherwise, just log the error.

        Args:
            error: The exception to handle.

        Returns:
            bool indicating if recovery or handling succeeded.
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
        Provide a progress snapshot for the active fix session.
        
        Returns:
            FixProgress: Progress populated from the current session (total errors, fixed count, current error test function name, retry count, current temperature, last error).
        
        Raises:
            RuntimeError: If no active session exists.
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
            current_temperature=self.initial_temp
            + self.temp_increment * self._session.retry_count,
            last_error=self._session.current_error.test_function
            if self._session.current_error
            else None,
        )

    def _change_session_state(
        self,
        current_required_state: FixSessionState,
        new_state: FixSessionState,
        action: str,
    ) -> bool:
        """
        Change the active session's state after verifying it is in the expected current state.
        
        Verifies an active session exists and that its state equals `current_required_state`; on success sets the session state to `new_state` and logs the transition.
        
        Parameters:
            current_required_state (FixSessionState): The state the session must currently have to allow the transition.
            new_state (FixSessionState): The state to assign to the session.
            action (str): Human-readable name of the action (used in error messages and logging).
        
        Returns:
            bool: `True` if the session state was changed.
        
        Raises:
            RuntimeError: If there is no active session or the session is not in `current_required_state`.
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
        Pause the current fix session.

        Returns:
            bool indicating successful pause.

        Raises:
            RuntimeError: If session cannot be paused.
        """
        return self._change_session_state(
            current_required_state=FixSessionState.RUNNING,
            new_state=FixSessionState.PAUSED,
            action="pause",
        )

    def resume_session(self) -> bool:
        """
        Resume a paused fix session.

        Returns:
            bool indicating successful resume.

        Raises:
            RuntimeError: If session cannot be resumed.
        """
        return self._change_session_state(
            current_required_state=FixSessionState.PAUSED,
            new_state=FixSessionState.RUNNING,
            action="resume",
        )

    def _create_checkpoint_if_needed(self, session: FixSession, label: str) -> None:
        """
        Create a recovery checkpoint for the given session when a recovery manager is configured.
        
        If no recovery manager is set this is a no-op. When configured, builds metadata
        containing the provided label and current timestamp, calls the recovery manager
        to create a checkpoint, and logs the created checkpoint's id on success. If
        checkpoint creation raises `CheckpointError` the error is caught and a warning is
        logged; the exception is not propagated.
        
        Parameters:
            session (FixSession): The session to snapshot.
            label (str): A short label describing the checkpoint.
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
