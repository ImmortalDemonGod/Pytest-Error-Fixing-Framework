# src/branch_fixer/utils/run_cli.py
import click
import logging
import asyncio
from pathlib import Path
from typing import Optional
from branch_fixer.services.pytest.error_processor import parse_pytest_errors
from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.cli import CLI

logger = logging.getLogger(__name__)


@click.command()
@click.option('--api-key', envvar='OPENAI_API_KEY', required=True,
              help='OpenAI API key (or set OPENAI_API_KEY env var)')
@click.option('--max-retries', default=3,
              help='Maximum fix attempts per error')
@click.option('--initial-temp', default=0.4,
              help='Initial AI temperature')
@click.option('--temp-increment', default=0.1, 
              help='Temperature increment between retries')
@click.option('--non-interactive', is_flag=True,
              help='Run without user prompts')
@click.option('--test-path', type=click.Path(exists=True, path_type=Path),
              help='Specific test file or directory to fix')
@click.option('--test-function',
              help='Specific test function to fix')
@click.option('--cleanup-only', is_flag=True,
              help='Just cleanup any leftover fix branches and exit')
def run_cli(api_key: str,
            max_retries: int,
            initial_temp: float,
            temp_increment: float,
            non_interactive: bool,
            test_path: Optional[Path],
            test_function: Optional[str],
            cleanup_only: bool) -> int:
    """pytest-fixer: Automatically fix failing pytest tests."""
    
    setup_logging()
    logger.info("Starting pytest-fixer...")
    logger.info(f"Working directory: {Path.cwd()}")
    
    cli = CLI()
    if not cli.setup_components(api_key, max_retries, initial_temp, temp_increment):
        return 1

    if cleanup_only:
        asyncio.get_event_loop().run_until_complete(cli.cleanup())
        return 0

    # Initial test run
    logger.info("Running pytest to find failures...")
    test_result = cli.service.test_runner.run_test(
        test_path=test_path,
        test_function=test_function
    )

    if test_result.exit_code == 0:
        logger.info("All tests passed - no fixes needed!")
        return 0

    # Parse errors
    logger.info("Analyzing test failures...")
    errors = parse_pytest_errors(test_result.output)
    if not errors:
        logger.error("Tests failed but no fixable errors were found")
        return 1

    logger.info(f"Found {len(errors)} test failures to fix")
    return cli.process_errors(errors, not non_interactive)

if __name__ == "__main__":
    run_cli()