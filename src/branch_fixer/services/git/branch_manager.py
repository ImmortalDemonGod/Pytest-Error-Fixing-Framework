# branch_fixer/services/git/branch_manager.py
from dataclasses import dataclass
from typing import List
from typing import List, Optional, Set, TYPE_CHECKING
from pathlib import Path
from branch_fixer.services.git.exceptions import (
    BranchCreationError, 
    MergeConflictError, 
    GitError
)

@dataclass
class BranchStatus:
    """
    Represents the status of a Git branch.
    
    Attributes:
        current_branch (str): The name of the current branch.
        has_changes (bool): Indicates if there are uncommitted changes.
        changes (List[str]): List of changed files.
    """
    current_branch: str
    has_changes: bool
    changes: List[str]

@dataclass
class BranchMetadata:
    """
    Metadata about a Git branch.
    
    Attributes:
        name: Branch name
        current: Whether this is the current branch
        upstream: Remote tracking branch if any
        last_commit: SHA of last commit
        modified_files: Files with uncommitted changes
    """
    name: str
    current: bool 
    upstream: Optional[str]
    last_commit: str
    modified_files: List[Path]

class BranchNameError(GitError):
    """Raised when branch name is invalid."""
    pass

if TYPE_CHECKING:
    from branch_fixer.services.git.repository import GitRepository

class BranchManager:
    """
    Manages Git branch operations with safety checks and error handling.
    
    Handles branch creation, merging, and cleanup with proper
    validation and error recovery.
    """
    
    def __init__(self, repository: 'GitRepository'):
        """
        Initialize with repository reference.

        Args:
            repository: GitRepository instance

        Raises:
            ValueError: If repository is invalid
        """
        self.repository = repository
        # Branch name validation patterns
        self.name_pattern = r'^[a-zA-Z0-9\-_\/]+$'
        self.forbidden_names: Set[str] = {'master', 'main', 'develop'}
    
    def get_status(self) -> BranchStatus:
        """
        Retrieve the current status of the Git repository.
    
        Returns:
            BranchStatus: The current branch status.
        """
        current_branch = self.repository.get_current_branch()
        has_changes = self.repository.is_clean()
        changes = [item.a_path for item in self.repository.repo.index.diff(None)]
        return BranchStatus(
            current_branch=current_branch,
            has_changes=not has_changes,
            changes=changes
        )

    async def create_fix_branch(self, 
                            branch_name: str,
                            from_branch: Optional[str] = None) -> bool:
        """Create and switch to a fix branch.

        Args:
            branch_name: Name for new branch
            from_branch: Optional base branch

        Returns:
            True if created successfully

        Raises:
            BranchNameError: If name is invalid
            BranchCreationError: If creation fails
            GitError: For other Git errors
        """
        try:
            # Validate branch name
            if not await self.validate_branch_name(branch_name):
                raise BranchNameError(f"Invalid branch name: {branch_name}")

            # Check if branch exists
            if self.repository.branch_exists(branch_name):
                raise BranchCreationError(f"Branch {branch_name} already exists")
                
            # Get base branch
            from_branch = from_branch or self.repository.main_branch

            # Create new branch from base
            result = await self.repository.run_command(
                ['checkout', '-b', branch_name, from_branch]
            )
            
            if result.returncode != 0:
                raise BranchCreationError(
                    f"Failed to create branch {branch_name}: {result.stderr}"
                )

            return True

        except Exception as e:
            # Convert to appropriate error type
            if isinstance(e, (BranchNameError, BranchCreationError)):
                raise e
            raise GitError(f"Failed to create branch {branch_name}: {str(e)}")
        
    async def cleanup_fix_branch(self,
                            branch_name: str,
                            force: bool = False) -> bool:
        """Clean up a fix branch after merging.

        Args:
            branch_name: Branch to clean up
            force: Whether to force deletion

        Returns:
            True if cleaned up successfully

        Raises:
            GitError: If cleanup fails with unexpected error
        """
        try:
            # Check if branch exists
            if not self.repository.branch_exists(branch_name):
                # Branch doesn't exist - consider cleanup successful
                return True

            # Switch back to main branch if needed
            current_branch = self.repository.get_current_branch()
            if current_branch == branch_name:
                await self.repository.run_command(['checkout', self.repository.main_branch])

            # Delete the branch
            delete_args = ['branch', '-D' if force else '-d', branch_name]
            result = await self.repository.run_command(delete_args)
            
            return result.returncode == 0

        except Exception as e:
            # Only raise if it's not just a "branch not found" error
            if "not found" not in str(e).lower():
                raise GitError(f"Failed to clean up branch {branch_name}: {str(e)}")
            return True

    async def get_branch_metadata(self, branch_name: str) -> BranchMetadata:
        """
        Get detailed metadata about a branch.

        Args:
            branch_name: Branch to check

        Returns:
            BranchMetadata for the branch

        Raises:
            GitError: If status check fails
        """
        raise NotImplementedError()

    async def validate_branch_name(self, branch_name: str) -> bool:
        """
        Validate branch name follows conventions.

        Args:
            branch_name: Name to validate

        Returns:
            True if valid

        Raises:
            BranchNameError: If name invalid
        """
        raise NotImplementedError()

    async def is_branch_merged(self, 
                             branch_name: str,
                             target_branch: Optional[str] = None) -> bool:
        """
        Check if a branch is fully merged.

        Args:
            branch_name: Branch to check
            target_branch: Branch to check against

        Returns:
            True if branch is merged

        Raises:
            GitError: If check fails
        """
        raise NotImplementedError()
