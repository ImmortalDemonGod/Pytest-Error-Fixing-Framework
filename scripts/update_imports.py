#!/usr/bin/env python3
"""
Script to update imports after project reorganization.
Run from the project root directory.
"""
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import shutil

logger = logging.getLogger(__name__)

# Old to new import mappings
IMPORT_MAPPINGS = {
    # Core imports
    'from domain.models': 'from branch_fixer.core.models',
    'from domain': 'from branch_fixer.core',
    'import domain.': 'import branch_fixer.core.',
    'from errors': 'from branch_fixer.core.exceptions',
    
    # Service imports
    'from ai_manager': 'from branch_fixer.services.ai.manager',
    'from change_applier': 'from branch_fixer.services.code.change_applier',
    
    # Git imports
    'from git.': 'from branch_fixer.services.git.',
    'import git.': 'import branch_fixer.services.git.',
    
    # Pytest imports
    'from pytest.': 'from branch_fixer.services.pytest.',
    'import pytest.': 'import branch_fixer.services.pytest.',
    'from pytest.error_parser.': 'from branch_fixer.services.pytest.parsers.',
    
    # Orchestration imports
    'from workflow.': 'from branch_fixer.orchestration.',
    'import workflow.': 'import branch_fixer.orchestration.',
    'from fix_service': 'from branch_fixer.orchestration.fix_service',
    'from orchestrator': 'from branch_fixer.orchestration.orchestrator',
    'from progress': 'from branch_fixer.orchestration.progress',
    
    # Storage imports
    'from storage.': 'from branch_fixer.storage.',
    'import storage.': 'import branch_fixer.storage.',
    
    # Utils imports
    'from workspace.': 'from branch_fixer.utils.',
    'import workspace.': 'import branch_fixer.utils.',
    'from utils.': 'from branch_fixer.utils.',
    
    # Config imports
    'from config.': 'from branch_fixer.config.',
    'import config.': 'import branch_fixer.config.',
}

class ImportUpdater:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.changes_made: Dict[Path, List[Tuple[str, str]]] = {}
    
    def update_file_imports(self, file_path: Path) -> List[Tuple[str, str]]:
        """Update imports in a single file"""
        try:
            content = file_path.read_text()
            original = content
            
            # Apply each import mapping
            for old, new in IMPORT_MAPPINGS.items():
                content = content.replace(old, new)
            
            # Record and apply changes if needed
            if content != original:
                file_path.write_text(content)
                changes = [(old, new) for old, new in IMPORT_MAPPINGS.items() 
                          if old in original]
                self.changes_made[file_path] = changes
                return changes
            
            return []
            
        except Exception as e:
            logger.error(f"Error updating {file_path}: {e}")
            return []
    
    def update_all_imports(self) -> Dict[Path, List[Tuple[str, str]]]:
        """Update imports in all Python files"""
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            if file_path.name != "update_imports.py":  # Skip this script
                self.update_file_imports(file_path)
        
        return self.changes_made
    
    def generate_report(self) -> str:
        """Generate a report of all changes made"""
        lines = ["Import Update Report", "===================\n"]
        
        if not self.changes_made:
            lines.append("No changes were required.")
            return "\n".join(lines)
        
        for file_path, changes in self.changes_made.items():
            rel_path = file_path.relative_to(self.project_root)
            lines.append(f"\nFile: {rel_path}")
            lines.append("-" * (len(str(rel_path)) + 6))
            for old, new in changes:
                lines.append(f"  {old} → {new}")
        
        return "\n".join(lines)

def get_project_paths():
    """Get project and backup paths"""
    # Look for src directory
    if Path('src/branch_fixer').exists():
        project_dir = Path('src/branch_fixer')
        backup_dir = Path('src/branch_fixer_import_backup')
    elif Path('branch_fixer').exists():
        project_dir = Path('branch_fixer')
        backup_dir = Path('branch_fixer_import_backup')
    else:
        raise FileNotFoundError("Project directory not found. Run from project root.")
        
    return project_dir, backup_dir

def main():
    """Run import updates"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    project_dir = None
    backup_dir = None
    
    try:
        # Find project paths
        project_dir, backup_dir = get_project_paths()
        
        # Create backup
        logger.info(f"Creating backup in {backup_dir}...")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(project_dir, backup_dir)
        
        # Update imports
        logger.info("Updating imports...")
        updater = ImportUpdater(project_dir)
        updater.update_all_imports()
        
        # Generate and save report
        report = updater.generate_report()
        report_file = Path("import_update_report.txt")
        report_file.write_text(report)
        
        logger.info(f"Import updates complete. Report saved to {report_file}")
        logger.info("Review the changes and run tests to verify everything works.")
        logger.info("To restore from backup if needed: ")
        logger.info(f"  rm -rf {project_dir} && mv {backup_dir} {project_dir}")
        
    except Exception as e:
        logger.error(f"Error during import updates: {e}")
        # Only attempt restore if we have both paths and backup exists
        if project_dir and backup_dir and backup_dir.exists():
            logger.info("Restoring from backup...")
            if project_dir.exists():
                shutil.rmtree(project_dir)
            shutil.copytree(backup_dir, project_dir)
            logger.info("Restored from backup.")
        raise

if __name__ == "__main__":
    main()