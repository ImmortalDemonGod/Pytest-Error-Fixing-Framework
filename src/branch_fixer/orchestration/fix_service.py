# branch_fixer/orchestration/fix_service.py
from typing import Optional
from branch_fixer.core.models import TestError, FixAttempt, CodeChanges
from branch_fixer.utils.workspace import WorkspaceValidator
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import PytestRunner as TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.orchestration.exceptions import FixServiceError
import asyncio



class FixService:
    """Orchestrates test fixing process"""

    def __init__(self,
                 ai_manager: AIManager,
                 test_runner: TestRunner,
                 change_applier: ChangeApplier,
                 git_repo: GitRepository,
                 max_retries: int = 3,
                 initial_temp: float = 0.4,
                 temp_increment: float = 0.1):
        """Initialize fix service with components.
        
        Args:
            ai_manager: AI service for generating fixes
            test_runner: Test execution service
            change_applier: Code change service
            git_repo: Git operations service
            max_retries: Maximum fix attempts
            initial_temp: Starting temperature
            temp_increment: Temperature increase per retry
            
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
    
    async def attempt_fix(self, error: TestError) -> bool:
        """Attempt to fix failing test.
        
        Args:
            error: TestError to attempt to fix
            
        Returns:
            bool indicating if fix succeeded
            
        Raises:
            FixServiceError: If fix process fails
            ValueError: If error is already fixed
        """
        try:
            # Validate workspace before attempting fix
            await self.validator.validate_workspace(error.test_file.parent)
            await self.validator.check_dependencies()

            # Create fix branch
            branch_name = f"fix-{error.test_file.stem}-{error.test_function}"
            if not await self.git_repo.branch_manager.create_fix_branch(branch_name):
                raise FixServiceError(f"Failed to create branch {branch_name}")

            # Start fix attempt with current temperature
            attempt = error.start_fix_attempt(self.initial_temp)
            
            # Generate fix using AI
            changes = await self.ai_manager.generate_fix(error, attempt.temperature)
            
            # Apply changes
            if not self.change_applier.apply_changes(error.test_file, changes):
                self._handle_failed_attempt(error, attempt)
                return False
                
            # Verify fix
            if not await self._verify_fix(error, attempt):
                self._handle_failed_attempt(error, attempt)
                return False
                
            # Create PR if successful
            if not await self.git_repo.create_pull_request(
                title=f"Fix {error.test_function}",
                description=f"Fixes failing test in {error.test_file}"
            ):
                raise FixServiceError("Failed to create pull request")
                
            # Mark as fixed
            error.mark_fixed(attempt)
            
            return True
            
        except Exception as e:
            self._handle_failed_attempt(error, attempt)
            raise FixServiceError(f"Fix attempt failed: {str(e)}") from e
        finally:
            # Clean up branch if fix failed
            if error.status != "fixed":
                await self.git_repo.branch_manager.cleanup_fix_branch(branch_name)
        
    def _handle_failed_attempt(self, 
                             error: TestError,
                             attempt: FixAttempt) -> None:
        """Handle cleanup after failed fix attempt.
        
        Args:
            error: TestError being fixed
            attempt: Failed FixAttempt
            
        Raises:
            FixServiceError: If cleanup fails
        """
        try:
            error.mark_attempt_failed(attempt)
            # Could add additional cleanup here if needed
        except Exception as e:
            raise FixServiceError(f"Failed to handle failed attempt: {str(e)}") from e
    
    async def _verify_fix(self,
                         error: TestError,
                         attempt: FixAttempt) -> bool:
        """Verify if fix attempt succeeded.
        
        Args:
            error: TestError being fixed  
            attempt: FixAttempt to verify
            
        Returns:
            bool indicating if fix works
            
        Raises:
            FixServiceError: If verification fails
        """
        try:
            return self.test_runner.verify_fix(error.test_file, error.test_function)
        except Exception as e:
            raise FixServiceError(f"Fix verification failed: {str(e)}") from e