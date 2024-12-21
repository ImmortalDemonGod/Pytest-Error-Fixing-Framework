# branch_fixer/main.py
import sys
from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.run_cli import cli
import snoop

snoop.install()

def main():
    """Main entry point for the application"""
    setup_logging()
    return cli()  # Call the click CLI group instead of run_cli

if __name__ == "__main__":
    sys.exit(main())