# tests/git/test_repository.py
from pathlib import Path
import pytest
from datetime import datetime
from branch_fixer.git.exceptions import NotAGitRepositoryError
from branch_fixer.git import GitRepository

class TestRepositoryInitialization:
    """Test suite for git repository initialization behaviors"""
    
    def test_repository_detects_valid_git_directory(self, temporary_repository):
        """
        Repository should recognize a valid git directory.
        
        Given: A directory containing .git metadata
        When: Initializing a GitRepository
        Then: It should validate successfully
        """
        repo = GitRepository(temporary_repository)
        assert repo.has_version_control()

    def test_repository_rejects_non_git_directory(self, temporary_directory):
        """
        Repository should reject directories without git metadata.
        
        Given: A directory without .git metadata
        When: Initializing a GitRepository
        Then: It should raise NotAGitRepositoryError
        """
        with pytest.raises(NotAGitRepositoryError) as exc:
            GitRepository(temporary_directory)
        assert "not a git repository" in str(exc.value).lower()

    def test_repository_finds_root_from_subdirectory(self, temporary_repository):
        """
        Repository should locate git root from any subdirectory.
        
        Given: A git repository with nested directories
        When: Initializing from a subdirectory
        Then: It should find the repository root
        """
        # Create nested directory
        subdir = temporary_repository / "src" / "nested" / "deep"
        subdir.mkdir(parents=True)
        
        # When initializing from subdirectory
        repo = GitRepository(subdir)
        
        # Then should find actual root
        assert repo.root.samefile(temporary_repository)
        assert (repo.root / ".git").exists()
        assert (repo.root / ".git" / "HEAD").exists()

class TestMainBranchIdentification:
    """Test suite for main branch detection behaviors"""
    
    def test_repository_identifies_default_branch(self, temporary_repository):
        """
        Repository should identify the default development branch.
        
        Given: A git repository
        When: Checking the main branch
        Then: It should identify either 'main' or 'master'
        """
        repo = GitRepository(temporary_repository)
        assert repo.main_branch in ("main", "master")

class TestRepositoryState:
    """Test suite for repository state behaviors"""
    
    def test_detects_clean_state(self, temporary_repository):
        """
        Repository should detect whether working directory is clean.
        
        Given: A git repository
        When: Checking repository state
        Then: Should accurately report clean/dirty state
        """
        repo = GitRepository(temporary_repository)
        assert repo.is_clean() is True
        
        # Create an untracked file
        (temporary_repository / "test.txt").write_text("change")
        assert repo.is_clean() is False

    def test_reports_current_branch(self, temporary_repository):
        """
        Repository should report currently checked out branch.
        
        Given: A git repository
        When: Requesting current branch
        Then: Should return current branch name
        """
        repo = GitRepository(temporary_repository)
        assert repo.get_current_branch() == "main"

    def test_validates_branch_existence(self, temporary_repository):
        """
        Repository should validate branch existence.
        
        Given: A git repository
        When: Checking if branches exist
        Then: Should correctly identify existing and non-existing branches
        """
        repo = GitRepository(temporary_repository)
        assert repo.branch_exists("main") is True
        assert repo.branch_exists("nonexistent") is False

@pytest.fixture
def temporary_directory():
    """
    Creates an empty temporary directory for testing.
    
    Returns:
        Path: Path to temporary directory
    
    Notes:
        - Directory is automatically cleaned up after test
        - Creates unique directory based on timestamp
    """
    test_dir = Path("/tmp") / f"test-{datetime.now().timestamp()}"
    test_dir.mkdir(parents=True)
    try:
        yield test_dir
    finally:
        import shutil
        shutil.rmtree(test_dir)

@pytest.fixture
def temporary_repository(temporary_directory):
    """
    Creates a temporary git repository for testing.
    
    Args:
        temporary_directory: Base directory fixture
    
    Returns:
        Path: Path to repository root
    
    Notes:
        - Creates minimal .git structure
        - Sets up main branch as default
        - Clean up handled by temporary_directory fixture
    """
    # Initialize git repository structure
    (temporary_directory / ".git").mkdir()
    (temporary_directory / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (temporary_directory / ".git" / "refs" / "heads").mkdir(parents=True)
    (temporary_directory / ".git" / "refs" / "heads" / "main").touch()
    
    return temporary_directory
    def test_identifies_main_branch_correctly(self, temporary_repository):
        """Should correctly identify the main branch from HEAD"""
        # Given
        head_file = temporary_repository / ".git" / "HEAD"
        
        # When HEAD points to main
        head_file.write_text("ref: refs/heads/main")
        repo = GitRepository(temporary_repository)
        assert repo.main_branch == "main"
        
        # When HEAD points to master
        head_file.write_text("ref: refs/heads/master")
        repo = GitRepository(temporary_repository)
        assert repo.main_branch == "master"
        
        # When HEAD is invalid
        head_file.write_text("invalid content")
        with pytest.raises(GitError):
            GitRepository(temporary_repository)

    def test_repository_initialization_errors(self, temporary_directory):
        """Should handle various initialization errors appropriately"""
        # Missing .git directory
        with pytest.raises(NotAGitRepositoryError):
            GitRepository(temporary_directory)
        
        # Invalid .git directory structure
        bad_git = temporary_directory / ".git"
        bad_git.mkdir()
        with pytest.raises(NotAGitRepositoryError):
            GitRepository(temporary_directory)
        
        # No read permissions
        bad_git.chmod(0o000)
        with pytest.raises(PermissionError):
            GitRepository(temporary_directory)

    def test_command_execution_errors(self, temporary_repository):
        """Should handle command execution errors appropriately"""
        repo = GitRepository(temporary_repository)
        
        # Non-existent command
        with pytest.raises(GitError) as exc:
            repo.run_command(["git", "nonexistent"])
        assert "unknown git command" in str(exc.value).lower()
        
        # Invalid arguments
        with pytest.raises(GitError) as exc:
            repo.run_command(["git", "--invalid-flag"])
        assert "unknown option" in str(exc.value).lower()
