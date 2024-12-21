# branch_fixer/config/logging_config.py
import logging
import os
from pathlib import Path

def setup_logging():
    """Setup logging configuration"""
    # Ensure logs directory exists
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "app.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console handler
            logging.FileHandler(str(log_file))  # File handler with explicit string path
        ]
    )