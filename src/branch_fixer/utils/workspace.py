# branch_fixer/utils/workspace.py
import os
from pathlib import Path
import importlib
import logging

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
    async def validate_workspace(path: Path) -> None:
        """Validate the workspace directory
        
        Args:
            path: Path to the workspace directory
            
        Raises:
            FileNotFoundError: If the directory does not exist
            PermissionError: If the directory is not accessible
        """
        if not path.exists():
            raise FileNotFoundError(f"Workspace directory {path} does not exist.")
        
        if not os.access(path, os.R_OK | os.W_OK):
            raise PermissionError(f"Workspace directory {path} is not accessible.")

        # Check if it's a git repository
        git_dir = path / ".git"
        if not git_dir.is_dir():
            logger.warning(f"Directory {path} is not a git repository. Some features may be limited.")
        else:
            logger.debug(f"Git repository found at {git_dir}")

        logger.debug(f"Workspace validation successful for {path}")

    @staticmethod
    async def check_dependencies() -> None:
        """Check for required dependencies
        
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