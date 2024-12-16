import pytest
from pathlib import Path
from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from branch_fixer.git.exceptions import NotAGitRepositoryError

@pytest.fixture
def empty_directory(tmp_path):
    """Create an empty directory without git initialization."""
    return tmp_path

@pytest.fixture
def temporary_repository(tmp_path):
    """Create a temporary git repository with proper initialization"""
    # Initialize git repo
    repo = Repo.init(tmp_path)
    
    # Configure test identity for commits
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")
    
    # Create initial commit so we have a HEAD 
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    # Set HEAD to point to main by default
    head_path = tmp_path / ".git" / "HEAD" 
    head_path.write_text("ref: refs/heads/main")
    
    return tmp_path

@pytest.fixture
def nested_repository(temporary_repository):
    """Create a Git repository with nested directories."""
    nested_path = temporary_repository / "src" / "nested" / "deep"
    nested_path.mkdir(parents=True)
    return temporary_repository

@pytest.fixture
def dirty_repository(temporary_repository):
    """Create a Git repository with uncommitted changes."""
    file_path = temporary_repository / "new_file.txt"
    file_path.write_text("uncommitted change")
    return temporary_repository
