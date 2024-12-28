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
        self.service: Optional[FixService] = None
        self.created_branches = set()  # Track branches we create
        self._exit_requested = False
        
    def setup_signal_handlers(self):
        """Setup handlers for graceful exit"""
        def handle_exit(signum, frame):
            print("\nReceived exit signal. Starting cleanup...")
            self._exit_requested = True
            
        # Optionally re-enable signals:
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

    def cleanup(self):
        """
        Cleanup resources before exit:
        1) Cleanup fix branches if any
        2) Checkout back to main branch
        """
        if not self.service:
            return
            
        print("\nCleaning up resources...")
        errors = []
        
        # 1) Cleanup branches
        for branch in self.created_branches:
            try:
                print(f"Cleaning up branch: {branch}")
                self.service.git_repo.branch_manager.cleanup_fix_branch(branch, force=True)
            except Exception as e:
                errors.append(f"Failed to cleanup branch {branch}: {str(e)}")
                logger.error(f"Cleanup error for branch {branch}: {str(e)}")
                
        # 2) Checkout main
        try:
            main_branch = self.service.git_repo.main_branch
            self.service.git_repo.run_command(["checkout", main_branch])
            logger.info(f"Checked out main branch: {main_branch}")
        except Exception as e:
            errors.append(f"Failed to checkout main branch: {str(e)}")
            logger.warning(f"Unable to checkout main branch: {e}")

        # Report any errors
        if errors:
            print("\nEncountered errors during cleanup:")
            for error in errors:
                print(f"- {error}")
        else:
            print("Cleanup completed successfully")


    def run_fix_workflow(self, error: TestError, interactive: bool) -> bool:
        """
        Run the fix workflow for a single error using AI (create branch, attempt fix, revert if needed, etc.)
        """
        try:
            logger.info(f"Attempting to fix {error.test_function} in {error.test_file}")
            
            # 1) Create fix branch with additional uniqueness
            import uuid
            unique_suffix = str(uuid.uuid4())[:8]
            branch_name = f"fix-{error.test_file.stem}-{error.test_function}-{unique_suffix}"
            
            logger.info(f"Creating fix branch: {branch_name}")
            try:
                if self.service and not self.service.git_repo.branch_manager.create_fix_branch(branch_name):
                    logger.error(f"Failed to create fix branch: {branch_name}")
                    return False
            except Exception as branch_create_error:
                logger.warning(f"Branch creation warning: {branch_create_error}")
                # Continue even if branch creation fails
                
            # Track the created branch
            self.created_branches.add(branch_name)
                
            # 2) Attempt to generate and apply fix
            logger.info("Attempting to generate and apply fix...")
            if self.service and self.service.attempt_fix(error):
                # If in interactive mode, optionally create PR
                if interactive:
                    if not click.confirm("Fix succeeded. Create PR?", default=True):
                        logger.info("Skipping PR creation as per user request")
                        return False

                # 3) Create PR if desired
                logger.info("Creating pull request...")
                if self.service and self.service.git_repo.create_pull_request_sync(branch_name, error):
                    logger.info("Created pull request successfully")
                    
                    # 4) Try to push changes to remote
                    if self.service.git_repo.push(branch_name):
                        logger.info(f"Successfully pushed branch {branch_name} to remote")
                        return True
                    else:
                        logger.error(f"Failed to push branch {branch_name} to remote")
                        return False
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

    def run_manual_fix_workflow(self, error: TestError) -> bool:
        """
        Let the user manually fix the test, then verify the fix with a test run.
        If the test is still failing, prompt user again until they skip or succeed.
        """
        while True:
            click.echo("\n--- MANUAL FIX MODE ---")
            click.echo(f"Open {error.test_file} and fix the issue for test {error.test_function}.")
            click.echo("Press Enter when you're done to rerun the test, or 's' to skip.")
            user_input = click.prompt("", default="", show_default=False)

            if user_input.lower() == 's':
                # user wants to skip manual fixes
                return False

            # Re-run the test to see if it's now passing
            if self.service and self.service.attempt_manual_fix(error):
                # If passing, mark success
                click.echo(f"✓ Test {error.test_function} now passes!")
                return True
            else:
                # If still failing, ask user if they want to fix again or skip
                click.echo(f"✗ Test {error.test_function} is still failing.")
                choice = click.prompt("Try again? (y)es / (s)kip", default="y")
                if choice.lower() == 's':
                    return False

    def setup_components(
        self,
        api_key: str,
        max_retries: int,
        initial_temp: float,
        temp_increment: float,
        dev_force_success: bool
    ) -> bool:
        """
        Initialize all required components.
        """
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
                temp_increment=temp_increment,
                dev_force_success=dev_force_success
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
    
    def _prompt_for_fix(self, error: TestError) -> Optional[str]:
        """
        Prompt user how to handle a failing test in interactive mode. 
        Returns 'y', 'm', 'n', 'q' or None if input is invalid.
        """
        while True:
            click.clear()  # Clear the screen for better visibility
            click.echo("\nFix this failing test?")
            click.echo(f"Test: {error.test_function}")
            click.echo(f"Error: {error.error_details.error_type}: {error.error_details.message}")
            click.echo("\nOptions:")
            click.echo("[Y] AI fix the test")
            click.echo("[M] Manually fix the code")
            click.echo("[N] Skip this test") 
            click.echo("[Q] Quit: Stop fixing tests and exit")

            choice = click.getchar("\nYour choice (y/m/n/q) [y]: ").lower()

            # Handle empty input (Enter key) as default 'y'
            if choice == '\r' or choice == '\n':
                choice = 'y'
                
            # Only accept valid choices
            if choice in ['y', 'm', 'n', 'q']:
                return choice
                
            # Invalid input - show error and loop
            click.echo("\nInvalid choice. Please enter y, m, n, or q.")
    
    
    def process_errors(self, errors: List[TestError], interactive: bool) -> int:
        """
        Process all found errors: either interactive or automatic fix attempts.
        """
        success_count = 0
        total_processed = 0
        
        try:
            self.setup_signal_handlers()
            
            total_errors = len(errors)
            print(f"Starting fix attempts for {total_errors} failed tests\n")
            logger.info(f"\nStarting fix attempts for {total_errors} failed tests")
            
            for i, error in enumerate(errors, 1):
                if self._exit_requested:
                    logger.info("Exit requested, stopping fix attempts")
                    break
                    
                logger.info(f"\nProcessing error {i}/{total_errors}:\n")
                logger.info(f"Test: {error.test_function}\n")
                logger.info(f"Error: {error.error_details.error_type}: {error.error_details.message}\n")

                if interactive:
                    choice = self._prompt_for_fix(error)
                    
                    if choice == 'q':
                        print("\nQuitting as requested...")
                        logger.info("Quitting as requested")
                        break
                    elif choice == 'n':
                        print("Skipping test\n")
                        logger.info("Skipping test per user request")
                        total_processed += 1
                        continue
                    elif choice == 'm':
                        # Manual fix path
                        if self.run_manual_fix_workflow(error):
                            success_count += 1
                            print(f"✓ Successfully fixed {error.test_function}\n")
                        else:
                            print(f"✗ {error.test_function} not fixed manually.\n")
                        total_processed += 1
                    else:
                        # Default or 'y' => AI fix path
                        if self.run_fix_workflow(error, interactive):
                            success_count += 1
                            print(f"✓ Successfully fixed {error.test_function}\n")
                        else:
                            print(f"✗ Failed to fix {error.test_function}\n")
                        total_processed += 1
                else:
                    # Non-interactive mode always attempts AI-based fixes
                    if self.run_fix_workflow(error, interactive):
                        success_count += 1
                        print(f"✓ Successfully fixed {error.test_function}\n")
                    else:
                        print(f"✗ Failed to fix {error.test_function}\n")
                    total_processed += 1

            # Summary
            if total_processed > 0:
                print("\nFix attempts completed:")
                print(f"Tests processed: {total_processed}/{total_errors}")
                print(f"Successfully fixed: {success_count}")
                print(f"Failed/skipped: {total_processed - success_count}\n")
            
        finally:
            print("Starting cleanup...")
            self.cleanup()
            print("Cleanup complete")
        
        return 0 if success_count == total_processed else 1
