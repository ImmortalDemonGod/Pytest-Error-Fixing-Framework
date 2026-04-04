# branch_fixer/config/logging_config.py
import logging
from pathlib import Path


def setup_logging():
    """
    Configure application logging to console and a file.
    
    Creates a "logs" directory under the current working directory and uses "logs/app.log" as the log file. Configures the root logger at INFO level with a timestamped formatter and both a console (stream) handler and a file handler that writes to that file, replacing any existing handlers. Also obtains the logger named "snoop", sets it to INFO level, and attaches a file handler using the same log file and formatter.
    """
    # Ensure logs directory exists
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "app.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Console handler
            logging.FileHandler(
                str(log_file)
            ),  # File handler with explicit string path
        ],
        force=True,  # Replace existing handlers — basicConfig is a no-op otherwise
    )

    # Create a dedicated logger for snoop
    snoop_logger = logging.getLogger("snoop")
    snoop_logger.setLevel(logging.INFO)

    # Create a handler for snoop
    snoop_handler = logging.FileHandler(str(log_file))
    snoop_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Add the handler to the snoop logger
    snoop_logger.addHandler(snoop_handler)
