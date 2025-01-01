# tests/integration/pytest/conftest.py
import pytest
import pytest_asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock
from textwrap import dedent

from _pytest.reports import TestReport
from _pytest.main import ExitCode
from branch_fixer.services.pytest.runner import PytestRunner

@pytest.fixture
def runner(test_suite_dir):
    """Create PytestRunner instance with test directory."""
    return PytestRunner(working_dir=test_suite_dir)

# tests/unit/git/conftest.py
import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.git.branch_manager import BranchManager

@pytest.fixture
def clean_repo():
    """Mock of a clean git repository."""
    repo = Mock(spec=GitRepository)
    repo.is_clean.return_value = True
    repo.branch_exists.return_value = False
    repo.create_branch.return_value = True
    repo.merge_branch.return_value = True
    return repo

@pytest.fixture
def branch_manager(clean_repo):
    """Create a BranchManager instance with mocked repo."""
    return BranchManager(clean_repo)