# branch_fixer/services/git/branch_manager.py
import re
from typing import Optional, Set

# Add the missing GitRepository import (adjust the path if needed)
from branch_fixer.services.git.repository import GitRepository

from branch_fixer.services.git.exceptions import (
    BranchCreationError,
    BranchNameError,
    GitError,
)
from branch_fixer.services.git.models import BranchMetadata, BranchStatus


class BranchManager:
    """
    Manages Git branch operations with safety checks and error handling.

    Handles branch creation, merging, and cleanup with proper
    validation and error recovery.
    """

    def __init__(self, repository: "GitRepository"):
        """
        Initialize with repository reference.

        Args:
            repository: GitRepository instance

        Raises:
            ValueError: If repository is invalid
        """
        self.repository = repository
        # Branch name validation patterns
        self.name_pattern = r"^[a-zA-Z0-9\-_\/]+$"
        self.forbidden_names: Set[str] = {"master", "main", "develop"}

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
            current_branch=current_branch, has_changes=not has_changes, changes=changes
        )

    def create_fix_branch(
        self, branch_name: str, from_branch: Optional[str] = None
    ) -> bool:
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
            # Validate that the branch name is valid and does not already exist
            self._check_valid_new_branch_name(branch_name)

            # Determine the base branch
            base_branch = from_branch or self.repository.main_branch

            # Create the new branch and checkout
            return self._create_and_checkout_branch(branch_name, base_branch)

        except Exception as e:
            # Convert to appropriate error type
            if isinstance(e, (BranchNameError, BranchCreationError)):
                raise e
            raise GitError(f"Failed to create branch {branch_name}: {str(e)}")

    def _check_valid_new_branch_name(self, branch_name: str) -> None:
        """
        Check that the new branch name is valid, non-empty, matches pattern,
        and does not already exist in the repository.

        Raises:
            BranchNameError: If branch name is invalid
            BranchCreationError: If branch already exists
        """
        if not self.validate_branch_name(branch_name):
            raise BranchNameError(f"Invalid branch name: {branch_name}")

        if self.repository.branch_exists(branch_name):
            raise BranchCreationError(f"Branch {branch_name} already exists")

    def _create_and_checkout_branch(self, branch_name: str, base_branch: str) -> bool:
        """
        Create a new branch from the specified base branch and switch to it.

        Raises:
            BranchCreationError: If Git command fails
        """
        result = self.repository.run_command(["checkout", "-b", branch_name, base_branch])
        if result.returncode != 0:
            raise BranchCreationError(
                f"Failed to create branch {branch_name}: {result.stderr}"
            )
        return True

    def cleanup_fix_branch(self, branch_name: str, force: bool = False) -> bool:
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
                self.repository.run_command(["checkout", self.repository.main_branch])

            # Delete the branch
            delete_args = ["branch", "-D" if force else "-d", branch_name]
            result = self.repository.run_command(delete_args)

            return result.returncode == 0

        except Exception as e:
            # Only raise if it's not just a "branch not found" error
            if "not found" not in str(e).lower():
                raise GitError(f"Failed to clean up branch {branch_name}: {str(e)}")
            return True

    def get_branch_metadata(self, branch_name: str) -> BranchMetadata:
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

    def validate_branch_name(self, branch_name: str) -> bool:
        """Validate branch name follows conventions.

        Args:
            branch_name: Name to validate

        Returns:
            True if valid

        Raises:
            BranchNameError: If name invalid
        """
        try:
            self._check_branch_name_not_empty(branch_name)
            self._check_branch_name_pattern(branch_name)
            self._check_forbidden_names(branch_name)
            return True
        except Exception as e:
            if isinstance(e, BranchNameError):
                raise e
            raise BranchNameError(f"Failed to validate branch name: {str(e)}") from e

    def _check_branch_name_not_empty(self, branch_name: str) -> None:
        if not branch_name:
            raise BranchNameError("Branch name cannot be empty")

    def _check_branch_name_pattern(self, branch_name: str) -> None:
        if not re.match(self.name_pattern, branch_name):
            raise BranchNameError(
                f"Branch name '{branch_name}' contains invalid characters"
            )

    def _check_forbidden_names(self, branch_name: str) -> None:
        if branch_name.lower() in self.forbidden_names:
            raise BranchNameError(
                f"Cannot use reserved name '{branch_name}' for branch"
            )

    def is_branch_merged(
        self, branch_name: str, target_branch: Optional[str] = None
    ) -> bool:
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
