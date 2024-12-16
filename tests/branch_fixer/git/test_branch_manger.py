import pytest
from unittest.mock import MagicMock, patch
from branch_fixer.git.branch_manager import BranchManager, BranchStatus
from branch_fixer.git.exceptions import NotAGitRepositoryError, BranchCreationError, MergeConflictError

# Assuming that the exceptions are defined in git/exceptions.py
# If not, adjust the import accordingly or define them as needed.

@pytest.fixture
def mock_repo():
    """
    Fixture to provide a mocked GitRepository instance.
    Mocks all necessary methods used by BranchManager.
    """
    repo = MagicMock()
    # Setup default return values for repository methods
    repo.get_current_branch.return_value = "main"
    repo.has_uncommitted_changes.return_value = False
    repo.get_uncommitted_changes.return_value = []
    repo.create_branch.return_value = True
    repo.checkout_branch.return_value = True
    repo.merge_branch.return_value = True
    repo.branch_exists.return_value = True
    return repo

@pytest.fixture
def branch_manager(mock_repo):
    """
    Fixture to initialize BranchManager with a mocked GitRepository.
    """
    return BranchManager(repo=mock_repo)

class TestBranchManager:
    """Test suite for the BranchManager class."""

    def test_get_status_no_changes(self, branch_manager, mock_repo):
        """
        Test get_status method when there are no uncommitted changes.
        """
        # Arrange
        mock_repo.get_current_branch.return_value = "main"
        mock_repo.has_uncommitted_changes.return_value = False
        mock_repo.get_uncommitted_changes.return_value = []

        # Act
        status = branch_manager.get_status()

        # Assert
        assert isinstance(status, BranchStatus)
        assert status.current_branch == "main"
        assert not status.has_changes
        assert status.changes == []
        mock_repo.get_current_branch.assert_called_once()
        mock_repo.has_uncommitted_changes.assert_called_once()
        mock_repo.get_uncommitted_changes.assert_called_once()

    def test_get_status_with_changes(self, branch_manager, mock_repo):
        """
        Test get_status method when there are uncommitted changes.
        """
        # Arrange
        mock_repo.get_current_branch.return_value = "develop"
        mock_repo.has_uncommitted_changes.return_value = True
        mock_repo.get_uncommitted_changes.return_value = ["file1.py", "file2.py"]

        # Act
        status = branch_manager.get_status()

        # Assert
        assert isinstance(status, BranchStatus)
        assert status.current_branch == "develop"
        assert status.has_changes is True
        assert status.changes == ["file1.py", "file2.py"]
        mock_repo.get_current_branch.assert_called_once()
        mock_repo.has_uncommitted_changes.assert_called_once()
        mock_repo.get_uncommitted_changes.assert_called_once()

    def test_get_status_repository_inaccessible(self, branch_manager, mock_repo):
        """
        Test get_status method when the repository is inaccessible.
        """
        # Arrange
        mock_repo.get_current_branch.side_effect = NotAGitRepositoryError("Repository not found")

        # Act & Assert
        with pytest.raises(NotAGitRepositoryError, match="Repository not found"):
            branch_manager.get_status()
        mock_repo.get_current_branch.assert_called_once()

    def test_create_fix_branch_success(self, branch_manager, mock_repo):
        """
        Test create_fix_branch method for successful branch creation and checkout.
        """
        # Arrange
        branch_name = "fix/bug-123"
        mock_repo.create_branch.return_value = True
        mock_repo.checkout_branch.return_value = True

        # Act
        result = branch_manager.create_fix_branch(branch_name)

        # Assert
        assert result is True
        mock_repo.create_branch.assert_called_once_with(branch_name)
        mock_repo.checkout_branch.assert_called_once_with(branch_name)

    def test_create_fix_branch_failure(self, branch_manager, mock_repo):
        """
        Test create_fix_branch method when branch creation fails.
        """
        # Arrange
        branch_name = "fix/bug-123"
        mock_repo.create_branch.return_value = False

        # Act
        result = branch_manager.create_fix_branch(branch_name)

        # Assert
        assert result is False
        mock_repo.create_branch.assert_called_once_with(branch_name)
        mock_repo.checkout_branch.assert_not_called()

    def test_create_fix_branch_invalid_name(self, branch_manager, mock_repo):
        """
        Test create_fix_branch method with an invalid branch name.
        """
        # Arrange
        branch_name = "invalid/branch name!"
        mock_repo.create_branch.side_effect = BranchCreationError("Invalid branch name")

        # Act & Assert
        with pytest.raises(BranchCreationError, match="Invalid branch name"):
            branch_manager.create_fix_branch(branch_name)
        mock_repo.create_branch.assert_called_once_with(branch_name)
        mock_repo.checkout_branch.assert_not_called()

    def test_merge_branch_fast_forward_success(self, branch_manager, mock_repo):
        """
        Test merge_branch method for a successful fast-forward merge.
        """
        # Arrange
        branch_name = "feature/new-feature"
        mock_repo.merge_branch.return_value = True

        # Act
        result = branch_manager.merge_branch(branch_name, no_ff=False)

        # Assert
        assert result is True
        mock_repo.merge_branch.assert_called_once_with(branch_name, fast_forward=True)

    def test_merge_branch_no_fast_forward_success(self, branch_manager, mock_repo):
        """
        Test merge_branch method for a successful no-fast-forward merge.
        """
        # Arrange
        branch_name = "feature/new-feature"
        mock_repo.merge_branch.return_value = True

        # Act
        result = branch_manager.merge_branch(branch_name, no_ff=True)

        # Assert
        assert result is True
        mock_repo.merge_branch.assert_called_once_with(branch_name, fast_forward=False)

    def test_merge_branch_nonexistent_branch(self, branch_manager, mock_repo):
        """
        Test merge_branch method when attempting to merge a nonexistent branch.
        """
        # Arrange
        branch_name = "nonexistent-branch"
        mock_repo.merge_branch.side_effect = BranchCreationError("Branch does not exist")

        # Act & Assert
        with pytest.raises(BranchCreationError, match="Branch does not exist"):
            branch_manager.merge_branch(branch_name)
        mock_repo.merge_branch.assert_called_once_with(branch_name, fast_forward=False)

    def test_merge_branch_merge_conflict(self, branch_manager, mock_repo):
        """
        Test merge_branch method when a merge conflict occurs.
        """
        # Arrange
        branch_name = "feature/conflict-feature"
        mock_repo.merge_branch.side_effect = MergeConflictError("Merge conflict detected")

        # Act & Assert
        with pytest.raises(MergeConflictError, match="Merge conflict detected"):
            branch_manager.merge_branch(branch_name, no_ff=True)
        mock_repo.merge_branch.assert_called_once_with(branch_name, fast_forward=False)

    def test_merge_branch_invalid_parameters(self, branch_manager, mock_repo):
        """
        Test merge_branch method with invalid parameters.
        """
        # Arrange
        branch_name = ""
        mock_repo.merge_branch.side_effect = ValueError("Branch name cannot be empty")

        # Act & Assert
        with pytest.raises(ValueError, match="Branch name cannot be empty"):
            branch_manager.merge_branch(branch_name)
        mock_repo.merge_branch.assert_called_once_with(branch_name, fast_forward=False)

    def test_create_fix_branch_already_exists(self, branch_manager, mock_repo):
        """
        Test create_fix_branch method when the branch already exists.
        """
        # Arrange
        branch_name = "fix/bug-123"
        mock_repo.create_branch.side_effect = BranchCreationError("Branch already exists")

        # Act & Assert
        with pytest.raises(BranchCreationError, match="Branch already exists"):
            branch_manager.create_fix_branch(branch_name)
        mock_repo.create_branch.assert_called_once_with(branch_name)
        mock_repo.checkout_branch.assert_not_called()

    def test_get_status_with_unexpected_changes(self, branch_manager, mock_repo):
        """
        Test get_status method with unexpected change types.
        """
        # Arrange
        mock_repo.get_current_branch.return_value = "develop"
        mock_repo.has_uncommitted_changes.return_value = True
        mock_repo.get_uncommitted_changes.return_value = ["binaryfile.bin", "script.sh", "README.md"]

        # Act
        status = branch_manager.get_status()

        # Assert
        assert isinstance(status, BranchStatus)
        assert status.current_branch == "develop"
        assert status.has_changes is True
        assert status.changes == ["binaryfile.bin", "script.sh", "README.md"]
        mock_repo.get_current_branch.assert_called_once()
        mock_repo.has_uncommitted_changes.assert_called_once()
        mock_repo.get_uncommitted_changes.assert_called_once()

    def test_create_fix_branch_with_special_characters(self, branch_manager, mock_repo):
        """
        Test create_fix_branch method with a branch name containing special characters.
        """
        # Arrange
        branch_name = "fix/bug-#123"
        mock_repo.create_branch.return_value = True
        mock_repo.checkout_branch.return_value = True

        # Act
        result = branch_manager.create_fix_branch(branch_name)

        # Assert
        assert result is True
        mock_repo.create_branch.assert_called_once_with(branch_name)
        mock_repo.checkout_branch.assert_called_once_with(branch_name)

    def test_merge_branch_with_large_number_of_changes(self, branch_manager, mock_repo):
        """
        Test merge_branch method when merging branches with a large number of changes.
        """
        # Arrange
        branch_name = "feature/large-changes"
        mock_repo.merge_branch.return_value = True
        mock_repo.get_uncommitted_changes.return_value = [f"file_{i}.py" for i in range(100)]

        # Act
        result = branch_manager.merge_branch(branch_name, no_ff=False)

        # Assert
        assert result is True
        mock_repo.merge_branch.assert_called_once_with(branch_name, fast_forward=True)
