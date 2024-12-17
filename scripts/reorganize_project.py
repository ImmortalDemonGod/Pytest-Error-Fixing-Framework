#!/usr/bin/env python3
"""
Script to reorganize the branch_fixer project structure.
Run from the src directory.
"""
import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Create new directory structure while preserving existing packages"""
    directories = [
        'branch_fixer/core',
        'branch_fixer/services/ai',
        'branch_fixer/services/code',
        'branch_fixer/services/git',
        'branch_fixer/services/pytest/parsers',
        'branch_fixer/orchestration',
        'branch_fixer/storage',
        'branch_fixer/utils',
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def move_files():
    """Move files to their new locations"""
    moves = [
        # Core domain
        ('branch_fixer/domain/models.py', 'branch_fixer/core/models.py'),
        ('branch_fixer/errors.py', 'branch_fixer/core/exceptions.py'),
        
        # AI Service
        ('branch_fixer/ai_manager.py', 'branch_fixer/services/ai/manager.py'),
        
        # Code Service
        ('branch_fixer/change_applier.py', 'branch_fixer/services/code/change_applier.py'),
        
        # Git Service
        ('branch_fixer/git/branch_manager.py', 'branch_fixer/services/git/branch_manager.py'),
        ('branch_fixer/git/exceptions.py', 'branch_fixer/services/git/exceptions.py'),
        ('branch_fixer/git/models.py', 'branch_fixer/services/git/models.py'),
        ('branch_fixer/git/pr_manager.py', 'branch_fixer/services/git/pr_manager.py'),
        ('branch_fixer/git/repository.py', 'branch_fixer/services/git/repository.py'),
        ('branch_fixer/git/safety_manager.py', 'branch_fixer/services/git/safety_manager.py'),
        
        # Pytest Service
        ('branch_fixer/pytest/config.py', 'branch_fixer/services/pytest/config.py'),
        ('branch_fixer/pytest/error_info.py', 'branch_fixer/services/pytest/error_info.py'),
        ('branch_fixer/pytest/exceptions.py', 'branch_fixer/services/pytest/exceptions.py'),
        ('branch_fixer/pytest/models.py', 'branch_fixer/services/pytest/models.py'),
        ('branch_fixer/pytest/runner.py', 'branch_fixer/services/pytest/runner.py'),
        ('branch_fixer/pytest/error_parser/collection_parser.py', 
         'branch_fixer/services/pytest/parsers/collection_parser.py'),
        ('branch_fixer/pytest/error_parser/failure_parser.py', 
         'branch_fixer/services/pytest/parsers/failure_parser.py'),
        
        # Orchestration
        ('branch_fixer/orchestrator.py', 'branch_fixer/orchestration/orchestrator.py'),
        ('branch_fixer/fix_service.py', 'branch_fixer/orchestration/fix_service.py'),
        ('branch_fixer/progress.py', 'branch_fixer/orchestration/progress.py'),
        ('branch_fixer/workflow/dispatcher.py', 'branch_fixer/orchestration/dispatcher.py'),
        ('branch_fixer/storage/coordination.py', 'branch_fixer/orchestration/coordinator.py'),
        
        # Storage
        ('branch_fixer/storage/recovery.py', 'branch_fixer/storage/recovery.py'),
        ('branch_fixer/storage/session_store.py', 'branch_fixer/storage/session_store.py'),
        ('branch_fixer/storage/state_manager.py', 'branch_fixer/storage/state_manager.py'),
        
        # Utils
        ('branch_fixer/workspace/validator.py', 'branch_fixer/utils/workspace.py'),
        ('branch_fixer/utils/cli.py', 'branch_fixer/utils/cli.py'),
        
        # Config (maintain at top level)
        ('branch_fixer/config/defaults.py', 'branch_fixer/config/defaults.py'),
        ('branch_fixer/config/logging_config.py', 'branch_fixer/config/logging_config.py'),
        ('branch_fixer/config/settings.py', 'branch_fixer/config/settings.py'),
        
        # Main entry point
        ('branch_fixer/main.py', 'branch_fixer/main.py'),
    ]
    
    for src, dst in moves:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if src_path.exists():
            print(f"Moving {src} to {dst}")
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_path), str(dst_path))  # Use copy2 first
            os.remove(str(src_path))  # Then remove original
        else:
            print(f"Warning: Source file not found: {src}")

def create_init_files():
    """Create __init__.py files"""
    init_paths = [
        'branch_fixer/core/__init__.py',
        'branch_fixer/services/__init__.py',
        'branch_fixer/services/ai/__init__.py',
        'branch_fixer/services/code/__init__.py',
        'branch_fixer/services/git/__init__.py',
        'branch_fixer/services/pytest/__init__.py',
        'branch_fixer/services/pytest/parsers/__init__.py',
        'branch_fixer/orchestration/__init__.py',
        'branch_fixer/storage/__init__.py',
        'branch_fixer/utils/__init__.py',
    ]
    
    for init_path in init_paths:
        Path(init_path).touch()

def cleanup_empty_dirs():
    """Remove empty directories after migration"""
    dirs_to_check = [
        'branch_fixer/domain',
        'branch_fixer/git',
        'branch_fixer/pytest/error_parser',
        'branch_fixer/pytest',
        'branch_fixer/workflow',
        'branch_fixer/workspace',
    ]
    
    for dir_path in dirs_to_check:
        path = Path(dir_path)
        if path.exists() and not any(path.iterdir()):
            shutil.rmtree(path)
            print(f"Removed empty directory: {dir_path}")

def main():
    """Execute reorganization"""
    print("Starting project reorganization...")
    
    # Backup first
    backup_dir = "branch_fixer_backup"
    print(f"Creating backup in {backup_dir}...")
    shutil.copytree("branch_fixer", backup_dir, dirs_exist_ok=True)
    
    try:
        # Create new structure
        print("Creating directory structure...")
        create_directory_structure()
        
        # Move files
        print("Moving files...")
        move_files()
        
        # Create __init__.py files
        print("Creating __init__.py files...")
        create_init_files()
        
        # Cleanup empty directories
        print("Cleaning up empty directories...")
        cleanup_empty_dirs()
        
        print("\nReorganization complete!")
        print("\nNext steps:")
        print("1. Update imports in all files")
        print("2. Run tests to verify everything works")
        print("3. If everything works, remove the backup with:")
        print(f"   rm -rf {backup_dir}")
        
    except Exception as e:
        print(f"\nError during reorganization: {e}")
        print("Restoring from backup...")
        shutil.rmtree("branch_fixer")
        shutil.copytree(backup_dir, "branch_fixer")
        print("Restored from backup.")
        raise

if __name__ == "__main__":
    main()