# tests/git/test_repository.py
from pathlib import Path
import pytest
from datetime import datetime

class TestRepositoryInitialization:
    def test_repository_detects_valid_git_directory(self):
        """Should recognize a directory with version control"""
        with temporary_repository() as repo_path:
            repo = GitRepository(repo_path)
            assert repo.has_version_control()

    def test_repository_rejects_non_git_directory(self):
        """Should reject directories without version control"""
        with temporary_directory() as non_git_dir:
            with pytest.raises(NotAGitRepositoryError) as exc:
                GitRepository(non_git_dir)
            assert "not a git repository" in str(exc.value).lower()

    def test_repository_finds_root_from_subdirectory(self):
        """Should find repository root from any subdirectory"""
        with temporary_repository() as repo_path:
            # Create nested directory structure
            subdir = repo_path / "src" / "nested" / "deep"
            subdir.mkdir(parents=True)
            
            repo = GitRepository(subdir)
            assert repo.root == repo_path

class TestMainBranchIdentification:
    def test_repository_identifies_default_branch(self):
        """Should identify the default development branch"""
        with temporary_repository() as repo_path:
            repo = GitRepository(repo_path)
            assert repo.main_branch in ("main", "master")

# Test fixtures and helpers
@pytest.fixture
def temporary_directory():
    """Creates a temporary directory for testing"""
    test_dir = Path("/tmp") / f"test-{datetime.now().timestamp()}"
    test_dir.mkdir(parents=True)
    try:
        yield test_dir
    finally:
        import shutil
        shutil.rmtree(test_dir)

@pytest.fixture
def temporary_repository():
    """Creates a temporary git repository for testing"""
    with temporary_directory() as test_dir:
        # Initialize git repository structure
        (test_dir / ".git").mkdir()
        (test_dir / ".git" / "HEAD").write_text("ref: refs/heads/main")
        yield test_dir

# Custom exceptions
class NotAGitRepositoryError(Exception):
    """Raised when a directory is not a git repository"""