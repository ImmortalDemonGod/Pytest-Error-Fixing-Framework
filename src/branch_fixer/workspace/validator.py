import os
from pathlib import Path

class WorkspaceValidator:
    """Validates the workspace and checks dependencies"""

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

    @staticmethod
    async def check_dependencies() -> None:
        """Check for required dependencies
        
        Raises:
            ImportError: If a required dependency is missing
        """
        try:
            import some_required_module
        except ImportError as e:
            raise ImportError("Required dependency is missing.") from e
