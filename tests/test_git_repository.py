import pytest
from unittest.mock import patch, MagicMock
from src.branch_fixer.git.repository import GitRepository

def test_clone_repository():
    with patch('src.branch_fixer.git.repository.subprocess.run') as mock_run:
        repo = GitRepository()
        repo.clone_repository('https://example.com/repo.git')
        mock_run.assert_called_once_with(['git', 'clone', 'https://example.com/repo.git'], check=True)

def test_clone_repository_failure():
    with patch('src.branch_fixer.git.repository.subprocess.run', side_effect=Exception("Clone failed")):
        repo = GitRepository()
        with pytest.raises(Exception, match="Clone failed"):
            repo.clone_repository('https://example.com/repo.git')

def test_checkout_branch():
    with patch('src.branch_fixer.git.repository.subprocess.run') as mock_run:
        repo = GitRepository()
        repo.checkout_branch('main')
        mock_run.assert_called_once_with(['git', 'checkout', 'main'], check=True)

def test_checkout_branch_failure():
    with patch('src.branch_fixer.git.repository.subprocess.run', side_effect=Exception("Checkout failed")):
        repo = GitRepository()
        with pytest.raises(Exception, match="Checkout failed"):
            repo.checkout_branch('main')
