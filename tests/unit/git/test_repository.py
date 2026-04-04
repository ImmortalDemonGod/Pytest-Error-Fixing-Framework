"""Tests for GitRepository — init, branch ops, run_command, is_clean, and helper methods."""
import pytest
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from branch_fixer.services.git.exceptions import (
    BranchCreationError,
    BranchNameError,
    GitError,
    NotAGitRepositoryError,
)
from branch_fixer.services.git.models import CommandResult
from branch_fixer.services.git.repository import GitRepository


# ---------------------------------------------------------------------------
# Fixture: real git repo in tmp_path
# ---------------------------------------------------------------------------

@pytest.fixture
def git_repo(tmp_path) -> GitRepository:
    """
    Create a real Git repository at tmp_path with an initial commit on branch "main".
    
    Parameters:
        tmp_path (pathlib.Path): Directory where the repository will be created (pytest tmp_path fixture).
    
    Returns:
        GitRepository: A GitRepository instance rooted at tmp_path.
    """
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return GitRepository(root=tmp_path)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_raises_for_non_git_dir(self, tmp_path):
        # __init__ catches NotAGitRepositoryError and re-wraps as GitError
        with pytest.raises(GitError):
            GitRepository(root=tmp_path)

    def test_sets_root(self, git_repo, tmp_path):
        assert git_repo.root == tmp_path

    def test_sets_main_branch(self, git_repo):
        assert git_repo.main_branch == "main"

    def test_pr_manager_initialized(self, git_repo):
        assert git_repo.pr_manager is not None

    def test_branch_manager_initialized(self, git_repo):
        assert git_repo.branch_manager is not None


# ---------------------------------------------------------------------------
# has_version_control
# ---------------------------------------------------------------------------

class TestHasVersionControl:
    def test_returns_true_for_valid_repo(self, git_repo):
        assert git_repo.has_version_control() is True


# ---------------------------------------------------------------------------
# get_current_branch / get_current_branch_sync
# ---------------------------------------------------------------------------

class TestGetCurrentBranch:
    def test_returns_main(self, git_repo):
        assert git_repo.get_current_branch() == "main"

    def test_sync_returns_main(self, git_repo):
        assert git_repo.get_current_branch_sync() == "main"


# ---------------------------------------------------------------------------
# is_clean / is_clean_sync
# ---------------------------------------------------------------------------

class TestIsClean:
    def test_clean_repo_returns_true(self, git_repo):
        assert git_repo.is_clean() is True

    def test_dirty_repo_returns_false(self, git_repo, tmp_path):
        (tmp_path / "new_file.py").write_text("x = 1")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        assert git_repo.is_clean() is False

    def test_clean_sync_returns_true(self, git_repo):
        assert git_repo.is_clean_sync() is True


# ---------------------------------------------------------------------------
# branch_exists / branch_exists_sync
# ---------------------------------------------------------------------------

class TestBranchExists:
    def test_existing_branch_returns_true(self, git_repo):
        assert git_repo.branch_exists("main") is True

    def test_missing_branch_returns_false(self, git_repo):
        assert git_repo.branch_exists("no-such-branch") is False

    def test_sync_existing_returns_true(self, git_repo):
        assert git_repo.branch_exists_sync("main") is True

    def test_sync_missing_returns_false(self, git_repo):
        assert git_repo.branch_exists_sync("no-such-branch") is False


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

class TestRunCommand:
    def test_status_returns_command_result(self, git_repo):
        result = git_repo.run_command(["status"])
        assert isinstance(result, CommandResult)

    def test_successful_command_has_zero_returncode(self, git_repo):
        result = git_repo.run_command(["status"])
        assert result.returncode == 0

    def test_git_prefix_stripped(self, git_repo):
        # Passing ["git", "status"] should work the same as ["status"]
        result = git_repo.run_command(["git", "status"])
        assert result.returncode == 0

    def test_unknown_command_raises_git_error(self, git_repo):
        with pytest.raises(GitError):
            git_repo.run_command(["nonexistent-subcommand-xyz"])


# ---------------------------------------------------------------------------
# create_fix_branch
# ---------------------------------------------------------------------------

class TestCreateFixBranch:
    def test_creates_new_branch(self, git_repo, tmp_path):
        git_repo.create_fix_branch("fix/my-feature")
        assert git_repo.branch_exists("fix/my-feature") is True

    def test_returns_true_on_success(self, git_repo):
        result = git_repo.create_fix_branch("fix/success")
        assert result is True

    def test_raises_on_duplicate_branch(self, git_repo):
        git_repo.create_fix_branch("fix/duplicate")
        # Switch back to main first
        subprocess.run(["git", "checkout", "main"], cwd=git_repo.root, check=True, capture_output=True)
        with pytest.raises(BranchCreationError):
            git_repo.create_fix_branch("fix/duplicate")

    def test_raises_on_invalid_branch_name(self, git_repo):
        with pytest.raises(BranchNameError):
            git_repo.create_fix_branch("invalid..name")


# ---------------------------------------------------------------------------
# validate_branch_name
# ---------------------------------------------------------------------------

class TestValidateBranchName:
    def test_valid_simple_name(self, git_repo):
        assert git_repo.validate_branch_name("fix/my-branch") is True

    def test_rejects_double_dot(self, git_repo):
        assert git_repo.validate_branch_name("bad..name") is False

    def test_rejects_space(self, git_repo):
        assert git_repo.validate_branch_name("bad name") is False
