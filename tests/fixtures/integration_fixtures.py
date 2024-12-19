import pytest
from pathlib import Path
from typing import List
from unittest.mock import Mock, AsyncMock

from branch_fixer.core.models import TestError, ErrorDetails
from branch_fixer.orchestration.fix_service import FixService
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import PytestRunner as TestRunner
from branch_fixer.code.change_applier import ChangeApplier
from branch_fixer.git.repository import GitRepository

@pytest.fixture
def error_factory():
    """Creates test errors with controlled configuration.
    
    Returns a factory function to create TestError instances with specified 
    parameters, ensuring consistent test error creation.
    """
    def create(
        file: str = "test_example.py",
        func: str = "test_something",
        error_type: str = "AssertionError",
        message: str = "Expected 5 but got 4"
    ) -> TestError:
        return TestError(
            test_file=Path(f"tests/{file}"),
            test_function=func,
            error_details=ErrorDetails(
                error_type=error_type,
                message=message
            )
        )
    return create

@pytest.fixture
def service_factory():
    """Creates FixService instances with controlled behaviors.
    
    Returns a factory function to create FixService instances with 
    configurable component behaviors.
    """
    def create(*, 
        branch_success: bool = True,
        ai_responses: List[dict] = None,
        test_results: List[bool] = None,
        max_retries: int = 3
    ) -> FixService:
        # Setup AI manager
        ai_manager = AsyncMock(spec=AIManager)
        ai_manager.generate_fix.side_effect = ai_responses or [
            {"original": "old", "modified": "new"}
        ]

        # Setup test runner
        test_runner = Mock(spec=TestRunner)
        test_runner.run_test.side_effect = test_results or [True]

        # Setup change applier
        change_applier = Mock(spec=ChangeApplier)
        change_applier.apply_changes.return_value = True

        # Setup git repo
        git_repo = Mock(spec=GitRepository)
        git_repo.create_branch.return_value = branch_success
        git_repo.create_pull_request.return_value = True

        return FixService(
            ai_manager=ai_manager,
            test_runner=test_runner,
            change_applier=change_applier,
            git_repo=git_repo,
            max_retries=max_retries
        )
    return create
