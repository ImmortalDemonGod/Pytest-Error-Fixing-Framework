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

        # NEW: Optionally store session, session_store, and state_manager
        self.session_store = session_store
        self.state_manager = state_manager
        self.session = (
            session  # We'll assume the session is created or loaded elsewhere
        )

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
            # Validate workspace before attempting fix
            try:
                self.validator.validate_workspace(error.test_file.parent)
                self.validator.check_dependencies()
            except Exception as e:
                raise FixServiceError(f"Workspace validation failed: {str(e)}") from e

            # Start fix attempt with the given temperature
            attempt = error.start_fix_attempt(temperature)

            # If dev_force_success is set, skip actual fix generation
            if self.dev_force_success:
                logger.info(
                    "Dev force success enabled: skipping actual fix logic and marking success."
                )
                error.mark_fixed(attempt)
                self._update_session_if_present(error)
                return True

            try:
                # Generate fix using AI
                changes = self.ai_manager.generate_fix(error, attempt.temperature)

                # Apply changes (we'll get both success bool and backup_path)
                success, backup_path = self.change_applier.apply_changes_with_backup(
                    error.test_file, changes
                )

                # If it didn't even apply successfully (syntax, etc.), fail
                if not success:
                    self._handle_failed_attempt(error, attempt)
                    return False

                # Now we do the functional test
                if not self._verify_fix(error, attempt):
                    # Revert the file because the functional test failed
                    try:
                        if backup_path:
                            self.change_applier.restore_backup(
                                error.test_file, backup_path
                            )
                            logger.info(
                                f"Reverted {error.test_file} after functional test failure."
                            )
                    except Exception as revert_exc:
                        logger.warning(
                            f"Failed to revert after functional test failure: {revert_exc}"
                        )

                    self._handle_failed_attempt(error, attempt)
                    return False

                # If we get here, the fix is good. Mark as fixed
                error.mark_fixed(attempt)
                self._update_session_if_present(error)
                return True

            except Exception as e:
                # If something unexpected breaks, let's also revert if we can
                # But we only have a backup if apply_changes_with_backup got that far
                logger.warning(
                    "Error occurred after changes might have been applied. Attempting revert."
                )
                self._handle_failed_attempt(error, attempt)
                raise FixServiceError(str(e)) from e

        except Exception as e:
            # Get the root cause, not the FixServiceError wrapper
            root_cause = getattr(e, "__cause__", e)
            raise FixServiceError(str(root_cause)) from e

    # @snoop
    def attempt_manual_fix(self, error: TestError) -> bool:
        """
        Check if a user's manual code edits have fixed the failing test.

        1) Validate workspace
        2) Re-run the test via test_runner to see if it now passes
        3) Return True if it passes, else False

        This method does not modify code or revert changes—it's purely a test verification
        step to see if the user's manual edits have resolved the issue.
        """
        try:
            # Validate workspace before re-testing
            self.validator.validate_workspace(error.test_file.parent)
            self.validator.check_dependencies()
        except Exception as e:
            raise FixServiceError(
                f"Workspace validation failed (manual fix): {str(e)}"
            ) from e

        # Run the test to see if the issue is resolved
        success = self.test_runner.verify_fix(error.test_file, error.test_function)
        if success:
            # Mark as fixed if test passes
            # We still want to create a fix attempt for tracking (with 0.0 temperature if you like)
            attempt = error.start_fix_attempt(0.0)
            error.mark_fixed(attempt)
            self._update_session_if_present(error)
        return success

    snoop()

    def _handle_failed_attempt(self, error: TestError, attempt: FixAttempt) -> None:
        """
        Handle cleanup after failed fix attempt.

        This marks the attempt as failed. Additional cleanup or revert logic can be added here if needed.
        """
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

        Raises:
            FixServiceError: If verification fails unexpectedly
        """
        try:
            return self.test_runner.verify_fix(error.test_file, error.test_function)
        except Exception as e:
            raise FixServiceError(f"Fix verification failed: {str(e)}") from e

    # NEW: optional helper to update session state or persist session
    def _update_session_if_present(self, error: TestError) -> None:
        """
        If a session is attached, update it with the new error state.
        Optionally persist via session_store and handle state transitions via state_manager.
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
                    else:
                        # Keep session as RUNNING if not completed
                        pass
                except (StateTransitionError, StateValidationError) as ex:
                    logger.warning(f"Failed to transition session state: {ex}")

            # Persist session changes if store is provided
            if self.session_store:
                self.session_store.save_session(self.session)
