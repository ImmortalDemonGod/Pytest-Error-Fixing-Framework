# src/branch_fixer/utils/cli.py

import click
import logging
from pathlib import Path
from typing import Optional, List
import traceback
import signal
import time
import uuid

from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.core.models import TestError
from branch_fixer.services.pytest.error_processor import parse_pytest_errors
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.config.settings import DEBUG
from branch_fixer.config.logging_config import setup_logging
from branch_fixer.orchestration.fix_service import FixService

# Orchestrator references:
from branch_fixer.orchestration.orchestrator import (
    FixOrchestrator,
    FixSession,
    FixSessionState
)

import snoop

logger = logging.getLogger(__name__)

class CLI:
    """CLI interface for pytest-fixer, refined for better user navigation and messaging."""
    
    def __init__(self):
        self.service: Optional[FixService] = None
        self.created_branches = set()  # Track any created fix branches
        self._exit_requested = False

        self.orchestrator: Optional[FixOrchestrator] = None  # Session-based approach
        
    def setup_signal_handlers(self):
        """Setup handlers for graceful exit (Ctrl-C, kill, etc.)."""
        def handle_exit(signum, frame):
            print("\nReceived exit signal. Starting cleanup...")
            self._exit_requested = True
            
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

    def cleanup(self):
        """
        Cleanup resources before exit:
         - Clean up fix branches
         - Checkout main branch
         - Provide user feedback on leftover errors
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
            for err in errors:
                print(f"- {err}")
        else:
            print("Cleanup completed successfully.")

    @snoop
    def run_fix_workflow(self, error: TestError, interactive: bool) -> bool:
        """
        Run the fix workflow for a single error using AI:
         1) Create a unique fix branch
         2) Attempt to generate/apply a fix
         3) Optionally create a PR & push
         4) Return success/failure
        """
        try:
            logger.info(f"Attempting to fix {error.test_function} in {error.test_file}")

            # 1) Create fix branch with unique suffix
            unique_suffix = str(uuid.uuid4())[:8]
            branch_name = f"fix-{error.test_file.stem}-{error.test_function}-{unique_suffix}"
            
            logger.info(f"Creating fix branch: {branch_name}")
            try:
                if self.service and not self.service.git_repo.branch_manager.create_fix_branch(branch_name):
                    logger.error(f"Failed to create fix branch: {branch_name}")
                    return False
            except Exception as branch_err:
                logger.warning(f"Branch creation warning: {branch_err}")
                # Continue even if branch creation fails
                
            # Track the created branch
            self.created_branches.add(branch_name)
                
            # 2) Attempt to generate and apply fix
            logger.info("Attempting to generate and apply fix...")
            if self.service and self.service.attempt_fix(error, self.service.initial_temp):
                logger.info(f"Fix attempt for {error.test_function} succeeded.")
                
                # If in interactive mode, optionally create PR
                if interactive:
                    pr_confirm = click.confirm(
                        "Fix succeeded. Would you like to open a Pull Request?",
                        default=True
                    )
                    if not pr_confirm:
                        logger.info("Skipping PR creation at user request.")
                        return True  # We still succeeded in the fix
                
                # 3) Create PR if desired
                logger.info("Creating pull request...")
                if self.service and self.service.git_repo.create_pull_request_sync(branch_name, error):
                    logger.info("Created pull request successfully.")
                    
                    # 4) Try pushing to remote
                    if self.service.git_repo.push(branch_name):
                        logger.info(f"Successfully pushed branch '{branch_name}' to remote.")
                        return True
                    else:
                        logger.error(f"Failed to push branch '{branch_name}' to remote.")
                        return False
                else:
                    logger.error("Failed to create pull request (or no repo configured).")
                    return True  # We consider fix successful, but PR creation failed
            else:
                logger.warning(f"Fix attempt for {error.test_function} failed.")
                return False
                
        except Exception as e:
            logger.error(f"Fix workflow encountered an error: {str(e)}")
            if DEBUG:
                logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            return False
    @snoop
    def run_manual_fix_workflow(self, error: TestError) -> str:
        """
        Let the user manually fix the test, then check if it passes:
        - Loop until user either *succeeds*, *skips*, or *quits*.
        - Limit the number of retries to avoid infinite loops.

        Return values:
        - "fixed" => The test now passes after user edits
        - "skip"  => The user pressed 's' to skip
        - "quit"  => The user pressed 'q' to stop manual fix mode entirely
        """
        retry_limit = 3  # Limit the number of retries for manual fixes.
        retries = 0

        while retries < retry_limit:
            click.echo("\n--- MANUAL FIX MODE ---")
            click.echo(f"Please open '{error.test_file}' and fix the issue for test '{error.test_function}'.")
            user_input = click.prompt(
                "Press Enter to re-run the test, type 's' to skip manual fixing, or 'q' to quit manual fix mode",
                default="",
                show_default=False
            )

            if user_input.lower() == 's':
                # user chooses skip
                return "skip"
            elif user_input.lower() == 'q':
                # user chooses quit
                click.echo("Exiting manual fix mode.")
                return "quit"

            # Attempt verifying the fix
            if self.service and self.service.attempt_manual_fix(error):
                # If passing, mark success
                click.echo(f"✓ Test '{error.test_function}' now passes!")
                return "fixed"
            else:
                # If still failing
                retries += 1
                click.echo(f"✗ Test '{error.test_function}' is still failing. ({retries}/{retry_limit} retries used)")

        # If retry limit is reached, exit manual fix mode
        click.echo("Retry limit reached. Exiting manual fix mode.")
        return "quit"


    @snoop
    def setup_components(
        self,
        api_key: str,
        max_retries: int,
        initial_temp: float,
        temp_increment: float,
        dev_force_success: bool
    ) -> bool:
        """
        Initialize AI, Test Runner, ChangeApplier, GitRepo, FixService, & Orchestrator.
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
            
            # Optional orchestrator
            logger.info("Creating Orchestrator object for session-based approach...")
            self.orchestrator = FixOrchestrator(
                ai_manager=ai_manager,
                test_runner=test_runner,
                change_applier=change_applier,
                git_repo=git_repo,
                max_retries=max_retries,
                initial_temp=initial_temp,
                temp_increment=temp_increment,
                interactive=True  # or dev_force_success
            )

            # Validate workspace
            logger.info("Validating workspace...")
            self.service.validator.validate_workspace(Path.cwd())
            
            logger.info("Checking dependencies...")
            self.service.validator.check_dependencies()
            
            logger.info("Component initialization successful.")
            return True
            
        except Exception as e:
            logger.error(f"Component initialization failed: {str(e)}")
            if DEBUG:
                logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            return False
    @snoop
    def _prompt_for_fix(self, error: TestError) -> Optional[str]:
        """
        Prompt user how to handle a failing test in interactive mode. 
         - 'y' => Attempt AI fix
         - 'm' => Manual fix
         - 'n' => Skip
         - 'q' => Quit
        """
        while True:
            click.clear()  # Clear screen for a fresh prompt
            click.echo(f"\nFailing Test: {error.test_function}")
            click.echo(f"Location: {error.test_file}")
            click.echo(f"Error Type: {error.error_details.error_type}")
            click.echo(f"Message: {error.error_details.message}")
            click.echo("\nOptions:")
            click.echo("[Y] Attempt AI-based fix")
            click.echo("[M] Perform manual fix")
            click.echo("[N] Skip this test")
            click.echo("[Q] Quit fixing tests entirely")

            choice = click.getchar("\nYour choice (y/m/n/q) [y]: ").lower()

            # Default to 'y' if user hits enter
            if choice in ['\r', '\n', '']:
                choice = 'y'
                
            # Acceptable
            if choice in ['y', 'm', 'n', 'q']:
                return choice
                
            # Else re-prompt
            click.echo("\nInvalid choice. Enter 'y', 'm', 'n', or 'q'.")

    def process_errors(self, errors: List[TestError], interactive: bool) -> int:
        """
        Process all discovered failing errors.
         - In interactive mode, prompt for fix path
         - In non-interactive, always attempt AI-based fix
         - Summarize the results at the end
        """
        success_count = 0
        total_processed = 0
        
        try:
            self.setup_signal_handlers()
            
            total_errors = len(errors)
            click.echo(f"Starting fix attempts for {total_errors} failing tests.\n")
            logger.info(f"Starting fix attempts for {total_errors} errors.")
            
            for i, error in enumerate(errors, 1):
                if self._exit_requested:
                    logger.info("Exit requested; stopping fix attempts.")
                    break
                    
                logger.info(f"\nProcessing error {i}/{total_errors}: {error.test_function}\n")

                if interactive:
                    choice = self._prompt_for_fix(error)
                    if choice == 'q':
                        click.echo("\nQuitting as requested.")
                        logger.info("User chose to quit.")
                        break
                    elif choice == 'n':
                        click.echo("\nSkipping this test.\n")
                        logger.info("User chose to skip.")
                        total_processed += 1
                        continue
                    elif choice == 'm':
                        # Manual fix path
                        click.echo("Switching to manual fix mode...\n")
                        manual_result = self.run_manual_fix_workflow(error)
                        if manual_result == "fixed":
                            success_count += 1
                            click.echo(f"✓ Successfully fixed '{error.test_function}' via manual fix.\n")
                        elif manual_result == "skip":
                            click.echo(f"✗ '{error.test_function}' not fixed in manual fix mode.\n")
                        elif manual_result == "quit":
                            click.echo("\nQuitting as requested.")
                            logger.info("User chose to quit manual fix mode entirely.")
                            break
                        total_processed += 1
                    else:
                        # 'y' => Attempt AI-based fix
                        click.echo("Attempting AI-based fix...\n")
                        if self.run_fix_workflow(error, interactive=True):
                            success_count += 1
                            click.echo(f"✓ Successfully fixed '{error.test_function}' with AI.\n")
                        else:
                            click.echo(f"✗ AI fix attempt for '{error.test_function}' failed.\n")
                        total_processed += 1
                else:
                    # Non-interactive => always attempt AI
                    if self.run_fix_workflow(error, interactive=False):
                        success_count += 1
                        click.echo(f"✓ AI fix for '{error.test_function}' succeeded.")
                    else:
                        click.echo(f"✗ AI fix for '{error.test_function}' failed.")
                    total_processed += 1

            # Summarize
            if total_processed > 0:
                click.echo("\nFix attempts complete.")
                click.echo(f"Tests processed: {total_processed}/{total_errors}")
                click.echo(f"Successfully fixed: {success_count}")
                click.echo(f"Failed/skipped: {total_processed - success_count}\n")
            
        finally:
            click.echo("Starting cleanup...")
            self.cleanup()
            click.echo("Cleanup complete.")
        
        return 0 if success_count == total_processed else 1
