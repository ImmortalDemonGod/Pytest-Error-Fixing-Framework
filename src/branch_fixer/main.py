# branch_fixer/main.py
import sys
from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.cli import run_cli

def main():
    """Main entry point for the application"""
    setup_logging()
    return run_cli()

if __name__ == "__main__":
    sys.exit(main())