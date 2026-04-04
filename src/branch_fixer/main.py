# branch_fixer/main.py
import logging
import os
import sys

from branch_fixer.config.logging_config import setup_logging
from branch_fixer.utils.run_cli import cli


def main():
    """
    Initialize application logging, optionally enable debug tracing, and invoke the command-line interface.
    
    If the environment variable BRANCH_FIXER_DEBUG (case-insensitive) is set to "1", "true", or "yes", enable snoop tracing routed to the "snoop" logger.
    
    Returns:
        int: Process exit code returned by the command-line interface.
    """
    setup_logging()
    if os.environ.get("BRANCH_FIXER_DEBUG", "").lower() in ("1", "true", "yes"):
        import snoop

        snoop.install(out=lambda msg: logging.getLogger("snoop").info(msg))
    return cli()


if __name__ == "__main__":
    sys.exit(main())
