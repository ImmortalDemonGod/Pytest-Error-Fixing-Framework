import pytest
from pathlib import Path
from git import Repo

@pytest.fixture
def empty_directory(tmp_path):
    """Create an empty directory without git initialization."""
    return tmp_path

@pytest.fixture
def temporary_directory(tmp_path):
    """Provides a temporary directory for testing."""
    return tmp_path

# We can also add a helper method to create git repositories
def init_repository(path: Path) -> None:
    """Initialize a git repository with some basic setup."""
    repo = Repo.init(path)
    
    # Create an initial commit so we have a master/main branch
    repo.index.commit("Initial commit")

@pytest.fixture 
def temporary_repository(temporary_directory):
    """Provides a temporary git repository for testing."""
    init_repository(temporary_directory)
    return temporary_directory

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
