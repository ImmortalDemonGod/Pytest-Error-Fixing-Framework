# src/branch_fixer/orchestration/fix_service.py
import logging
from typing import Optional

import snoop

from branch_fixer.core.models import FixAttempt, TestError
from branch_fixer.orchestration.exceptions import FixServiceError

# NEW: Imports for storing session or orchestrating
from branch_fixer.orchestration.orchestrator import FixSession
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.pytest.runner import PytestRunner as TestRunner
from branch_fixer.storage.session_store import SessionStore
from branch_fixer.storage.state_manager import (
    StateManager,
    StateTransitionError,
    StateValidationError,
)
from branch_fixer.utils.workspace import WorkspaceValidator

logger = logging.getLogger(__name__)


class FixService:
    """Orchestrates test fixing process"""

    def __init__(
        self,
        ai_manager: AIManager,
        test_runner: TestRunner,
        change_applier: ChangeApplier,
        git_repo: GitRepository,
        max_retries: int = 3,
        initial_temp: float = 0.4,
        temp_increment: float = 0.1,
        dev_force_success: bool = False,
        session_store: Optional[SessionStore] = None,
        state_manager: Optional[StateManager] = None,
        session: Optional[FixSession] = None,
    ):
        """
        Initialize fix service with components.

        Args:
            ai_manager: AI service for generating fixes
            test_runner: Test execution service
            change_applier: Code change service
            git_repo: Git operations service
            max_retries: Maximum fix attempts
            initial_temp: Starting temperature
            temp_increment: Temperature increase per retry
            dev_force_success: If True, skip actual fix logic and force success
            session_store: Optional session store for persisting fix session
            state_manager: Optional manager for validating state transitions
            session: Optional FixSession to track fix state

        Raises:
            ValueError: If invalid parameters provided
        """
        if max_retries <= 0:
            raise ValueError("max_retries must be positive")
        if not 0 <= initial_temp <= 1:
            raise ValueError("initial_temp must be between 0 and 1")
        if temp_increment <= 0:
            raise ValueError("temp_increment must be positive")

        self.validator = WorkspaceValidator()
        self.ai_manager = ai_manager
        self.test_runner = test_runner
        self.change_applier = change_applier
        self.git_repo = git_repo
        self.max_retries = max_retries
        self.initial_temp = initial_temp
        self.temp_increment = temp_increment
        self.dev_force_success = dev_force_success

        # Keep references to optional sessioning logic
        self.session_store = session_store
        self.state_manager = state_manager
        self.session = session

    # @snoop
    def attempt_fix(self, error: TestError, temperature: float) -> bool:
        """
        Attempt to fix failing test in a single shot (no internal loop).

        1) Validate workspace
        2) Generate fix (unless dev_force_success is True)
        3) Apply fix (with backup)
        4) If syntax fails, revert automatically (handled in apply_changes).
        5) If functional test fails, revert changes here.
        6) Mark error as fixed if successful, else handle failure.

        The 'temperature' parameter is passed in from the orchestrator, which
        handles multi-retry loops and increments if needed.

        Returns:
            bool indicating if fix succeeded

        Raises:
            FixServiceError: If fix process fails
            ValueError: If error is already fixed
        """
        try:
            # Validate workspace
            try:
                self.validator.validate_workspace(error.test_file.parent)
                self.validator.check_dependencies()
            except Exception as e:
                raise FixServiceError(f"Workspace validation failed: {str(e)}") from e

            # Start fix attempt
            attempt = error.start_fix_attempt(temperature)

            # Skip actual fix generation if dev_force_success
            if self.dev_force_success:
                logger.info(
                    "Dev force success enabled: skipping actual fix logic and marking success."
                )
                error.mark_fixed(attempt)
                self._update_session_if_present(error)
                return True

            try:
                # AI-based fix
                changes = self.ai_manager.generate_fix(error, attempt.temperature)
                success, backup_path = self.change_applier.apply_changes_with_backup(
                    error.test_file, changes
                )

                if not success:
                    self._handle_failed_attempt(error, attempt)
                    return False

                # Re-run functional test
                if not self._verify_fix(error, attempt):
                    try:
                        if backup_path:
                            self.change_applier.restore_backup(error.test_file, backup_path)
                            logger.info(
                                f"Reverted {error.test_file} after functional test failure."
                            )
                    except Exception as revert_exc:
                        logger.warning(
                            f"Failed to revert after functional test failure: {revert_exc}"
                        )

                    self._handle_failed_attempt(error, attempt)
                    return False

                # If we reach here, fix is good
                error.mark_fixed(attempt)
                self._update_session_if_present(error)
                return True

            except Exception as e:
                logger.warning("Error occurred after changes might have been applied.")
                self._handle_failed_attempt(error, attempt)
                raise FixServiceError(str(e)) from e

        except Exception as e:
            root_cause = getattr(e, "__cause__", e)
            raise FixServiceError(str(root_cause)) from e

    # @snoop
    def attempt_manual_fix(self, error: TestError) -> bool:
        """
        Check if a user's manual code edits have fixed the failing test.

        1) Validate workspace
        2) Re-run the test
        3) Mark error as fixed if it passes

        Returns True if test passes, else False
        """
        try:
            self.validator.validate_workspace(error.test_file.parent)
            self.validator.check_dependencies()
        except Exception as e:
            raise FixServiceError(
                f"Workspace validation failed (manual fix): {str(e)}"
            ) from e

        success = self.test_runner.verify_fix(error.test_file, error.test_function)
        if success:
            attempt = error.start_fix_attempt(0.0)
            error.mark_fixed(attempt)
            self._update_session_if_present(error)
        return success

    snoop()

    def _handle_failed_attempt(self, error: TestError, attempt: FixAttempt) -> None:
        """Mark attempt as failed and optionally revert code."""
        try:
            error.mark_attempt_failed(attempt)
            self._update_session_if_present(error)
        except Exception as e:
            raise FixServiceError(f"Failed to handle failed attempt: {str(e)}") from e

    def _verify_fix(self, error: TestError, attempt: FixAttempt) -> bool:
        """
        Verify if fix attempt succeeded by re-running the test function.

        Returns:
            bool indicating if fix works

        Note: If you rely on parsing the pytest output for post-processing,
        it will now flow through the new unified_error_parser (via error_processor).
        That ensures consistent handling of both collection errors and standard failures.

        Raises:
            FixServiceError: If verification fails unexpectedly
        """
        try:
            return self.test_runner.verify_fix(error.test_file, error.test_function)
        except Exception as e:
            raise FixServiceError(f"Fix verification failed: {str(e)}") from e

    def _update_session_if_present(self, error: TestError) -> None:
        """
        If a session is attached, update it with the new error state.
        Save to session_store if present, manage states via state_manager if provided.
        """
        if not self.session:
            return

        # If this error is part of the session’s errors, see if it’s fixed
        # We do not know if the orchestrator has a deeper error-tracking approach,
        # but as an example:
        if error in self.session.errors:
            if error.status == "fixed" and error not in self.session.completed_errors:
                self.session.completed_errors.append(error)
            if self.state_manager:
                try:
                    # For example, if the session is still RUNNING, check if all errors are fixed
                    if len(self.session.completed_errors) == len(self.session.errors):
                        self.state_manager.transition_state(
                            self.session, "FixSessionState.COMPLETED"
                        )
                except (StateTransitionError, StateValidationError) as ex:
                    logger.warning(f"Failed to transition session state: {ex}")

            if self.session_store:
                self.session_store.save_session(self.session)
