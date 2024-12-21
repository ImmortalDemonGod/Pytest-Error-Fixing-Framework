# branch_fixer/services/code/change_applier.py
from pathlib import Path
from typing import Optional
import shutil
from logging import getLogger
import snoop
from datetime import datetime
from uuid import uuid4

logger = getLogger(__name__)

from branch_fixer.core.models import CodeChanges

class ChangeApplicationError(Exception):
    """Base exception for change application errors"""
    pass

class BackupError(ChangeApplicationError):
    """Raised when backup operations fail"""
    pass

class ChangeApplier:
    """
    Handles safe application of code changes with backup/restore.
    Now includes a method that returns the created backup path
    so we can revert on functional test failure.
    """

    BACKUP_DIRNAME = ".backups"

    @snoop
    def apply_changes_with_backup(self, test_file: Path, changes: CodeChanges) -> (bool, Path):
        """
        Apply code changes with backup. Returns (success, backup_path).
        
        - success: indicates if the changes were applied successfully (including syntax check).
        - backup_path: the newly created backup, or None if something failed early.

        We call an internal method for actual logic but store the backup_path to revert if needed.
        """
        backup_path = None
        try:
            # 1) Create backup
            backup_path = self._backup_file(test_file)
            if not backup_path:
                raise BackupError(f"Failed to create backup for {test_file}")
            
            # 2) Actually apply changes (like your old apply_changes logic)
            success = self._apply_changes_core(test_file, changes, backup_path)
            return success, backup_path

        except Exception as e:
            logger.error(f"Failed to apply changes with backup: {e}")
            return (False, backup_path)

    def restore_backup(self, file_path: Path, backup_path: Path) -> bool:
        """
        Public method to restore a file from a known backup path.
        """
        return self._restore_backup(file_path, backup_path)

    @snoop
    def _apply_changes_core(self, test_file: Path, changes: CodeChanges, backup_path: Path) -> bool:
        """
        Internal helper that:
          - writes changes
          - checks syntax
          - reverts if syntax fails
        """
        try:
            # Clean up code markers from AI response
            modified_code = changes.modified_code
            if modified_code.startswith('```python'):
                modified_code = modified_code[8:]  # Remove ```python
            if modified_code.endswith('```'):
                modified_code = modified_code[:-3]  # Remove ```
            modified_code = modified_code.strip()

            # Overwrite the file
            test_file.write_text(modified_code, encoding='utf-8')
            logger.debug(f"Wrote changes to {test_file}")

            # Syntax verification
            if not self._verify_changes(test_file):
                logger.warning(
                    f"Changes to {test_file} did not pass local syntax verification. Restoring backup..."
                )
                self._restore_backup(test_file, backup_path)
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to apply changes to {test_file}: {e}")
            # Attempt to revert because something else went wrong
            try:
                self._restore_backup(test_file, backup_path)
            except Exception as revert_err:
                logger.warning(f"Failed to revert after error: {revert_err}")
            return False
    
    def _backup_file(self, file_path: Path) -> Path:
        """Create backup copy of file.
        
        Args:
            file_path: Path to file to backup
            
        Returns:
            Path to the backup file, or raises an exception if anything fails.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Cannot backup non-existent file: {file_path}")

        backups_root = file_path.parent / self.BACKUP_DIRNAME
        backups_root.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid4())[:8]
        backup_name = f"{file_path.name}-{timestamp}-{short_uuid}.bak"
        backup_path = backups_root / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            raise BackupError(f"Failed to create backup for {file_path}: {e}") from e

    def _restore_backup(self, file_path: Path, backup_path: Path) -> bool:
        """
        Restore file from the specified backup.
        """
        if not backup_path.exists():
            raise BackupError(f"No backup found at {backup_path} to restore {file_path}")
        try:
            shutil.copy2(backup_path, file_path)
            logger.info(f"Restored {file_path} from backup {backup_path}")
            return True
        except Exception as e:
            raise BackupError(f"Failed to restore {file_path} from {backup_path}: {e}") from e

    def _verify_changes(self, file_path: Path) -> bool:
        """
        Verify file is valid after changes (simple Python syntax check).
        """
        try:
            updated_source = file_path.read_text(encoding='utf-8')
            compile(updated_source, file_path.name, 'exec')
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Verification error in {file_path}: {e}")
            return False