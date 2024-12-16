# tests/git/test_repository.py
from pathlib import Path
import pytest
from datetime import datetime
from branch_fixer.git.exceptions import NotAGitRepositoryError
from branch_fixer.git import GitRepository, GitError

class TestRepositoryInitialization:
    """Test suite for git repository initialization behaviors"""
    
    def test_repository_detects_valid_git_directory(self, temporary_repository):
        """Should recognize a valid git directory"""
        repo = GitRepository(temporary_repository)
        assert repo.has_version_control()

    def test_repository_rejects_non_git_directory(self, temporary_directory):
        """Should reject directories without git metadata"""
        with pytest.raises(NotAGitRepositoryError) as exc:
            GitRepository(temporary_directory)
        assert "not a git repository" in str(exc.value).lower()

    def test_repository_finds_root_from_subdirectory(self, temporary_repository):
        """Should find repository root from any subdirectory"""
        # Create nested directory
        subdir = temporary_repository / "src" / "nested" / "deep"
        subdir.mkdir(parents=True)
        
        # When initializing from subdirectory
        repo = GitRepository(subdir)
        
        # Then should find actual root
        assert repo.root.samefile(temporary_repository)
        assert (repo.root / ".git").exists()
        assert (repo.root / ".git" / "HEAD").exists()

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

class TestRepositoryState:
    """Test suite for repository state behaviors"""
    
    def test_detects_clean_state(self, temporary_repository):
        """Should detect whether working directory is clean"""
        repo = GitRepository(temporary_repository)
        assert repo.is_clean() is True
        
        # Create an untracked file
        (temporary_repository / "test.txt").write_text("change")
        assert repo.is_clean() is False

    def test_reports_current_branch(self, temporary_repository):
        """Should report currently checked out branch"""
        repo = GitRepository(temporary_repository)
        assert repo.get_current_branch() == "main"

    def test_validates_branch_existence(self, temporary_repository):
        """Should validate branch existence"""
        repo = GitRepository(temporary_repository)
        assert repo.branch_exists("main") is True
        assert repo.branch_exists("nonexistent") is False

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

