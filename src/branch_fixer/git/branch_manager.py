# src/branch_fixer/git/branch_manager.py
from dataclasses import dataclass
from typing import List, Optional
from branch_fixer.git.exceptions import BranchCreationError, MergeConflictError, GitError

@dataclass
class BranchStatus:
    """Represents the current state of a Git branch."""
    current_branch: str          # Name of current branch
    has_changes: bool           # Whether there are uncommitted changes
    changes: List[str]          # List of paths with changes

class BranchManager:
    """Manages Git branch operations with safety checks and error handling."""
    
    def __init__(self, repository):
        """Initialize with a Git repository instance.
        
        Args:
            repository: GitRepository instance to perform operations on
        """
        self.repository = repository

    def get_status(self) -> BranchStatus:
        """Get current branch status including uncommitted changes.
        
        Returns:
            BranchStatus with current branch and change information
        
        Raises:
            GitError: If unable to get repository status
        """
        # Stub implementation to make tests fail for behavioral reasons
        return BranchStatus(
            current_branch=self.repository.get_current_branch(),
            # FIX: Query actual repository state
            has_changes=self.repository.has_uncommitted_changes(),
            changes=self.repository.get_uncommitted_changes()
        )

    def create_fix_branch(self, branch_name: str) -> bool:
        """Create a new branch for fixing an issue.
        
        Args:
            branch_name: Name of branch to create
            
        Returns:
            bool: True if branch created successfully
            
        Raises:
            BranchCreationError: If branch creation fails due to:
                - Empty branch name
                - Invalid branch name format
                - Branch already exists
                - Uncommitted changes present
        """
        # Stub implementation to make tests fail for behavioral reasons
        if self.repository.has_uncommitted_changes():
            raise BranchCreationError("cannot create branch with uncommitted changes")
            
        # FIX: Validate branch name before checking existence
        if not branch_name:
            raise BranchCreationError("empty branch name")
        if "//" in branch_name:
            raise BranchCreationError("invalid branch name")
            
        # Now check existence
        if self.repository.branch_exists(branch_name):
            raise BranchCreationError("branch already exists")
            
        return self.repository.create_branch(branch_name)
    
    def merge_branch(self, branch_name: str, fast_forward: bool = False) -> bool:
        """Merge specified branch into current branch.
        
        Args:
            branch_name: Name of branch to merge
            fast_forward: Whether to allow fast-forward merge
            
        Returns:
            bool: True if merge completed successfully
            
        Raises:
            BranchCreationError: If branch doesn't exist
            MergeConflictError: If merge has conflicts
            GitError: For other merge failures
        """
        # Stub implementation to make tests fail for behavioral reasons
        # FIX: Default fast_forward to True
        if not self.repository.branch_exists(branch_name):
            raise BranchCreationError("branch does not exist")
                
        try:
            return self.repository.merge_branch(branch_name, fast_forward=fast_forward)
        except GitError as e:
            if "conflict" in str(e).lower():
                raise MergeConflictError(str(e))
            raise

    def is_clean(self) -> bool:
        """Check if repository is in a clean state.
        
        Returns:
            bool: True if no uncommitted changes
        """
        return not self.repository.has_uncommitted_changes()

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists.
        
        Args:
            branch_name: Name of branch to check
            
        Returns:
            bool: True if branch exists
        """
        return self.repository.branch_exists(branch_name)

    def get_current_branch(self) -> str:
        """Get name of currently checked out branch.
        
        Returns:
            str: Name of current branch
            
        Raises:
            GitError: If unable to determine current branch
        """
        return self.repository.get_current_branch()
