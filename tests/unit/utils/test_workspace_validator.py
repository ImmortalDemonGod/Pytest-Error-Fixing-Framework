"""
Combined test file for WorkspaceValidator in branch_fixer/utils/workspace.py
Leverages pytest fixtures, parametrization, and Hypothesis to maximize coverage
and minimize flaky failures.
"""

import os
import pytest
import importlib
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
from git import Repo, InvalidGitRepositoryError
from hypothesis import given, strategies as st, reject
from src.branch_fixer.utils.workspace import WorkspaceValidator
from src.branch_fixer.services.git.exceptions import NotAGitRepositoryError

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
#                               FIXTURES
# -----------------------------------------------------------------------------
@pytest.fixture
def tmp_non_git_dir(tmp_path: Path) -> Path:
    """
    Pytest fixture providing a temporary directory without a .git folder.
    """
    return tmp_path  # No .git, ensures 'find_git_root' and 'validate_workspace' fail.


@pytest.fixture
def tmp_git_dir(tmp_path: Path) -> Path:
    """
    Pytest fixture providing a temporary directory with an initialized .git repository.
    """
    Repo.init(tmp_path)  # Initialize a local Git repo
    return tmp_path


# -----------------------------------------------------------------------------
#                           TEST: find_git_root
# -----------------------------------------------------------------------------
def test_find_git_root_with_direct_git_dir(tmp_git_dir: Path) -> None:
    """
    Confirm find_git_root identifies the Git root immediately if .git is at the same level.
    """
    found_root = WorkspaceValidator.find_git_root(tmp_git_dir)
    assert found_root == tmp_git_dir, "Expected Git root to match directory containing .git"


def test_find_git_root_nested_subdirectory(tmp_git_dir: Path) -> None:
    """
    Confirm find_git_root climbs directory tree until it finds .git.
    """
    nested_dir = tmp_git_dir / "nested" / "deep"
    nested_dir.mkdir(parents=True)

    found_root = WorkspaceValidator.find_git_root(nested_dir)
    assert found_root == tmp_git_dir, "Expected Git root to match top-level repo directory"


def test_find_git_root_no_git_directory(tmp_non_git_dir: Path) -> None:
    """
    Confirm find_git_root raises NotAGitRepositoryError if there's no .git folder.
    """
    with pytest.raises(NotAGitRepositoryError) as exc:
        WorkspaceValidator.find_git_root(tmp_non_git_dir)
    assert "Failed to find Git repository" in str(exc.value), "Error should indicate .git was not found"


def test_find_git_root_unexpected_exception(tmp_non_git_dir: Path) -> None:
    """
    Force an unexpected exception inside find_git_root to check error wrapping coverage.
    """
    with patch("pathlib.Path.absolute", side_effect=Exception("Unexpected error")):
        with pytest.raises(NotAGitRepositoryError) as exc:
            WorkspaceValidator.find_git_root(tmp_non_git_dir)
        # Confirm the raised error is wrapped properly
        assert "Failed to find Git repository" in str(exc.value)


@given(random_path=st.from_type(Path))
def test_find_git_root_hypothesis_fuzz(random_path: Path) -> None:
    """
    Property-based test: If random_path has no .git folder, find_git_root must raise.
    We mock out the directory existence checks to always fail for .git.
    """
    # If the path is empty or doesn't end in .git, we say it fails
    # If the path does end in .git, we 'pretend' it is found
    path_str = str(random_path)

    def is_dir_side_effect(p: Path) -> bool:
        """Return True only if p ends with .git"""
        return str(p).endswith(".git")

    with patch("pathlib.Path.is_dir", side_effect=is_dir_side_effect):
        if path_str.endswith(".git"):
            # We expect success
            result = WorkspaceValidator.find_git_root(random_path)
            assert isinstance(result, Path), "Should return a Path object if .git is found"
        else:
            # We expect an error
            with pytest.raises(NotAGitRepositoryError):
                WorkspaceValidator.find_git_root(random_path)


# -----------------------------------------------------------------------------
#                           TEST: validate_workspace
# -----------------------------------------------------------------------------
def test_validate_workspace_success(tmp_git_dir: Path) -> None:
    """
    Confirm validate_workspace succeeds for a valid, accessible Git repo.
    """
    # Make sure directory is accessible
    os.chmod(tmp_git_dir, 0o700)
    # Should not raise any exceptions
    WorkspaceValidator.validate_workspace(tmp_git_dir)


def test_validate_workspace_dir_not_found(tmp_path: Path) -> None:
    """
    Confirm validate_workspace raises FileNotFoundError if path doesn't exist.
    """
    non_existent = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        WorkspaceValidator.validate_workspace(non_existent)


def test_validate_workspace_dir_not_accessible(tmp_git_dir: Path) -> None:
    """
    Confirm validate_workspace raises PermissionError if directory is inaccessible.
    """
    os.chmod(tmp_git_dir, 0o000)  # Remove all permissions
    with pytest.raises(PermissionError):
        WorkspaceValidator.validate_workspace(tmp_git_dir)


def test_validate_workspace_no_git_dir(tmp_non_git_dir: Path) -> None:
    """
    Confirm validate_workspace raises NotAGitRepositoryError if no .git folder is found.
    """
    with pytest.raises(NotAGitRepositoryError):
        WorkspaceValidator.validate_workspace(tmp_non_git_dir)


def test_validate_workspace_bare_repo(tmp_git_dir: Path) -> None:
    """
    Confirm validate_workspace raises NotAGitRepositoryError if the repo is bare.
    """
    with patch("branch_fixer.utils.workspace.Repo") as mock_repo:
        mock_repo.return_value.bare = True
        with pytest.raises(NotAGitRepositoryError) as exc:
            WorkspaceValidator.validate_workspace(tmp_git_dir)
        assert "Repository is bare" in str(exc.value), "Expected bare repository error"


def test_validate_workspace_invalid_repo(tmp_git_dir: Path) -> None:
    """
    Confirm validate_workspace raises NotAGitRepositoryError if Repo() fails with InvalidGitRepositoryError.
    """
    with patch("branch_fixer.utils.workspace.Repo", side_effect=InvalidGitRepositoryError("Corrupted repo")):
        with pytest.raises(NotAGitRepositoryError) as exc:
            WorkspaceValidator.validate_workspace(tmp_git_dir)
        assert "Corrupted repo" in str(exc.value), "Error message should include cause of failure"


def test_validate_workspace_unknown_error(tmp_git_dir: Path) -> None:
    """
    Confirm validate_workspace re-raises NotAGitRepositoryError when an unexpected exception occurs.
    """
    with patch("branch_fixer.utils.workspace.Repo", side_effect=Exception("Something else")):
        with pytest.raises(NotAGitRepositoryError) as exc:
            WorkspaceValidator.validate_workspace(tmp_git_dir)
        assert "Failed to validate Git repository" in str(exc.value)


def test_validate_then_check_dependencies_round_trip(tmp_git_dir: Path) -> None:
    """
    Demonstrates a 'round-trip': validate the workspace, then check dependencies in sequence.
    If both succeed, no exceptions are raised.
    """
    # 1) Validate the accessible Git workspace
    WorkspaceValidator.validate_workspace(tmp_git_dir)

    # 2) Check dependencies (mock out success)
    with patch("importlib.import_module", return_value=True):
        WorkspaceValidator.check_dependencies()

    # If no exception, test passes
    assert True, "Round-trip succeeded without errors"


# -----------------------------------------------------------------------------
#                           TEST: check_dependencies
# -----------------------------------------------------------------------------
def test_check_dependencies_success() -> None:
    """
    Confirm check_dependencies succeeds if all required dependencies can be imported.
    """
    with patch("importlib.import_module", return_value=True):
        # Should not raise any exception
        WorkspaceValidator.check_dependencies()


@pytest.mark.parametrize(
    "missing_packages",
    [
        ["pytest"],
        ["pytest", "click"],
        ["pytest", "click", "git", "snoop"],  # multiple missing packages
    ]
)
def test_check_dependencies_missing(missing_packages: list[str]) -> None:
    """
    Confirm check_dependencies raises ImportError for any missing dependencies.
    """
    def mock_import(name: str):
        if name in missing_packages:
            raise ImportError(f"No module named '{name}'")

    with patch("importlib.import_module", side_effect=mock_import):
        with pytest.raises(ImportError) as exc:
            WorkspaceValidator.check_dependencies()
        for pkg in missing_packages:
            assert pkg in str(exc.value), f"Missing package '{pkg}' not mentioned in ImportError"
