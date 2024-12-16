from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from src.branch_fixer.git.repository import GitRepository
import subprocess

@pytest.fixture
def mock_find_git_root_success():
    with patch.object(GitRepository, '_find_git_root', return_value=Path("/fake/repo")) as mock_method:
        yield mock_method

@pytest.fixture
def mock_find_git_root_failure():
    with patch.object(GitRepository, '_find_git_root', side_effect=FileNotFoundError("Git root not found")) as mock_method:
        yield mock_method

@pytest.fixture
def mock_get_main_branch_success():
    with patch.object(GitRepository, '_get_main_branch', return_value="main") as mock_method:
        yield mock_method

@pytest.fixture
def mock_get_main_branch_failure():
    with patch.object(GitRepository, '_get_main_branch', side_effect=ValueError("Branch not found")) as mock_method:
        yield mock_method

def test_git_repository_init_default(mock_find_git_root_success, mock_get_main_branch_success):
    repo = GitRepository()
    assert repo.root == Path("/fake/repo")
    assert repo.main_branch == "main"
    mock_find_git_root_success.assert_called_once_with(None)
    mock_get_main_branch_success.assert_called_once()

def test_git_repository_init_custom(mock_find_git_root_success, mock_get_main_branch_success):
    custom_root = Path("/custom/repo")
    repo = GitRepository(root=custom_root)
    assert repo.root == Path("/fake/repo")
    assert repo.main_branch == "main"
    mock_find_git_root_success.assert_called_once_with(custom_root)
    mock_get_main_branch_success.assert_called_once()

def test_git_repository_init_find_git_root_failure(mock_find_git_root_failure):
    with pytest.raises(FileNotFoundError, match="Git root not found"):
        GitRepository()
    mock_find_git_root_failure.assert_called_once_with(None)

def test_git_repository_init_get_main_branch_failure(mock_find_git_root_success, mock_get_main_branch_failure):
    with pytest.raises(ValueError, match="Branch not found"):
        GitRepository()
    mock_find_git_root_success.assert_called_once_with(None)
    mock_get_main_branch_failure.assert_called_once()

def test_run_command_success(mock_find_git_root_success, mock_get_main_branch_success):
    cmd = ["git", "status"]
    expected_result = MagicMock()
    expected_result.returncode = 0
    expected_result.stdout = "On branch main"
    expected_result.stderr = ""

    with patch("subprocess.run") as mock_subprocess_run:
        mock_completed_process = MagicMock()
        mock_completed_process.returncode = expected_result.returncode
        mock_completed_process.stdout = expected_result.stdout
        mock_completed_process.stderr = expected_result.stderr
        mock_subprocess_run.return_value = mock_completed_process
        repo = GitRepository()
        result = repo.run_command(cmd)
        assert result.returncode == 0
        assert result.stdout == "On branch main"
        assert result.stderr == ""
        mock_subprocess_run.assert_called_once_with(cmd, capture_output=True, text=True)

def test_run_command_failure(mock_find_git_root_success, mock_get_main_branch_success):
    cmd = ["git", "invalid-command"]
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, cmd, "Error: command not found", "")) as mock_subprocess_run:
        repo = GitRepository()
        with pytest.raises(subprocess.CalledProcessError, match="Error: command not found"):
            repo.run_command(cmd)
        mock_subprocess_run.assert_called_once_with(cmd, capture_output=True, text=True)

def test_run_command_empty_command(mock_find_git_root_success, mock_get_main_branch_success):
    cmd = []
    expected_result = MagicMock()
    expected_result.returncode = 0
    expected_result.stdout = ""
    expected_result.stderr = ""

    with patch("subprocess.run") as mock_subprocess_run:
        mock_completed_process = MagicMock()
        mock_completed_process.returncode = expected_result.returncode
        mock_completed_process.stdout = expected_result.stdout
        mock_completed_process.stderr = expected_result.stderr
        mock_subprocess_run.return_value = mock_completed_process
        repo = GitRepository()
        result = repo.run_command(cmd)
        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""
        mock_subprocess_run.assert_called_once_with(cmd, capture_output=True, text=True)

def test_run_command_unusual_output(mock_find_git_root_success, mock_get_main_branch_success):
    cmd = ["git", "log", "--oneline"]
    expected_result = MagicMock()
    expected_result.returncode = 0
    expected_result.stdout = "commit1\ncommit2\ncommit3"
    expected_result.stderr = ""

    with patch("subprocess.run") as mock_subprocess_run:
        mock_completed_process = MagicMock()
        mock_completed_process.returncode = expected_result.returncode
        mock_completed_process.stdout = expected_result.stdout
        mock_completed_process.stderr = expected_result.stderr
        mock_subprocess_run.return_value = mock_completed_process

        repo = GitRepository()
        result = repo.run_command(cmd)
        assert result.returncode == expected_result.returncode
        assert result.stdout == expected_result.stdout
        assert result.stderr == expected_result.stderr
        mock_subprocess_run.assert_called_once_with(cmd, capture_output=True, text=True)

def test_init_custom_root_no_git(mock_find_git_root_failure):
    custom_root = Path("/no/git/repo")
    with pytest.raises(FileNotFoundError, match="Git root not found"):
        GitRepository(root=custom_root)
    mock_find_git_root_failure.assert_called_once_with(custom_root)

def test_run_command_unusual_output():
    cmd = ["git", "log", "--oneline"]
    expected_result = MagicMock()
    expected_result.returncode = 0
    expected_result.stdout = "commit1\ncommit2\ncommit3"
    expected_result.stderr = ""

    with patch.object(GitRepository, 'run_command', return_value=expected_result) as mock_run_command:
        repo = GitRepository()
        result = repo.run_command(cmd)
        assert result.returncode == 0
        assert result.stdout == "commit1\ncommit2\ncommit3"
        assert result.stderr == ""
        mock_run_command.assert_called_once_with(cmd)
