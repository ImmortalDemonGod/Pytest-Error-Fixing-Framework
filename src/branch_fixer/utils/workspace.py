# branch_fixer/utils/workspace.py
import os
from pathlib import Path
import importlib
import logging
from git import Repo, InvalidGitRepositoryError
from branch_fixer.services.git.exceptions import NotAGitRepositoryError

logger = logging.getLogger(__name__)

class WorkspaceValidator:
    """Validates the workspace and checks dependencies"""

    REQUIRED_DEPENDENCIES = [
        'click',
        'pytest',
        'aiohttp',
        'git',      # python-git
        'snoop'     # For debugging
    ]

    @staticmethod
    def find_git_root(path: Path) -> Path:
        """
        Find the root Git repository by walking up the directory tree.
        
        Args:
            path: Starting path to search from
            
        Returns:
            Path to Git root directory
            
        Raises:
            NotAGitRepositoryError: If no Git repository found
        """
        current = path.absolute()
        while current != current.parent:
            if (current / ".git").is_dir():
                logger.debug(f"Found Git repository root at {current}")
                return current
            current = current.parent
        
        raise NotAGitRepositoryError(f"No Git repository found for {path}")

    @staticmethod
    def validate_workspace(path: Path) -> None:
        """
        Validate the workspace directory and locate Git repository.
        
        Args:
            path: Path to the workspace directory
            
        Raises:
            FileNotFoundError: If the directory does not exist
            PermissionError: If the directory is not accessible
            NotAGitRepositoryError: If no valid Git repository found
        """
        if not path.exists():
            raise FileNotFoundError(f"Workspace directory {path} does not exist.")
        
        if not os.access(path, os.R_OK | os.W_OK):
            raise PermissionError(f"Workspace directory {path} is not accessible.")

        repo = None
        try:
            # Find and validate Git repository
            git_root = WorkspaceValidator.find_git_root(path)
            repo = Repo(git_root)

            # Additional Git repository validations
            if repo.bare:
                raise NotAGitRepositoryError("Repository is bare")

            logger.debug(f"Git repository validation successful at {git_root}")
            logger.debug(f"Workspace validation successful for {path}")

        except InvalidGitRepositoryError as e:
            logger.error(f"Invalid Git repository: {e}")
            raise NotAGitRepositoryError(f"Invalid Git repository at {path}: {str(e)}") from e
        except Exception as e:
            # Catch any other exceptions during Repo interaction and wrap them
            logger.error(f"An unexpected error occurred during Git validation: {e}")
            raise NotAGitRepositoryError(f"Git validation failed at {path}: {str(e)}") from e
        finally:
            if repo:
                repo.git.clear_cache()
                repo.close()

    @staticmethod
    def check_dependencies() -> None:
        """
        Check for required dependencies.
        
        Raises:
            ImportError: If a required dependency is missing
        """
        missing_deps = []

        for dep in WorkspaceValidator.REQUIRED_DEPENDENCIES:
            try:
                importlib.import_module(dep)
                logger.debug(f"Found required dependency: {dep}")
            except ImportError:
                missing_deps.append(dep)
                logger.error(f"Missing required dependency: {dep}")

        if missing_deps:
            error_message = (
                "Required dependencies are missing. Please install the following packages:\n" +
                "\n".join(f"  - {dep}" for dep in missing_deps) +
                "\nYou can install them using: pip install " + " ".join(missing_deps)
            )
            raise ImportError(error_message)

        logger.debug("All required dependencies are installed")