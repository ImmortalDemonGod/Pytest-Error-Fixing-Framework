# branch_fixer/utils/cli.py
import click
import logging
import asyncio
from pathlib import Path
from typing import Optional, List
import traceback

from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.core.models import TestError
from branch_fixer.services.pytest.error_processor import parse_pytest_errors
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.config.settings import DEBUG
from branch_fixer.config.logging_config import setup_logging
from branch_fixer.orchestration.fix_service import FixService

logger = logging.getLogger(__name__)

class CLI:
    """CLI interface for pytest-fixer"""
    
    def __init__(self):
        self.service = None
        
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
            asyncio.get_event_loop().run_until_complete(
                self.service.validator.validate_workspace(Path.cwd())
            )
            
            logger.info("Checking dependencies...")
            asyncio.get_event_loop().run_until_complete(
                self.service.validator.check_dependencies()
            )
            
            logger.info("Component initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Component initialization failed: {str(e)}")
            if DEBUG:
                logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            return False

    async def run_fix_workflow(self, error: TestError, interactive: bool) -> bool:
        """Run fix workflow for a single error."""
        try:
            logger.info(f"Attempting to fix {error.test_function} in {error.test_file}")
            
            # Create fix branch
            branch_name = f"fix-{error.test_file.stem}-{error.test_function}"
            if not self.service.git_repo.create_fix_branch(branch_name):
                logger.error(f"Failed to create fix branch: {branch_name}")
                return False
                
            # Attempt fix
            logger.info("Attempting to generate and apply fix...")
            if await self.service.attempt_fix(error):
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
            logger.error(f"Fix workflow failed: {e}")
            if DEBUG:
                logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            return False

    def process_errors(self, errors: List[TestError], interactive: bool) -> int:
        """Process all found errors."""
        success_count = 0
        
        logger.info(f"\nStarting fix attempts for {len(errors)} failed tests")
        for i, error in enumerate(errors, 1):
            logger.info(f"\nProcessing error {i}/{len(errors)}:")
            logger.info(f"Test: {error.test_function}")
            logger.info(f"Error: {error.error_details.error_type}: {error.error_details.message}")

            if interactive:
                if not click.confirm(f"\nAttempt to fix {error.test_function}?", default=True):
                    logger.info("Skipping fix attempt as per user request")
                    continue

            if asyncio.get_event_loop().run_until_complete(self.run_fix_workflow(error, interactive)):
                success_count += 1
                logger.info(f"Successfully fixed {error.test_function}")
            else:
                logger.warning(f"Failed to fix {error.test_function}")

        logger.info(f"\nFix attempts completed:")
        logger.info(f"- Total errors: {len(errors)}")
        logger.info(f"- Successfully fixed: {success_count}")
        logger.info(f"- Failed to fix: {len(errors) - success_count}")
        
        return 0 if success_count == len(errors) else 1

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
def run_cli(api_key: str,
            max_retries: int,
            initial_temp: float,
            temp_increment: float,
            non_interactive: bool,
            test_path: Optional[Path],
            test_function: Optional[str]) -> int:
    """pytest-fixer: Automatically fix failing pytest tests."""
    
    # Setup logging
    setup_logging()
    logger.info("Starting pytest-fixer...")
    logger.info(f"Working directory: {Path.cwd()}")
    
    cli = CLI()
    if not cli.setup_components(api_key, max_retries, initial_temp, temp_increment):
        return 1

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