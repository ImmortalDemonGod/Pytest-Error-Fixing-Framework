# src/branch_fixer/utils/cli.py

import logging
from math import log
import signal
import traceback
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import click

from branch_fixer.config.settings import DEBUG
from branch_fixer.core.models import TestError
from branch_fixer.orchestration.fix_service import FixService

# Orchestrator references:
from branch_fixer.orchestration.orchestrator import FixOrchestrator
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.pytest.runner import TestRunner
from branch_fixer.storage.state_manager import StateManager

import snoop
logger = logging.getLogger(__name__)


@dataclass
class ComponentSettings:
    """
    Encapsulate setup parameters for easier handling and future extensions.
    Provide default values to reduce the required argument count.
    """

    api_key: str
    max_retries: int = 3
    initial_temp: float = 0.5
    temp_increment: float = 0.1
    dev_force_success: bool = False


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
        self._cleanup_branches(errors)

        # 2) Checkout main
        self._checkout_main(errors)

        # Report any errors
        if errors:
            print("\nEncountered errors during cleanup:")
            for err in errors:
                print(f"- {err}")
        else:
            print("Cleanup completed successfully.")

    def _cleanup_branches(self, errors: List[str]) -> None:
        """
        Helper to clean up fix branches, logging any errors.
        """
        for branch in self.created_branches:
            try:
                print(f"Cleaning up branch: {branch}")
                self.service.git_repo.branch_manager.cleanup_fix_branch(
                    branch, force=True
                )
            except Exception as e:
                errors.append(f"Failed to cleanup branch {branch}: {str(e)}")
                logger.error(f"Cleanup error for branch {branch}: {str(e)}")

    def _checkout_main(self, errors: List[str]) -> None:
        """
        Helper to checkout the main branch and log errors.
        """
        try:
            main_branch = self.service.git_repo.main_branch
            self.service.git_repo.run_command(["checkout", main_branch])
            logger.info(f"Checked out main branch: {main_branch}")
        except Exception as e:
            errors.append(f"Failed to checkout main branch: {str(e)}")
            logger.warning(f"Unable to checkout main branch: {e}")

    def _create_fix_branch(self, error: TestError) -> Optional[str]:
        """
        Helper to create a new fix branch with a unique suffix.
        Returns the branch name or None on failure.
        """
        unique_suffix = str(uuid.uuid4())[:8]
        branch_name = (
            f"fix-{error.test_file.stem}-{error.test_function}-{unique_suffix}"
        )

        logger.info(f"Creating fix branch: {branch_name}")
        try:
            if (
                self.service
                and self.service.git_repo.branch_manager.create_fix_branch(
                    branch_name
                )
            ):
                self.created_branches.add(branch_name)
                return branch_name

            logger.error(f"Failed to create fix branch: {branch_name}")
            return None
        except Exception as branch_err:
            logger.warning(f"Branch creation failed with exception: {branch_err}")
            return None

    def run_fix_workflow(self, error: TestError, interactive: bool) -> bool:
        """
        Run the fix workflow for a single error using AI.
        This workflow now ensures the original branch is checked out upon completion.
        """
        if not self.service:
            logger.error("FixService not initialized, cannot run fix workflow.")
            return False

        original_branch = self.service.git_repo.get_current_branch()
        logger.info(f"Starting fix workflow from branch: {original_branch}")
        success = False

        try:
            logger.info(f"Attempting to fix {error.test_function} in {error.test_file}")

            # 1) Create fix branch
            branch_name = self._create_fix_branch(error)
            if not branch_name:
                return False  # Early exit if branch creation fails

            # 2) Attempt to generate and apply fix
            if self._generate_and_apply_fix(error):
                # 3) On success, handle PR creation
                if interactive:
                    if click.confirm(
                        "Fix succeeded. Would you like to open a Pull Request?",
                        default=True,
                    ):
                        success = self._create_and_push_pr(branch_name, error)
                    else:
                        logger.info("Skipping PR creation at user request.")
                        success = True  # Fix is good, just no PR
                else:
                    # Non-interactive mode: create PR automatically
                    success = self._create_and_push_pr(branch_name, error)

            # If _generate_and_apply_fix failed, success remains False
            return success

        except Exception as e:
            logger.error(f"Fix workflow encountered an error: {str(e)}")
            if DEBUG:
                logger.error(
                    f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}"
                )
            return False
        finally:
            # ALWAYS check out the original branch
            current_branch = self.service.git_repo.get_current_branch()
            if current_branch != original_branch:
                logger.info(f"Checking out original branch: {original_branch}")
                try:
                    self.service.git_repo.run_command(["checkout", original_branch])
                except Exception as e:
                    logger.error(f"Failed to checkout original branch '{original_branch}': {e}")

    def _generate_and_apply_fix(self, error: TestError) -> bool:
        """
        Attempt to generate/apply a fix via AI; return True if successful, False otherwise.
        """
        logger.info("Attempting to generate and apply fix...")
        if self.service and self.service.attempt_fix(error, self.service.initial_temp):
            logger.info(f"Fix attempt for {error.test_function} succeeded.")
            return True
        else:
            logger.warning(f"Fix attempt for {error.test_function} failed.")
            return False

    def _create_and_push_pr(self, branch_name: str, error: TestError) -> bool:
        """
        Create a pull request for the given branch and push to remote.
        Return True if successful or if PR creation fails but the fix was still okay.
        Return False if push fails.
        """
        logger.info("Creating pull request...")
        if self.service and self.service.git_repo.create_pull_request_sync(
            branch_name, error
        ):
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
            # We consider fix successful, but PR creation failed
            return True

    def run_manual_fix_workflow(self, error: TestError) -> str:
        """
        Let the user manually fix the test, then check if it passes:
        - Create a unique fix branch
        - Loop until user either *succeeds*, *skips*, or *quits*.
        - Limit the number of retries to avoid infinite loops.

        Return values:
        - "fixed" => The test now passes after user edits
        - "skip"  => The user pressed 's' to skip
        - "quit"  => The user pressed 'q' to stop manual fix mode entirely
        """
        retry_limit = 5  # Limit the number of retries for manual fixes.
        retries = 0

        # 1) Create fix branch with unique suffix
        branch_name = self._create_fix_branch(error)
        if not branch_name:
            # If branch creation fails entirely, skip
            return "skip"

        while retries < retry_limit:
            click.echo("\n--- MANUAL FIX MODE ---")
            click.echo(
                f"Please open '{error.test_file}' and fix the issue for test '{error.test_function}'."
            )
            user_input = click.prompt(
                "Press Enter to re-run the test, type 's' to skip manual fixing, or 'q' to quit manual fix mode",
                default="",
                show_default=False,
            )

            if user_input.lower() == "s":
                # user chooses skip
                return "skip"
            elif user_input.lower() == "q":
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
                click.echo(
                    f"✗ Test '{error.test_function}' is still failing. ({retries}/{retry_limit} retries used)"
                )

        # If retry limit is reached, exit manual fix mode
        click.echo("Retry limit reached. Exiting manual fix mode.")
        return "quit"

   # @snoop
    def setup_components(self, config: ComponentSettings) -> bool:
        """
        Initialize AI, Test Runner, Change Applier, GitRepo, FixService, & Orchestrator.
        Now uses a single `config` object to address the 'excess function arguments' complaint
        while preserving existing comments and features.
        """
        try:
            logger.info("Initializing AI Manager...")
            ai_manager = AIManager(config.api_key)

            logger.info("Initializing Test Runner...")
            test_runner = TestRunner()

            logger.info("Initializing Change Applier...")
            change_applier = ChangeApplier()

            logger.info("Initializing Git Repository...")
            git_repo = GitRepository()

            logger.info("Creating State Manager...")
            state_manager = StateManager()

            logger.info("Creating Fix Service...")
            self.service = FixService(
                ai_manager=ai_manager,
                test_runner=test_runner,
                change_applier=change_applier,
                git_repo=git_repo,
                max_retries=config.max_retries,
                initial_temp=config.initial_temp,
                temp_increment=config.temp_increment,
                dev_force_success=config.dev_force_success,
                state_manager=state_manager,
            )

            # NEW: Initialize SessionStore to ensure session data is always saved
            from branch_fixer.storage.session_store import SessionStore
            store_dir = Path.cwd() / "session_data"
            store_dir.mkdir(parents=True, exist_ok=True)
            session_store = SessionStore(store_dir)
            self.service.session_store = session_store

            # Optional orchestrator
            logger.info("Creating Orchestrator object for session-based approach...")
            self.orchestrator = FixOrchestrator(
                ai_manager=ai_manager,
                test_runner=test_runner,
                change_applier=change_applier,
                git_repo=git_repo,
                max_retries=config.max_retries,
                initial_temp=config.initial_temp,
                temp_increment=config.temp_increment,
                interactive=True,  # or dev_force_success
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
                logger.error(
                    f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}"
                )
            return False

    # -- START: Extracted user-choice handlers for interactive error --

    def _handle_quit_choice(self, error: TestError) -> bool:
        """Handle the 'q' user choice: quit entirely."""
        click.echo("\nQuitting as requested.")
        logger.info("User chose to quit.")
        return False

    def _handle_skip_choice(self, error: TestError) -> bool:
        """Handle the 'n' user choice: skip this test."""
        click.echo("\nSkipping this test.\n")
        logger.info("User chose to skip.")
        return True

    def _handle_manual_fix_choice(self, error: TestError) -> bool:
        """Handle the 'm' user choice: run manual fix workflow."""
        click.echo("Switching to manual fix mode...\n")
        manual_result = self.run_manual_fix_workflow(error)
        if manual_result == "fixed":
            click.echo(
                f"✓ Successfully fixed '{error.test_function}' via manual fix.\n"
            )
        elif manual_result == "skip":
            click.echo(f"✗ '{error.test_function}' not fixed in manual fix mode.\n")
        elif manual_result == "quit":
            click.echo("\nQuitting as requested.")
            logger.info("User chose to quit manual fix mode entirely.")
            return False
        return True

    def _handle_ai_fix_choice(self, error: TestError) -> bool:
        """Handle the 'y' user choice: run AI-based fix."""
        click.echo("Attempting AI-based fix...\n")
        if self.run_fix_workflow(error, interactive=True):
            click.echo(f"✓ Successfully fixed '{error.test_function}' with AI.\n")
        else:
            click.echo(f"✗ AI fix attempt for '{error.test_function}' failed.\n")
        return True

    # -- END: Extracted user-choice handlers for interactive error --

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
            if choice in ["\r", "\n", ""]:
                choice = "y"

            # Acceptable
            if choice in ["y", "m", "n", "q"]:
                return choice

            # Else re-prompt
            click.echo("\nInvalid choice. Enter 'y', 'm', 'n', or 'q'.")

    def _process_interactive_error(self, error: TestError) -> bool:
        """
        Handles interactive error processing logic.
        Returns True if user chooses to continue, False if user quits.
        """
        choice = self._prompt_for_fix(error)
        handlers = {
            "q": self._handle_quit_choice,
            "n": self._handle_skip_choice,
            "m": self._handle_manual_fix_choice,
            "y": self._handle_ai_fix_choice,
        }

        handler = handlers.get(choice)
        if handler:
            return handler(error)
        else:
            # If somehow not recognized, default to AI fix
            return self._handle_ai_fix_choice(error)

    def _process_non_interactive_error(self, error: TestError):
        """
        Handles non-interactive error processing logic.
        """
        if self.run_fix_workflow(error, interactive=False):
            click.echo(f"✓ AI fix for '{error.test_function}' succeeded.")
        else:
            click.echo(f"✗ AI fix for '{error.test_function}' failed.")

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

            total_processed, success_count = self._process_all_errors(errors, interactive)

            # Summarize if any were processed
            if total_processed > 0:
                self._summarize_results(total_processed, total_errors, success_count)

        finally:
            click.echo("Starting cleanup...")
            self.cleanup()
            click.echo("Cleanup complete.")

        # If the user quit early, total_processed will be less than total_errors.
        # This should result in a non-zero exit code.
        if total_processed < total_errors:
            return 1

        # If you want to tie success_count to actual fix results, incorporate it in the interactive checks.
        # For now we assume success_count remains a placeholder for further logic.
        return 0 if success_count == total_processed else 1

    def _process_all_errors(self, errors: List[TestError], interactive: bool) -> Tuple[int, int]:
        """
        Extracted helper that loops over all errors, handling interactive
        vs. non-interactive flows. Returns total_processed, success_count.
        """
        total_processed = 0
        success_count = 0

        for i, error in enumerate(errors, 1):
            # Early return if user requested exit
            if self._exit_requested:
                logger.info("Exit requested; stopping fix attempts.")
                break

            logger.info(f"\nProcessing error {i}/{len(errors)}: {error.test_function}\n")

            if interactive:
                # If the user chooses to quit in interactive mode, we break out
                if not self._process_interactive_error(error):
                    break
            else:
                self._process_non_interactive_error(error)

            # If you track actual success/fail logic, you can increment success_count here.
            total_processed += 1

        return total_processed, success_count

    def _summarize_results(self, total_processed: int, total_errors: int, success_count: int) -> None:
        """
        Helper to summarize the final fix attempts result.
        """
        click.echo("\nFix attempts complete.")
        click.echo(f"Tests processed: {total_processed}/{total_errors}")
        click.echo(f"Successfully fixed: {success_count}")
        click.echo(f"Failed/skipped: {total_processed - success_count}\n")