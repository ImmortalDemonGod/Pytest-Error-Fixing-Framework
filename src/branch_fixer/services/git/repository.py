# branch_fixer/services/git/repository.py
import asyncio
import subprocess
from pathlib import Path
from git import Repo, GitCommandError
from typing import List, Optional
from branch_fixer.services.git.exceptions import (
    GitError, 
    NotAGitRepositoryError, 
    InvalidGitRepositoryError, 
    NoSuchPathError
)
from branch_fixer.services.git.pr_manager import PRManager
from branch_fixer.services.git.safety_manager import SafetyManager
from branch_fixer.services.git.branch_manager import BranchManager
from branch_fixer.services.git.models import CommandResult, TestError
import logging

logger = logging.getLogger(__name__)

class GitRepository:
    """
    Represents a Git repository and provides methods to interact with it.

    This class manages asynchronous Git command executions and repository state checks.
    It wraps Git operations in async calls, providing a consistent interface for checking
    branch existence, current branch, repository cleanliness, and more.

    **Note:** Some methods remain unimplemented (`NotImplementedError`) and serve as
    placeholders for operations like cloning, committing, pushing, and pulling, which 
    would need to be implemented depending on the specific use case.

    The class uses `CommandResult` objects to standardize command outputs and errors,
    and leverages GitPython's `Repo` class for local repository state. 
    """
    
    def __init__(self, root: Optional[Path] = None):
        """Initialize a GitRepository instance.
        
        Args:
            root: Path to repository root. Uses current directory if None.
            
        Raises:
            NotAGitRepositoryError: If the specified directory is not a git repository.
            GitError: If other git operations fail (e.g., unable to initialize the repo).
        """
        try:
            self.root = self._find_git_root(root or Path.cwd())
            self.repo = Repo(self.root)
            self.main_branch = self._get_main_branch()
            
            # Initialize managers for PRs, branches, and safety (backup/restore)
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
            Path: The path to the Git root directory.

        Raises:
            NotAGitRepositoryError: If no Git repository is found from the starting path upwards.
            PermissionError: If there's a permission issue accessing the repository directory.
        """
        try:
            if root is None:
                root = Path.cwd()

            root = Path(root)

            # Check if .git directory exists to validate it's a repository
            if not (root / ".git").exists():
                raise NotAGitRepositoryError(f"Not a git repository: {root}")

            # Let GitPython locate the repository root with parent directory search
            repo = Repo(root, search_parent_directories=True)
            return Path(repo.working_dir)

        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise NotAGitRepositoryError(f"Not a git repository: {root}") from e
        except PermissionError as e:
            raise PermissionError(f"Permission denied accessing git repository: {e}")

    def _get_main_branch(self) -> str:
        """
        Determine the main branch name of the repository (e.g., 'main' or 'master').

        Reads the HEAD file to identify the currently checked-out branch, which typically
        corresponds to the main branch after clone or initial setup. This method can help
        to identify the repository’s primary integration branch.

        Returns:
            str: The name of the main branch.

        Raises:
            GitError: If unable to determine the main branch (e.g., HEAD file is invalid).
        """
        try:
            head_file = self.root / ".git" / "HEAD"
            head_content = head_file.read_text().strip()
            
            # Check for a standard ref format (e.g., "ref: refs/heads/main")
            if head_content.startswith("ref: refs/heads/"):
                return head_content.replace("ref: refs/heads/", "").strip()

            # If not in the standard format, it's invalid or detached
            raise GitError("Invalid HEAD file format")
                
        except (OSError, IOError) as e:
            raise GitError(f"Unable to read HEAD file: {e}")

    async def run_command(self, cmd: List[str]) -> CommandResult:
        """
        Execute a Git command asynchronously within the repository and return a `CommandResult`.

        This is the core helper method that runs a given Git command in the repository's 
        root directory. It captures stdout, stderr, and the return code, packaging them 
        into a `CommandResult` instance.

        Args:
            cmd (List[str]): The Git command and its arguments (e.g., ['status', '--porcelain']).

        Returns:
            CommandResult: An object containing the return code, stdout, stderr, and the command run.

        Raises:
            GitError: If the command execution fails or if the Git command is unknown.
        """        try:
            logger.debug(f"Running command: {' '.join(cmd)} in {self.root}")
            # First element should be 'git', remove it if present
            if cmd[0] == 'git':
                cmd = cmd[1:]
            
            # Prepare full command
            full_cmd = ['git'] + cmd
            
            # Create and run process
            try:
                process = await asyncio.create_subprocess_exec(
                    *full_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.root)
                )
                
                if process is None:
                    raise GitError(f"Failed to create subprocess for command: {' '.join(full_cmd)}")
                
                # Wait for completion and get output
                stdout, stderr = await process.communicate()
                
                if stdout is None:
                    stdout = b''
                if stderr is None:
                    stderr = b''
                    
                # Decode output
                stdout_decoded = stdout.decode('utf-8') if stdout else ''
                stderr_decoded = stderr.decode('utf-8') if stderr else ''
                
                # Create result object
                result = CommandResult(
                    returncode=process.returncode,
                    stdout=stdout_decoded,
                    stderr=stderr_decoded,
                    command=full_cmd
                )
                
                # Log result for debugging
                logger.debug(f"Command result: {result}")
                
                if result.returncode != 0:
                    raise GitError(f"Git command failed with return code {result.returncode}: {result.stderr}")
                    
                return result
                
            except asyncio.CancelledError:
                if process:
                    process.terminate()
                raise GitError("Git command was cancelled")
                
            except Exception as e:
                if process:
                    process.terminate()
                raise GitError(f"Git command execution failed: {str(e)}")
                
        except GitError:
            # Don't wrap GitError - let it propagate
            raise
        except Exception as e:
            if "'nonexistent' is not a git command" in str(e):
                raise GitError("unknown git command")
            raise GitError(f"Git command failed: {str(e)}")

    async def is_clean(self) -> bool:
        """
        Determine if the working directory is clean (no uncommitted changes).

        Uses `git status --porcelain` to check if there are staged or unstaged changes.
        An empty output indicates a clean working directory.

        Returns:
            bool: True if the working directory is clean, False otherwise.

        Raises:
            GitError: If unable to determine the repository state (e.g., if `git status` fails).
        """
        try:
            result = await self.run_command(['status', '--porcelain'])
            # If stdout is empty, repo is clean
            is_clean = not bool(result.stdout.strip())
            logger.debug(f"Repository clean: {is_clean}")
            return is_clean
        except Exception as e:
            raise GitError(f"Unable to determine repository state: {str(e)}") from e

    async def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a branch with the specified name exists in the repository.

        Uses `git branch --list <branch_name>` to check for existence.

        Args:
            branch_name (str): The name of the branch to check.

        Returns:
            bool: True if the branch exists, False otherwise.

        Raises:
            GitError: If unable to determine branch existence (e.g., command failure).
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
        Retrieve the name of the currently checked-out branch asynchronously.

        Uses `git branch --show-current` to determine which branch is currently active.

        Returns:
            str: The name of the current branch.

        Raises:
            GitError: If unable to determine the current branch (e.g., if in detached HEAD state 
                      without handling or command failure).
        """
        try:
            result = await self.run_command(['branch', '--show-current'])
            current_branch = result.stdout.strip()
            logger.debug(f"Current branch: {current_branch}")
            return current_branch
        except Exception as e:
            raise GitError(f"Unable to determine current branch: {str(e)}") from e

    def clone(self, url: str, destination: Optional[Path] = None) -> bool:
        """
        Clone a Git repository from the specified URL to the destination path.

        Currently not implemented (placeholder).

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

        Currently not implemented (placeholder).

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

        Currently not implemented (placeholder).

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

        Currently not implemented (placeholder).

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
        Determine if the working directory is clean (no uncommitted changes) synchronously.

        This uses GitPython's `repo.is_dirty()` to check if there are uncommitted changes.
        Useful if synchronous operation is desired for certain checks.

        Returns:
            bool: True if the working directory is clean, False otherwise.

        Raises:
            GitError: If unable to determine the repository state.
        """
        try:
            return not self.repo.is_dirty(untracked_files=True)
        except Exception as e:
            raise GitError(f"Unable to determine repository state: {str(e)}") from e

    def get_current_branch_sync(self) -> Optional[str]:
        """
        Retrieve the name of the currently checked-out branch synchronously.

        Uses GitPython to determine the active branch. If the HEAD is detached, returns None.

        Returns:
            str or None: The name of the current branch, or None if in detached HEAD state.

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
        Check if a branch with the specified name exists in the repository (synchronously).

        Uses GitPython to iterate over known heads.

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
        Create a pull request for the current changes (old synchronous method).

        This method is a placeholder for backward compatibility and is not used 
        since we now have an async method for PR creation. It remains unimplemented.

        Args:
            title (str): Title for the pull request
            description (str): Description of the changes

        Returns:
            bool: indicating if PR creation succeeded

        Raises:
            GitError: If PR creation fails
        """
        raise NotImplementedError("Old create_pull_request method is not used.")

    def backup_state(self) -> str:
        """
        Create a backup of the current repository state.

        Uses the SafetyManager to create a backup, which can be restored later.

        Returns:
            str: A backup identifier string.

        Raises:
            GitError: If backup creation fails.
        """
        return self.safety_manager.create_backup()

    def restore_state(self, backup_id: str) -> bool:
        """
        Restore repository state from a previously created backup.

        Args:
            backup_id (str): Identifier of the backup to restore.

        Returns:
            bool: True if the restore succeeded, False otherwise.

        Raises:
            GitError: If restore fails.
        """
        return self.safety_manager.restore_backup(backup_id)

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
            logger.debug(f"Creating fix branch: {branch_name}")
            
            # Validate branch name
            if not await self.validate_branch_name(branch_name):
                raise BranchNameError(f"Invalid branch name: {branch_name}")

            # Check if branch exists
            try:
                exists = await self.repository.branch_exists(branch_name)
                if exists:
                    raise BranchCreationError(f"Branch {branch_name} already exists")
            except GitError as e:
                # Preserve GitError but provide context
                raise GitError(f"Failed to check if branch exists: {str(e)}") from e
                    
            # Get base branch
            from_branch = from_branch or self.repository.main_branch

            # Create new branch from base
            try:
                result = await self.repository.run_command(
                    ['checkout', '-b', branch_name, from_branch]
                )
                
                if result.returncode != 0:
                    raise BranchCreationError(
                        f"Failed to create branch {branch_name}: {result.stderr}"
                    )

                logger.info(f"Successfully created branch: {branch_name}")
                return True

            except GitError as e:
                # Preserve GitError but provide context
                raise GitError(f"Failed to create branch {branch_name}: {str(e)}") from e

        except (BranchNameError, BranchCreationError, GitError):
            # Don't wrap these errors
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise GitError(f"Unexpected error creating branch {branch_name}: {str(e)}") from e

    async def cleanup_fix_branch(self, branch_name: str, force: bool = False) -> bool:
        """
        Clean up a fix branch asynchronously.

        Removes the specified fix branch if it exists, optionally forcing removal even if
        there are unmerged changes.

        Args:
            branch_name (str): Name of the fix branch to clean up.
            force (bool): Whether to force branch removal if it has unmerged changes.

        Returns:
            bool: True if cleanup succeeded, False otherwise.

        Raises:
            GitError: If cleanup fails.
        """
        try:
            return await self.branch_manager.cleanup_fix_branch(branch_name, force)
        except Exception as e:
            raise GitError(f"Failed to cleanup branch {branch_name}: {str(e)}")

    async def create_pull_request(self, branch_name: str, error: TestError) -> bool:
        """
        Create a pull request for a fix asynchronously.

        Generates a pull request title and description based on the given `TestError`,
        identifying which test function and what kind of error occurred. The PRManager
        is then used to create the PR with the specified branch and any relevant files.

        Args:
            branch_name (str): The fix branch to create a PR from.
            error (TestError): An error object containing details about the test failure 
                               that prompted the fix.

        Returns:
            bool: True if the PR creation succeeded, False otherwise.

        Raises:
            GitError: If PR creation fails for any reason.
        """
        try:
            title = f"Fix for {error.test_function}"
            description = f"Fixes {error.error_details.error_type} in {error.test_file}"
            return await self.pr_manager.create_pr(title, description, branch_name, [error.test_file])
        except Exception as e:
            raise GitError(f"Failed to create pull request: {str(e)}")

    def sync_with_remote(self) -> bool:
        """
        Synchronize the local repository state with the remote repository.

        Currently uses placeholders (`pull` and `push` methods), which are not implemented.
        This method, once pull and push are implemented, should:
        1. Pull latest changes from the remote repository.
        2. Push local changes to the remote repository.

        Returns:
            bool: True if sync succeeded, False otherwise.

        Raises:
            GitError: If synchronization fails (pull or push errors).
        """
        try:
            self.pull()
            self.push()
            return True
        except GitError:
            return False
