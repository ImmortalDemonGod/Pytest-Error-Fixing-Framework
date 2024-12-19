# tests/unit/git/conftest.py
import pytest
from unittest.mock import Mock, MagicMock, create_autospec
from pathlib import Path
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.git.branch_manager import BranchManager

@pytest.fixture
def clean_repo():
    """Create a mock GitRepository in a clean state."""
    # Create a proper mock spec from the GitRepository class
    repo = create_autospec(GitRepository, instance=True)
    
    # Configure standard responses
    repo.is_clean.return_value = True
    repo.get_current_branch.return_value = "main"
    repo.has_uncommitted_changes.return_value = False
    repo.branch_exists.return_value = False
    repo.create_branch.return_value = True
    repo.merge_branch.return_value = True
    
    # Setup status attribute 
    status = MagicMock()
    status.changes = []
    repo.status = status
    
    return repo

@pytest.fixture
def dirty_repo():
    """Create a mock GitRepository in a dirty state."""
    # Create a proper mock spec from the GitRepository class
    repo = create_autospec(GitRepository, instance=True)
    
    # Configure responses for dirty state
    repo.is_clean.return_value = False
    repo.get_current_branch.return_value = "feature"
    repo.has_uncommitted_changes.return_value = True
    
    # Setup status with changes
    status = MagicMock()
    status.changes = ["modified: file1.py"]
    repo.status = status
    
    return repo

@pytest.fixture
def branch_manager(clean_repo):
    """Create a BranchManager instance with a clean repo."""
    manager = BranchManager(clean_repo)
    return manager