# src/branch_fixer/orchestration/fix_service.py
import logging
from typing import Optional

from branch_fixer.core.models import FixAttempt, TestError
from branch_fixer.orchestration.exceptions import FixServiceError

# NEW: Imports for storing session or orchestrating
from branch_fixer.orchestration.orchestrator import FixSession, FixSessionState
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
        Construct a FixService coordinating AI-driven fix generation, change application, test verification, and optional session persistence.
        
        Parameters:
            ai_manager (AIManager): Service that proposes code changes for a failing test.
            test_runner (TestRunner): Service that runs and verifies tests.
            change_applier (ChangeApplier): Service that applies and restores code changes.
            git_repo (GitRepository): Repository interface used for workspace operations.
            max_retries (int): Maximum number of fix attempts; must be greater than zero.
            initial_temp (float): Initial temperature for AI generation; must be in the range [0, 1].
            temp_increment (float): Amount to increase temperature after each retry; must be positive.
            dev_force_success (bool): If True, bypasses attempt logic and marks fixes as successful (development shortcut).
            session_store (Optional[SessionStore]): Optional persistence backend for saving FixSession state.
            state_manager (Optional[StateManager]): Optional manager to validate/transition session state.
            session (Optional[FixSession]): Optional FixSession instance to track and update error/fix progress.
        
        Raises:
            ValueError: If `max_retries` <= 0, or `initial_temp` is outside [0, 1], or `temp_increment` <= 0.
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

    def attempt_fix(self, error: TestError, temperature: float) -> bool:
        """
        Perform a single attempt to fix a failing test by generating, applying, and verifying code changes.
        
        Validates the workspace and dependencies, may apply AI-proposed changes with a backup and restore the original file on failure, records the attempt result (success or failure), and updates any attached session state.
        
        Returns:
            `True` if the failing test was fixed, `False` otherwise.
        
        Raises:
            FixServiceError: On workspace validation failures or other operational errors during generation, application, or verification.
            ValueError: If the provided TestError is already marked as fixed.
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

            backup_path = None
            fix_succeeded = False
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
                fix_succeeded = self._verify_fix(error, attempt)

            except Exception as e:
                logger.warning("Error occurred after changes might have been applied.")
                self._handle_failed_attempt(error, attempt)
                raise FixServiceError(str(e)) from e

            finally:
                # Restore backup on any failure path once a backup exists
                if backup_path and not fix_succeeded:
                    try:
                        self.change_applier.restore_backup(error.test_file, backup_path)
                        logger.info(f"Reverted {error.test_file} after fix failure.")
                    except Exception as revert_exc:
                        logger.warning(
                            f"Failed to revert after fix failure: {revert_exc}"
                        )

            if not fix_succeeded:
                self._handle_failed_attempt(error, attempt)
                return False

            # If we reach here, fix is good
            error.mark_fixed(attempt)
            self._update_session_if_present(error)
            return True

        except Exception as e:
            root_cause = getattr(e, "__cause__", e)
            raise FixServiceError(str(root_cause)) from e

    def attempt_manual_fix(self, error: TestError) -> bool:
        """
        Checks whether a user's manual edit fixed the failing test by validating the workspace, re-running the test, and recording success.
        
        Parameters:
            error (TestError): The failing test context to verify.
        
        Returns:
            True if the test passes after the manual edit, False otherwise.
        
        Raises:
            FixServiceError: If workspace validation or dependency checks fail.
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

    def _handle_failed_attempt(self, error: TestError, attempt: FixAttempt) -> None:
        """
        Record a failed fix attempt and update any attached session.
        
        Marks the provided attempt as failed on the TestError and updates the FixService's session/state if one is attached.
        
        Raises:
            FixServiceError: If recording the failure or updating the session fails.
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
        Update the attached FixSession when the provided error's status changes, persist the session, and trigger session state transitions as appropriate.
        
        If no session is attached this is a no-op. If `error` is part of `self.session.errors` and its `status` equals `"fixed"`, the error is appended to `self.session.completed_errors` when not already present. If a `state_manager` is configured and all session errors are completed, attempts to transition the session to `FixSessionState.COMPLETED` (any StateTransitionError or StateValidationError is caught and logged). If a `session_store` is configured, saves the updated session; errors from saving are not caught here.
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
                            self.session, FixSessionState.COMPLETED
                        )
                except (StateTransitionError, StateValidationError) as ex:
                    logger.warning(f"Failed to transition session state: {ex}")

            if self.session_store:
                self.session_store.save_session(self.session)
