# branch_fixer/main.py
import logging
import os
import sys

from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.run_cli import cli


def main():
    """Main entry point for the application"""
    setup_logging()
    if os.environ.get("BRANCH_FIXER_DEBUG"):
        import snoop
        snoop.install(out=lambda msg: logging.getLogger("snoop").info(msg))
    return cli()


if __name__ == "__main__":
    sys.exit(main())