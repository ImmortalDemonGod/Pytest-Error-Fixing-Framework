# branch_fixer/orchestration/fix_service.py

from typing import Optional, Tuple
from branch_fixer.core.models import TestError, FixAttempt, CodeChanges
from branch_fixer.utils.workspace import WorkspaceValidator
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import PytestRunner as TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.orchestration.exceptions import FixServiceError
import asyncio
import snoop
import logging

logger = logging.getLogger(__name__)

class FixService:
    """Orchestrates test fixing process"""

    def __init__(self,
                 ai_manager: AIManager,
                 test_runner: TestRunner,
                 change_applier: ChangeApplier,
                 git_repo: GitRepository,
                 max_retries: int = 3,
                 initial_temp: float = 0.4,
                 temp_increment: float = 0.1,
                 dev_force_success: bool = False):
        """Initialize fix service with components.
        
        Args:
            ai_manager: AI service for generating fixes
            test_runner: Test execution service
            change_applier: Code change service
            git_repo: Git operations service
            max_retries: Maximum fix attempts
            initial_temp: Starting temperature
            temp_increment: Temperature increase per retry
            dev_force_success: If True, skip actual fix logic and force success
                        
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
    
    @snoop
    def attempt_fix(self, error: TestError) -> bool:
        """
        Attempt to fix failing test.
        
        1) Validate workspace
        2) Generate fix (unless dev_force_success is True)
        3) Apply fix (with backup)
        4) If syntax fails, revert automatically (handled in apply_changes).
        5) If functional test fails, revert changes here.
        6) Mark error as fixed if successful, else handle failure.

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

            # Start fix attempt with current temperature
            attempt = error.start_fix_attempt(self.initial_temp)
            
            # If dev_force_success is set, skip actual fix generation
            if self.dev_force_success:
                logger.info("Dev force success enabled: skipping actual fix logic and marking success.")
                error.mark_fixed(attempt)
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
                            self.change_applier.restore_backup(error.test_file, backup_path)
                            logger.info(f"Reverted {error.test_file} after functional test failure.")
                    except Exception as revert_exc:
                        logger.warning(f"Failed to revert after functional test failure: {revert_exc}")
                    
                    self._handle_failed_attempt(error, attempt)
                    return False
                    
                # If we get here, the fix is good. Mark as fixed
                error.mark_fixed(attempt)
                return True
                
            except Exception as e:
                # If something unexpected breaks, let's also revert if we can
                # But we only have a backup if apply_changes_with_backup got that far
                # So let's do a careful attempt
                logger.warning("Error occurred after changes might have been applied. Attempting revert.")
                # We can do a local variable or track it in attempt
                # For simplicity: no revert here if changes not applied yet
                self._handle_failed_attempt(error, attempt)
                raise FixServiceError(str(e)) from e

        except Exception as e:
            # Get the root cause, not the FixServiceError wrapper
            root_cause = getattr(e, '__cause__', e)
            raise FixServiceError(str(root_cause)) from e

    snoop()
    def _handle_failed_attempt(self, error: TestError, attempt: FixAttempt) -> None:
        """
        Handle cleanup after failed fix attempt.
        
         """
        try:
            error.mark_attempt_failed(attempt)
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