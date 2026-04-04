import pytest
from pathlib import Path
from typing import List
from unittest.mock import Mock, MagicMock

from branch_fixer.core.models import TestError, ErrorDetails
from branch_fixer.orchestration.fix_service import FixService
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import PytestRunner as TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository

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
    """
    Provide a factory that constructs FixService instances with mocked collaborators and configurable behaviors.
    
    The returned factory function accepts these keyword parameters to control mock behavior:
    - branch_success (bool): Whether the mocked Git repository successfully creates a fix branch.
    - ai_responses (List[dict] | None): Sequence of values to use as `ai_manager.generate_fix` side effects; defaults to a single dict with `{"original": "old", "modified": "new"}`.
    - test_results (List[bool] | None): Sequence of boolean values to use as `test_runner.run_test` side effects; defaults to `[True]`.
    - max_retries (int): `max_retries` passed to the constructed FixService.
    
    Returns:
        Callable[..., FixService]: A factory function that returns a FixService configured with mocked AI manager, test runner, change applier, and git repository according to the provided parameters.
    """
    def create(*, 
        branch_success: bool = True,
        ai_responses: List[dict] = None,
        test_results: List[bool] = None,
        max_retries: int = 3
    ) -> FixService:
        # Setup AI manager
        """
        Create a FixService instance whose collaborators are mocked with configurable outcomes for use in tests.
        
        Parameters:
            branch_success (bool): Value returned by the mocked git repository's create_fix_branch (default True).
            ai_responses (List[dict] | None): Sequence of responses used as side effects for the mocked AI manager's generate_fix; if None, a single response {"original": "old", "modified": "new"} is used.
            test_results (List[bool] | None): Sequence of booleans used as side effects for the mocked test runner's run_test; if None, a single True is used.
            max_retries (int): The max_retries value passed to the created FixService (default 3).
        
        Returns:
            FixService: A FixService configured with mocked ai_manager, test_runner, change_applier, and git_repo. The mocks exhibit the observable behaviors described by the parameters:
              - ai_manager.generate_fix yields values from `ai_responses` (or the default).
              - test_runner.run_test yields values from `test_results` (or the default).
              - change_applier.apply_changes_with_backup returns (True, None).
              - git_repo.create_fix_branch returns `branch_success`; git_repo.create_pull_request_sync returns True.
        """
        ai_manager = MagicMock(spec=AIManager)
        ai_manager.generate_fix.side_effect = ai_responses or [
            {"original": "old", "modified": "new"}
        ]

        # Setup test runner
        test_runner = Mock(spec=TestRunner)
        test_runner.run_test.side_effect = test_results or [True]

        # Setup change applier
        change_applier = Mock(spec=ChangeApplier)
        change_applier.apply_changes_with_backup.return_value = (True, None)

        # Setup git repo
        git_repo = Mock(spec=GitRepository)
        git_repo.create_fix_branch.return_value = branch_success
        git_repo.create_pull_request_sync.return_value = True

        return FixService(
            ai_manager=ai_manager,
            test_runner=test_runner,
            change_applier=change_applier,
            git_repo=git_repo,
            max_retries=max_retries
        )
    return create
