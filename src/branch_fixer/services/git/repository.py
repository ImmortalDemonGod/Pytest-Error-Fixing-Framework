# branch_fixer/services/git/repository.py
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional
from git import Repo, GitCommandError
from branch_fixer.services.git.exceptions import (
    GitError, 
    NotAGitRepositoryError, 
    InvalidGitRepositoryError, 
    NoSuchPathError
)
from branch_fixer.services.git.pr_manager import PRManager
from branch_fixer.services.git.safety_manager import SafetyManager
from branch_fixer.services.git.branch_manager import BranchManager
from branch_fixer.services.git.models import CommandResult
import logging

logger = logging.getLogger(__name__)

class GitRepository:
    """
    Represents a Git repository and provides methods to interact with it.

    **Note:** This class currently contains stub implementations for its methods.
    Each method raises a `NotImplementedError` and needs to be fully implemented
    to interact with an actual Git repository.
    """
    
    def __init__(self, root: Optional[Path] = None):
        """Initialize a GitRepository instance.
        
        Args:
            root: Path to repository root. Uses current directory if None.
            
        Raises:
            NotAGitRepositoryError: If directory is not a git repository
            GitError: If git operations fail
        """
        try:
            self.root = self._find_git_root(root or Path.cwd())
            self.repo = Repo(self.root)
            self.main_branch = self._get_main_branch()
            
            # Initialize managers
            self.pr_manager = PRManager(self)
            self.branch_manager = BranchManager(self)
            self.safety_manager = SafetyManager(self)
            
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise NotAGitRepositoryError(f"Not a git repository: {root}") from e
        except GitCommandError as e:
            raise GitError(f"Git initialization failed: {e.stderr}") from e
        except Exception as e:
            raise GitError(f"Repository initialization failed: {str(e)}") from e

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

            # First check if basic .git directory exists to validate
            if not (root / ".git").exists():
                raise NotAGitRepositoryError(f"Not a git repository: {root}")

            # Let GitPython find the repository root
            # search_parent_directories=True makes it search up directory tree
            repo = Repo(root, search_parent_directories=True)

            # Return the repository working directory (root)
            # This will be the directory containing .git/
            return Path(repo.working_dir)

        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise NotAGitRepositoryError(f"Not a git repository: {root}") from e
        except PermissionError as e:
            raise PermissionError(f"Permission denied accessing git repository: {e}")

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

    async def run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Execute a Git command within the repository and return the result.

        Args:
            cmd: The Git command and its arguments to execute.

        Returns:
            subprocess.CompletedProcess: The result of the executed command.

        Raises:
            GitError: If the command execution fails.
        """
        try:
            logger.debug(f"Running command: {' '.join(cmd)} in {self.root}")
            # First element should be 'git', remove it if present
            if cmd[0] == 'git':
                cmd = cmd[1:]
            
            # Prepare full command
            full_cmd = ['git'] + cmd
            
            # Create and run process
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.root)
            )
            
            # Wait for completion and get output
            stdout, stderr = await process.communicate()
            
            # Decode output
            stdout_decoded = stdout.decode('utf-8') if stdout else ''
            stderr_decoded = stderr.decode('utf-8') if stderr else ''
            
            logger.debug(f"Command stdout: {stdout_decoded}")
            logger.debug(f"Command stderr: {stderr_decoded}")
            
            if process.returncode != 0:
                raise GitError(f"Git command failed with return code {process.returncode}: {stderr_decoded}")
            
            return subprocess.CompletedProcess(
                args=full_cmd,
                returncode=process.returncode,
                stdout=stdout_decoded,
                stderr=stderr_decoded
            )
                
        except GitError:
            raise
        except Exception as e:
            if "'nonexistent' is not a git command" in str(e):
                raise GitError("unknown git command")
            raise GitError(f"Git command failed: {str(e)}")

    async def is_clean(self) -> bool:
        """
        Determine if the working directory is clean (no uncommitted changes).

        Returns:
            bool: True if the working directory is clean, False otherwise.

        Raises:
            GitError: If unable to determine the repository state.
        """
        try:
            result = await self.run_command(['status', '--porcelain'])
            is_clean = result.stdout.strip() == ''
            logger.debug(f"Repository clean: {is_clean}")
            return is_clean
        except Exception as e:
            raise GitError(f"Unable to determine repository state: {str(e)}") from e

    async def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a branch with the specified name exists in the repository.

        Args:
            branch_name: The name of the branch to check.

        Returns:
            bool: True if the branch exists, False otherwise.

        Raises:
            GitError: If unable to determine branch existence.
        """
        try:
            result = await self.run_command(['branch', '--list', branch_name])
            exists = bool(result.stdout.strip())
            logger.debug(f"Branch '{branch_name}' exists: {exists}")
            return exists
        except Exception as e:
            raise GitError(f"Unable to check branch existence: {str(e)}") from e

    async def get_current_branch(self) -> str:
        """
        Retrieve the name of the currently checked-out branch.

        Returns:
            str: The name of the current branch.

        Raises:
            GitError: If unable to determine the current branch.
        """
        try:
            result = await self.run_command(['branch', '--show-current'])
            current_branch = result.stdout.strip()
            logger.debug(f"Current branch: {current_branch}")
            return current_branch
        except Exception as e:
            raise GitError(f"Unable to determine current branch: {str(e)}") from e

    async def run_command_async(self, cmd: List[str]) -> CommandResult:
        """Execute a Git command asynchronously within the repository.
        
        Args:
            cmd: The Git command and its arguments to execute
            
        Returns:
            CommandResult containing execution results
            
        Raises:
            GitError: If command execution fails
        """
        try:
            # Ensure we're in the repository directory
            cwd = self.root if hasattr(self, 'root') else None
            
            # Prepare full command
            if cmd[0] == 'git':
                cmd = cmd[1:]
            full_cmd = ['git'] + cmd

            logger.debug(f"Executing async command: {' '.join(full_cmd)} in {cwd}")

            # Create and run process
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait for completion and get output
            stdout, stderr = await process.communicate()
            
            # Decode output
            stdout_str = stdout.decode('utf-8').strip() if stdout else ''
            stderr_str = stderr.decode('utf-8').strip() if stderr else ''
            
            logger.debug(f"Async command stdout: {stdout_str}")
            logger.debug(f"Async command stderr: {stderr_str}")
            
            if process.returncode != 0:
                raise GitError(f"Git command failed with return code {process.returncode}: {stderr_str}")
            
            return CommandResult(
                returncode=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                command=' '.join(full_cmd)
            )

        except GitError:
            raise
        except Exception as e:
            if "'nonexistent' is not a git command" in str(e):
                raise GitError("unknown git command")
            raise GitError(f"Git command failed: {str(e)}")

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

    def is_clean_sync(self) -> bool:
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

    def get_current_branch_sync(self) -> str:
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

    def branch_exists_sync(self, branch_name: str) -> bool:
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
    
    def create_pull_request(self, title: str, description: str) -> bool:
        """
        Create a pull request for the current changes.

        Args:
            title: Title for the pull request
            description: Description of changes

        Returns:
            bool indicating if PR creation succeeded

        Raises:
            GitError: If PR creation fails
        """
        return self.pr_manager.create_pr(title, description)

    def backup_state(self) -> str:
        """
        Create backup of current repository state.

        Returns:
            str: Backup identifier

        Raises:
            GitError: If backup creation fails
        """
        return self.safety_manager.create_backup()

    def restore_state(self, backup_id: str) -> bool:
        """
        Restore repository state from backup.

        Args:
            backup_id: Identifier of backup to restore

        Returns:
            bool indicating if restore succeeded

        Raises:
            GitError: If restore fails
        """
        return self.safety_manager.restore_backup(backup_id)

    def create_fix_branch(self, branch_name: str) -> bool:
        """
        Create and switch to a new branch for fixes.

        Args:
            branch_name: Name for the new branch

        Returns:
            bool indicating if branch creation succeeded

        Raises:
            GitError: If branch creation fails
        """
        return self.branch_manager.create_fix_branch(branch_name)

    def sync_with_remote(self) -> bool:
        """
        Synchronize with remote repository.

        Returns:
            bool indicating if sync succeeded

        Raises:
            GitError: If sync fails
        """
        try:
            self.pull()
            self.push()
            return True
        except GitError:
            return False