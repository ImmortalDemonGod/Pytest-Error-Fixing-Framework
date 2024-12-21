# branch_fixer/services/code/change_applier.py
from pathlib import Path
from typing import Optional
import shutil
from logging import getLogger
import snoop

logger = getLogger(__name__)

from branch_fixer.core.models import CodeChanges

class ChangeApplicationError(Exception):
    """Base exception for change application errors"""
    pass

class BackupError(ChangeApplicationError):
    """Raised when backup operations fail"""
    pass

class ChangeApplier:
    """Handles safe application of code changes with backup/restore"""

    @snoop
    def apply_changes(self, test_file: Path, changes: CodeChanges) -> bool:
        """Apply code changes to file with automatic backup.
        
        Args:
            test_file: Path to test file to modify
            changes: CodeChanges containing modifications
            
        Returns:
            bool indicating success
            
        Raises:
            BackupError: If backup fails
            ChangeApplicationError: If changes cannot be applied
            FileNotFoundError: If test file doesn't exist
        """
        try:
            # Create backup
            backup_path = self._backup_file(test_file)
            if not backup_path:
                raise BackupError(f"Failed to create backup for {test_file}")
            
            # Clean up code markers from AI response
            modified_code = changes.modified_code
            if modified_code.startswith('```python'):
                modified_code = modified_code[8:]  # Remove ```python
            if modified_code.endswith('```'):
                modified_code = modified_code[:-3]  # Remove ```
            modified_code = modified_code.strip()
            
            # Write changes 
            test_file.write_text(modified_code)
            logger.debug(f"Wrote changes to {test_file}")

            # Verify changes are valid
            if not self._verify_changes(test_file):
                self._restore_backup(test_file)
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to apply changes: {str(e)}")
            return False
    
    def _backup_file(self, file_path: Path) -> Path:
        """Create backup copy of file.
        
        Args:
            file_path: Path to file to backup
            
        Returns:
            Path to backup file
            
        Raises:
            BackupError: If backup creation fails
            FileNotFoundError: If source file missing
        """
        raise NotImplementedError()
    
    def _restore_backup(self, file_path: Path) -> bool:
        """Restore file from backup.
        
        Args:
            file_path: Path to file to restore
            
        Returns:
            bool indicating success
            
        Raises:
            BackupError: If restore fails
            FileNotFoundError: If backup missing
        """
        raise NotImplementedError()
    
    def _verify_changes(self, file_path: Path) -> bool:
        """Verify file is valid after changes.
        
        Args:
            file_path: Path to modified file
            
        Returns:
            bool indicating if changes are valid
        """
        raise NotImplementedError()
