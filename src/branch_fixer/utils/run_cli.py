# src/branch_fixer/utils/run_cli.py

import logging
from pathlib import Path
from typing import Optional

import click

from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.cli import CLI, ComponentSettings

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Pytest Error Fixing Framework - Automatically fix failing pytest tests."""
    pass


@cli.command()
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    required=True,
    help="OpenAI API key (or set OPENAI_API_KEY env var)",
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
    Fix failing pytest tests automatically.
    """

    from branch_fixer.services.pytest.error_processor import parse_pytest_errors

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

    # If no failures, nothing to fix
    if failed_tests == 0:
        logger.info("All tests passed - no fixes needed!")
        return 0

    # Parse errors
    logger.info("Analyzing test failures...")
    errors = parse_pytest_errors(test_result.output)
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


def main():
    """Main entry point."""
    return cli()
