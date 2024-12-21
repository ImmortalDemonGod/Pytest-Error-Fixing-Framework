# src/branch_fixer/utils/cli.py
import click
import logging
from pathlib import Path
from typing import Optional, List
import traceback
import signal
import time
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.core.models import TestError
from branch_fixer.services.pytest.error_processor import parse_pytest_errors
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.config.settings import DEBUG
from branch_fixer.config.logging_config import setup_logging
from branch_fixer.orchestration.fix_service import FixService
import snoop

logger = logging.getLogger(__name__)

class CLI:
    """CLI interface for pytest-fixer"""
    
    def __init__(self):
        self.service = None
        self.created_branches = set()  # Track branches we create
        self._exit_requested = False
        
    def setup_signal_handlers(self):
        """Setup handlers for graceful exit"""
        def handle_exit(signum, frame):
            print("\nReceived exit signal. Starting cleanup...")
            self._exit_requested = True
            
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

    def cleanup(self):
        """Cleanup resources before exit"""
        if not self.service:
            return
            
        print("\nCleaning up resources...")
        errors = []
        
        # Cleanup branches
        for branch in self.created_branches:
            try:
                print(f"Cleaning up branch: {branch}")
                self.service.git_repo.branch_manager.cleanup_fix_branch(
                    branch, force=True
                )
            except Exception as e:
                errors.append(f"Failed to cleanup branch {branch}: {str(e)}")
                logger.error(f"Cleanup error for branch {branch}: {str(e)}")
                
        # Report any errors
        if errors:
            print("\nEncountered errors during cleanup:")
            for error in errors:
                print(f"- {error}")
        else:
            print("Cleanup completed successfully")
    @snoop
    def run_fix_workflow(self, error: TestError, interactive: bool) -> bool:
        """Run the fix workflow for a single error."""
        try:
            logger.info(f"Attempting to fix {error.test_function} in {error.test_file}")
            
            # Create fix branch with additional uniqueness
            import uuid
            unique_suffix = str(uuid.uuid4())[:8]
            branch_name = f"fix-{error.test_file.stem}-{error.test_function}-{unique_suffix}"
            
            logger.info(f"Creating fix branch: {branch_name}")
            
            try:
                if not self.service.git_repo.branch_manager.create_fix_branch(branch_name):
                    logger.error(f"Failed to create fix branch: {branch_name}")
                    return False
            except Exception as branch_create_error:
                logger.warning(f"Branch creation warning: {branch_create_error}")
                # Continue even if branch creation fails
                
            # Track branch for cleanup
            self.created_branches.add(branch_name)
                
            logger.info("Attempting to generate and apply fix...")
            if self.service.attempt_fix(error):
                if interactive:
                    if not click.confirm("Fix succeeded. Create PR?", default=True):
                        logger.info("Skipping PR creation as per user request")
                        return False
                        
                # Create PR
                logger.info("Creating pull request...")
                if self.service.git_repo.create_pull_request(branch_name, error):
                    logger.info("Created pull request successfully")
                    return True
                else:
                    logger.error("Failed to create pull request")
                    return False
                
            logger.warning("Fix attempt failed")
            return False
                
        except Exception as e:
            logger.error(f"Fix workflow failed: {str(e)}")
            if DEBUG:
                logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            return False

    def setup_components(self, api_key: str, max_retries: int, 
                        initial_temp: float, temp_increment: float) -> bool:
        """Initialize all required components."""
        try:
            logger.info("Initializing AI Manager...")
            ai_manager = AIManager(api_key)
            
            logger.info("Initializing Test Runner...")
            test_runner = TestRunner()
            
            logger.info("Initializing Change Applier...")
            change_applier = ChangeApplier()
            
            logger.info("Initializing Git Repository...")
            git_repo = GitRepository()
            
            logger.info("Creating Fix Service...")
            self.service = FixService(
                ai_manager=ai_manager,
                test_runner=test_runner,
                change_applier=change_applier,
                git_repo=git_repo,
                max_retries=max_retries,
                initial_temp=initial_temp,
                temp_increment=temp_increment
            )
            
            # Run workspace validation
            logger.info("Validating workspace...")
            self.service.validator.validate_workspace(Path.cwd())
            
            logger.info("Checking dependencies...")
            self.service.validator.check_dependencies()
            
            logger.info("Component initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Component initialization failed: {str(e)}")
            if DEBUG:
                logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            return False

    def _prompt_for_fix(self, test_number: int, total_tests: int, error: TestError) -> Optional[str]:
        """Prompt the user with detailed information and options for fixing a test."""
        print(f"\n[Test {test_number}/{total_tests}]")
        print(f"Fix this failing test?")
        print(f"  Test: {error.test_function}")
        print(f"  Error: {error.error_details.error_type}: {error.error_details.message}\n")
        print("Options:")
        print("  [Y]es: Attempt to fix this test")
        print("  [N]o:  Skip this test")
        print("  [Q]uit: Stop fixing tests and exit\n")
        
        choices = {'y': 'y', 'n': 'n', 'q': 'q'}
        while True:
            choice = input("Your choice [Y/n/q]: ").strip().lower() or 'y'
            if choice in choices:
                return choice
            print("Please enter one of: Y, n, Q")

    def process_errors(self, errors: List[TestError], interactive: bool) -> int:
        """Process all found errors."""
        success_count = 0
        
        try:
            self.setup_signal_handlers()
            
            total_errors = len(errors)
            print(f"Starting fix attempts for {total_errors} failed tests\n")
            logger.info(f"\nStarting fix attempts for {total_errors} failed tests")
            
            for i, error in enumerate(errors, 1):
                if self._exit_requested:
                    logger.info("Exit requested, stopping fix attempts")
                    break
                    
                logger.info(f"\nProcessing error {i}/{total_errors}:")
                logger.info(f"Test: {error.test_function}")
                logger.info(f"Error: {error.error_details.error_type}: {error.error_details.message}")

                if interactive:
                    choice = self._prompt_for_fix(i, total_errors, error)
                    
                    if choice == 'q':
                        logger.info("Exiting as requested")
                        break
                    elif choice == 'n':
                        logger.info("Skipping fix attempt as per user request")
                        continue

                if self.run_fix_workflow(error, interactive):
                    success_count += 1
                    print(f"✓ Successfully fixed {error.test_function}\n")
                    logger.info(f"Successfully fixed {error.test_function}")
                else:
                    print(f"✗ Failed to fix {error.test_function}\n")
                    logger.warning(f"Failed to fix {error.test_function}")

            # Summary
            fixed = success_count
            failed = i - success_count
            print("\nFix attempts completed:")
            print(f"- Total errors processed: {i}/{total_errors}")
            print(f"- Successfully fixed: {fixed}")
            print(f"- Failed to fix: {failed}")
            logger.info(f"\nFix attempts completed:")
            logger.info(f"- Total errors processed: {i}/{total_errors}")
            logger.info(f"- Successfully fixed: {fixed}")
            logger.info(f"- Failed to fix: {failed}")
            
        finally:
            # Always run cleanup
            self.cleanup()
        
        return 0 if success_count == total_errors else 1