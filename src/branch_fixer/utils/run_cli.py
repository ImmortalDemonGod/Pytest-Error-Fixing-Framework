# src/branch_fixer/utils/run_cli.py

import importlib.metadata
import logging
import platform
from pathlib import Path
from typing import Optional

import click
from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.cli import CLI, ComponentSettings

logger = logging.getLogger(__name__)


def get_version() -> str:
    """
    Return the installed distribution version for the `pytest-fixer` package.
    
    Returns:
        str: The package version string, or "unknown (package not installed)" if the package metadata is not available.
    """
    try:
        # The package name "pytest-fixer" is defined in pyproject.toml
        return importlib.metadata.version("pytest-fixer")
    except importlib.metadata.PackageNotFoundError:
        # Graceful fallback for when package is not installed in the environment.
        # This is more informative than a generic error or a misleading version like "0.0.0".
        return "unknown (package not installed)"


@click.group()
@click.version_option(version=get_version(), prog_name="pytest-fixer")
def cli():
    """
    Command-line entry point for pytest-fixer; a Click command group that hosts subcommands.
    
    This command group is configured with the package version and groups commands such as the primary `fix` workflow and optional development subcommands when available.
    """
    pass


@cli.command()
@click.option(
    "--api-key",
    envvar="OPENROUTER_API_KEY",
    required=True,
    help="OpenRouter API key (or set OPENROUTER_API_KEY env var)",
)
@click.option(
    "--max-retries",
    default=3,
    show_default=True,
    help="Maximum number of fix attempts per error",
)
@click.option(
    "--initial-temp", default=0.4, show_default=True, help="Initial temperature for AI"
)
@click.option(
    "--temp-increment",
    default=0.1,
    show_default=True,
    help="Temperature increment between retries",
)
@click.option("--non-interactive", is_flag=True, help="Run without user prompts")
@click.option(
    "--fast-run",
    is_flag=True,
    help="Debug mode: only fix the first failing test and then exit",
)
@click.option(
    "--test-path",
    type=click.Path(exists=True, path_type=Path),
    help="Specific test file or directory to fix",
)
@click.option("--test-function", help="Specific test function to fix")
@click.option("--cleanup-only", is_flag=True, help="Only cleanup leftover fix branches")
@click.option(
    "--dev-force-success",
    is_flag=True,
    help="Force all fix attempts to be marked successful (for dev testing)",
)
# @snoop
def fix(
    api_key: str,
    max_retries: int,
    initial_temp: float,
    temp_increment: float,
    non_interactive: bool,
    fast_run: bool,
    test_path: Optional[Path],
    test_function: Optional[str],
    cleanup_only: bool,
    dev_force_success: bool,
):
    """
    Run pytest, analyze failures, and attempt automated fixes according to the provided options.
    
    This command initializes runtime components, executes the test runner, parses failures, and drives the fix workflows. Depending on flags it can perform a cleanup-only action, run in non-interactive or fast-run (first-failure-only) modes, and persist a session record when applicable.
    
    Parameters:
        api_key (str): API key used by remote services for generating fixes.
        max_retries (int): Maximum number of retry attempts for a single failing test.
        initial_temp (float): Initial randomness/temperature setting for generation-based fixes.
        temp_increment (float): Amount to increase temperature between retries.
        non_interactive (bool): If True, suppress interactive prompts during the fix workflows.
        fast_run (bool): If True, attempt to fix only the first failing test and then exit.
        test_path (Optional[Path]): Path to the tests or test file to run; if None uses default discovery.
        test_function (Optional[str]): Specific test function name to run within the given path.
        cleanup_only (bool): If True, perform cleanup actions and exit without running tests or fixes.
        dev_force_success (bool): If True, simulate successful fixes for development/testing purposes.
    
    Returns:
        int: Exit code where `0` indicates overall success (or cleanup-only success) and `1` indicates failure or an inability to proceed.
    """

    from branch_fixer.services.pytest.error_processor import process_pytest_results
    from branch_fixer.orchestration.orchestrator import FixSession, FixSessionState

    setup_logging()
    logger.info("Starting pytest-fixer...")
    logger.info(f"Working directory: {Path.cwd()}")

    # Create the CLI object
    cli_obj = CLI()

    # Build a parameter object with all relevant settings
    config = ComponentSettings(
        api_key=api_key,
        max_retries=max_retries,
        initial_temp=initial_temp,
        temp_increment=temp_increment,
        dev_force_success=dev_force_success,
    )

    # Setup components using the combined config object
    if not cli_obj.setup_components(config):
        logger.error("Failed to setup components")
        return 1

    # If just doing cleanup
    if cleanup_only:
        cli_obj.cleanup()
        return 0

    # Make sure cli_obj.service is ready if you're using it:
    if not cli_obj.service:
        logger.error("FixService not initialized.")
        return 1

    # Run pytest to find failures
    logger.info("Running pytest to find failures...")
    test_result = cli_obj.service.test_runner.run_test(
        test_path=test_path, test_function=test_function
    )

    # Summarize test results
    total_tests = test_result.total_collected
    failed_tests = test_result.failed
    logger.info(
        f"Test run complete. Total tests: {total_tests}, Failed tests: {failed_tests}"
    )

    # If no failures, let's still record a session in TinyDB for completeness
    if failed_tests == 0:
        logger.info("All tests passed - no fixes needed!")

        # Create a minimal session with 0 failures, mark as COMPLETED
        zero_session = FixSession()
        zero_session.total_tests = total_tests
        zero_session.failed_tests = 0
        zero_session.passed_tests = total_tests
        zero_session.state = FixSessionState.COMPLETED

        # Optionally gather environment details
        zero_session.environment_info = {
            "os": platform.system(),
            "python_version": platform.python_version(),
        }

        # Store warnings from the test run
        zero_session.warnings = test_result.warnings  # <--- ADDED

        # If session_store is available, persist it
        if cli_obj.service.session_store:
            cli_obj.service.session_store.save_session(zero_session)

        return 0

    # Parse errors
    logger.info("Analyzing test failures...")
    errors = process_pytest_results(test_result)
    if not errors:
        logger.warning("Tests failed but no parsable test failures found")
        return 1

    logger.info(f"Found {len(errors)} test failures to fix")

    # FAST-RUN logic: fix just the first failing test, then exit
    if fast_run:
        first_error = errors[0]
        logger.info("FAST-RUN mode enabled. Only fixing the first failing test.")
        success = cli_obj.run_fix_workflow(first_error, interactive=False)
        if success:
            click.echo("FAST-RUN: Successfully fixed the first failing test!\n")
            return 0
        else:
            click.echo("FAST-RUN: Failed to fix the first failing test.\n")
            return 1

    # Otherwise, proceed with normal multi-test flow
    return cli_obj.process_errors(errors, not non_interactive)


try:
    from dev.cli.generate import generate_command

    cli.add_command(generate_command)
except ImportError:
    pass  # generate subcommand unavailable outside dev environment


def main():
    """
    Invoke the CLI application and return its exit code.
    
    Returns:
        int: Exit code (0 on success, non-zero on failure).
    """
    return cli()
