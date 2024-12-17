# branch_fixer/services/pytest/config.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict

@dataclass
class PytestConfig:
    """Configuration for pytest execution.
    
    Attributes:
        working_dir: Directory to run tests from
        pytest_args: Additional pytest command line arguments
        timeout: Test execution timeout in seconds
        capture_output: Whether to capture test output
        parallel: Whether to run tests in parallel
        max_retries: Number of retry attempts on failure
        env_vars: Additional environment variables
    """
    working_dir: Optional[Path] = None
    pytest_args: Optional[List[str]] = None
    timeout: int = 30
    capture_output: bool = True
    parallel: bool = True
    max_retries: int = 1
    env_vars: Optional[Dict[str, str]] = None