# tests/unit/git/conftest.py
import pytest
from unittest.mock import Mock, MagicMock, create_autospec
from pathlib import Path
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.git.branch_manager import BranchManager

@pytest.fixture
def clean_repo():
    """
    Create a mock GitRepository in a clean state.
    This fixture sets up the repository to appear 'clean' with no changes 
    and a default branch of 'main'.
    """
    # Create a proper mock spec from the GitRepository class
    repo = create_autospec(GitRepository, instance=True)
    
    # Configure standard responses
    repo.is_clean.return_value = True
    repo.get_current_branch.return_value = "main"
    
    # For BranchManager usage: 
    # 'branch_exists' is used by create_fix_branch() checks
    repo.branch_exists.return_value = False
    # The real method is 'create_fix_branch', not 'create_branch'
    repo.create_fix_branch.return_value = True
    
    # If your tests call a hypothetical 'merge_branch' or other git methods, keep them
    repo.merge_branch.return_value = True
    
    # Setup a status attribute for further mocking if needed
    status = MagicMock()
    status.changes = []
    repo.status = status
    
    return repo

@pytest.fixture
def dirty_repo():
    """
    Create a mock GitRepository in a dirty state.
    This fixture sets up the repository to appear 'dirty' with some 
    uncommitted changes and a non-main branch named 'feature'.
    """
    # Create a proper mock spec from the GitRepository class
    repo = create_autospec(GitRepository, instance=True)
    
    # Configure responses for a dirty repo
    repo.is_clean.return_value = False
    repo.get_current_branch.return_value = "feature"
    
    # Setup status with changes
    status = MagicMock()
    status.changes = ["modified: file1.py"]
    repo.status = status
    
    return repo

@pytest.fixture
def branch_manager(clean_repo):
    """
    Create a BranchManager instance with a clean repo mock.
    This manager uses the 'clean_repo' fixture by default, 
    but you can override with 'dirty_repo' if needed.
    """
    manager = BranchManager(clean_repo)
    return manager
