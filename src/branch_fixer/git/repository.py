# src/branch_fixer/git/repository.py
import subprocess
from pathlib import Path
from typing import List, Optional
from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from branch_fixer.git.exceptions import GitError, NotAGitRepositoryError

class GitRepository:
    """
    Represents a Git repository and provides methods to interact with it.

    **Note:** This class currently contains stub implementations for its methods.
    Each method raises a `NotImplementedError` and needs to be fully implemented
    to interact with an actual Git repository.
    """
    
    def __init__(self, root: Optional[Path] = None):
        """
        Initialize the GitRepository instance by locating the Git root and determining the main branch.

        Args:
            root (Optional[Path]): The path to the repository root. If None, the current working directory is used.

        Raises:
            NotAGitRepositoryError: If the specified directory is not a Git repository.
            GitError: If an error occurs while determining the main branch.
        """
        self.root = self._find_git_root(root)
        self.repo = Repo(self.root)  # Add this line to store the Repo instance
        self.main_branch = self._get_main_branch()

    def _find_git_root(self, root: Optional[Path]) -> Path:
        """
        Locate the Git root directory starting from the given root path.

        Args:
            root: The starting path to search for the Git root. If None, uses current directory.

        Returns:
            Path to the Git root directory

        Raises:
            NotAGitRepositoryError: If no Git repository found from starting path upwards
        """
        try:
            # Handle None input - default to current directory
            if root is None:
                root = Path.cwd()

            # Convert to Path if needed
            root = Path(root)

            # Let GitPython find the repository root
            # search_parent_directories=True makes it search up directory tree
            repo = Repo(root, search_parent_directories=True)

            # Return the repository working directory (root)
            # This will be the directory containing .git/
            return Path(repo.working_dir)

        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise NotAGitRepositoryError(f"No git repository found at or above {root}") from e

    def _get_main_branch(self) -> str:
        """
        Determine the main branch name of the repository (e.g., 'main' or 'master').

        Returns:
            str: The name of the main branch.

        Raises:
            GitError: If unable to determine the main branch.
        """
        try:
            # Read HEAD file content
            head_file = self.root / ".git" / "HEAD"
            head_content = head_file.read_text().strip()
            
            # Check for ref format (e.g. "ref: refs/heads/main")
            if head_content.startswith("ref: refs/heads/"):
                # Extract branch name after refs/heads/
                return head_content.replace("ref: refs/heads/", "").strip()
                
            # Invalid format
            raise GitError("Invalid HEAD file format")
                
        except (OSError, IOError) as e:
            raise GitError(f"Unable to read HEAD file: {e}")

    def run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """
        Execute a Git command within the repository and return the result.

        Args:
            cmd (List[str]): The Git command and its arguments to execute.

        Returns:
            subprocess.CompletedProcess: The result of the executed command.

        Raises:
            GitError: If the command execution fails.
        """
        try:
            # Ensure cmd is not empty
            if not cmd:
                raise ValueError("Git command list cannot be empty.")

            # First element should be 'git', remove it if present
            if cmd[0].lower() == 'git':
                cmd = cmd[1:]
            
            # Execute the command using GitPython
            exit_code, stdout, stderr = self.repo.git.execute(cmd, with_extended_output=True)
            
            # Create CompletedProcess object to match subprocess interface
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=exit_code,
                stdout=stdout,
                stderr=stderr
            )
            
        except GitCommandError as e:
            raise GitError(f"Git command failed: {e.stderr}") from e
        except ValueError as ve:
            raise GitError(str(ve)) from ve

    def clone(self, url: str, destination: Optional[Path] = None) -> bool:
        """
        Clone a Git repository from the specified URL to the destination path.

        Args:
            url (str): The URL of the repository to clone.
            destination (Optional[Path]): The directory where the repository should be cloned. 
                                          If None, clones into a new directory in the current path.

        Returns:
            bool: True if the clone was successful, False otherwise.

        Raises:
            GitError: If the clone operation fails.
        """
        raise NotImplementedError("clone method is not implemented yet.")

    def commit(self, message: str) -> bool:
        """
        Commit staged changes with the provided commit message.

        Args:
            message (str): The commit message.

        Returns:
            bool: True if the commit was successful, False otherwise.

        Raises:
            GitError: If the commit operation fails.
        """
        raise NotImplementedError("commit method is not implemented yet.")

    def push(self, branch: Optional[str] = None) -> bool:
        """
        Push commits to the remote repository.

        Args:
            branch (Optional[str]): The branch to push. If None, pushes the current branch.

        Returns:
            bool: True if the push was successful, False otherwise.

        Raises:
            GitError: If the push operation fails.
        """
        raise NotImplementedError("push method is not implemented yet.")

    def pull(self, branch: Optional[str] = None) -> bool:
        """
        Pull commits from the remote repository.

        Args:
            branch (Optional[str]): The branch to pull. If None, pulls the current branch.

        Returns:
            bool: True if the pull was successful, False otherwise.

        Raises:
            GitError: If the pull operation fails.
        """
        raise NotImplementedError("pull method is not implemented yet.")

    def has_version_control(self) -> bool:
        """
        Check if the repository has version control initialized.

        Returns:
            bool: True if the repository is under Git version control, False otherwise.
        """
        return hasattr(self, 'repo') and self.repo is not None

    def is_clean(self) -> bool:
        """
        Determine if the working directory is clean (no uncommitted changes).

        Returns:
            bool: True if the working directory is clean, False otherwise.

        Raises:
            GitError: If unable to determine the repository state.
        """
        try:
            return not self.repo.is_dirty(untracked_files=True)
        except Exception as e:
            raise GitError(f"Unable to determine repository state: {str(e)}") from e

    def get_current_branch(self) -> str:
        """
        Retrieve the name of the currently checked-out branch.

        Returns:
            str: The name of the current branch.

        Raises:
            GitError: If unable to determine the current branch.
        """
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached HEAD state
            return None
        except GitCommandError as e:
            raise GitError(f"Unable to determine current branch: {str(e)}") from e

    def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a branch with the specified name exists in the repository.

        Args:
            branch_name (str): The name of the branch to check.

        Returns:
            bool: True if the branch exists, False otherwise.

        Raises:
            GitError: If unable to determine branch existence.
        """
        try:
            return any(branch.name == branch_name for branch in self.repo.heads)
        except Exception as e:
            raise GitError(f"Unable to check branch existence: {str(e)}") from e
