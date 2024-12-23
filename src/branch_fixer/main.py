# branch_fixer/main.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.run_cli import cli
import snoop
import logging

snoop.install(python=snoop({"output": lambda msg: logging.getLogger('snoop').info(msg)}))

def main():
    """Main entry point for the application"""
    setup_logging()
    return cli()  # Call the click CLI group instead of run_cli

if __name__ == "__main__":
    sys.exit(main())
