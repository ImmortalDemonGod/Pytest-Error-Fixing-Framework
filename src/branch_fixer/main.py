# src/branch_fixer/main.py
import sys
from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.cli import run_cli

if __name__ == "__main__":
    setup_logging()

if __name__ == "__main__":
    sys.exit(run_cli())
