# tests/branch_fixer/git/test_branch_manager.py
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

from branch_fixer.git.branch_manager import BranchManager, BranchStatus
from branch_fixer.git.exceptions import GitError, BranchCreationError, MergeConflictError


class TestBranchStatus:
    """Test branch status reporting behavior"""
    
    def test_clean_status(self, branch_manager):
        """Should report clean state accurately"""
        # When getting status
        status = branch_manager.get_status()
        
        # Then should show clean state
        assert isinstance(status, BranchStatus)
        assert status.current_branch == "main"
        assert not status.has_changes
        assert len(status.changes) == 0

    def test_dirty_status(self, dirty_repo):
        """Should detect uncommitted changes"""
        # Given manager with dirty repo
        manager = BranchManager(dirty_repo)
        
        # When getting status
        status = manager.get_status()
        
        # Then should show changes
        assert status.current_branch == "feature"
        assert status.has_changes
        assert "modified: file1.py" in status.changes

class TestBranchCreation:
    """Test branch creation behavior"""

    def test_create_branch_clean_repo(self, branch_manager, clean_repo):
        """Should create branch in clean repo"""
        # Given clean repo state is valid
        clean_repo.branch_exists.return_value = False
        clean_repo.create_branch.return_value = True
        
        # When creating branch
        success = branch_manager.create_fix_branch("fix-123")
        
        # Then should:
        # 1. Check if branch exists first
        clean_repo.branch_exists.assert_called_once_with("fix-123")
        # 2. Check for uncommitted changes
        clean_repo.has_uncommitted_changes.assert_called_once()
        # 3. Create branch with exact name
        clean_repo.create_branch.assert_called_once_with("fix-123")
        # 4. Return success
        assert success is True

    def test_reject_creation_dirty_repo(self, dirty_repo):
        """Should reject branch creation with uncommitted changes"""
        # Given repo with changes
        manager = BranchManager(dirty_repo)
        
        # When attempting creation
        # Then should fail
        with pytest.raises(BranchCreationError) as exc:
            manager.create_fix_branch("fix-123")
        assert "uncommitted changes" in str(exc.value)


    @pytest.mark.parametrize("branch_name,error", [
        ("", "empty branch name"),
        ("invalid//name", "invalid branch name"), 
        ("fix-123", "branch already exists")
    ])
    def test_invalid_branch_creation(self, branch_manager, clean_repo, branch_name, error):
        """Should handle invalid branch creation scenarios"""
        # Given error condition
        clean_repo.create_branch.side_effect = BranchCreationError(error)
        
        # When/Then:
        # 1. Should raise appropriate error
        with pytest.raises(BranchCreationError) as exc:
            branch_manager.create_fix_branch(branch_name)
            
        # 2. Verify exact error message
        assert str(exc.value) == error
            
        # 3. Verify proper validation order
        if branch_name == "":
            # Should fail fast without checking repo
            clean_repo.branch_exists.assert_not_called()
        else:
            # Should check branch existence first
            clean_repo.branch_exists.assert_called_once_with(branch_name)

class TestBranchMerging:
    """Test branch merging behavior"""

    def test_successful_merge(self, branch_manager, clean_repo):
        """Should merge branches successfully"""
        # Given branches exist
        clean_repo.branch_exists.return_value = True
        clean_repo.merge_branch.return_value = True
        
        # When merging
        success = branch_manager.merge_branch("feature")
        
        # Then should succeed
        assert success is True
        clean_repo.merge_branch.assert_called_once_with("feature", fast_forward=True)

    def test_merge_with_conflicts(self, branch_manager, clean_repo):
        """Should handle merge conflicts appropriately"""
        # Given merge will conflict
        clean_repo.branch_exists.return_value = True
        clean_repo.merge_branch.side_effect = MergeConflictError("Conflict in file.py")
        
        # When/Then should raise conflict error
        with pytest.raises(MergeConflictError):
            branch_manager.merge_branch("feature")

    def test_merge_nonexistent_branch(self, branch_manager, clean_repo):
        """Should reject merging nonexistent branches"""
        # Given branch doesn't exist
        clean_repo.branch_exists.return_value = False
        
        # When/Then should fail 
        with pytest.raises(BranchCreationError):
            branch_manager.merge_branch("nonexistent")

    @pytest.mark.parametrize("ff_option", [True, False])
    def test_merge_fast_forward_option(self, branch_manager, clean_repo, ff_option):
        """Should respect fast-forward option"""
        # Given branch exists
        clean_repo.branch_exists.return_value = True
        clean_repo.merge_branch.return_value = True
        
        # When merging with ff option
        branch_manager.merge_branch("feature", fast_forward=ff_option)
        
        # Then should pass correct option
        clean_repo.merge_branch.assert_called_once_with("feature", fast_forward=ff_option)
