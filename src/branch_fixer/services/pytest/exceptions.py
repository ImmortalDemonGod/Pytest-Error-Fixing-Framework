# branch_fixer/services/pytest/exceptions.py
from typing import Optional
from pathlib import Path


class PytestError(Exception):
    """Base exception for pytest operations"""

    def __init__(self, message: str, test_file: Optional[Path] = None):
        """
        Create a PytestError with an error message and an optional originating test file.
        
        Parameters:
            message (str): Human-readable error message describing the pytest-related failure.
            test_file (Optional[Path]): Path to the test file associated with the error, or `None` if not applicable.
        """
        self.test_file = test_file
        super().__init__(message)


class PytestConfigError(PytestError):
    """Configuration validation errors"""

    pass


class PytestExecutionError(PytestError):
    """Test execution failures"""

    def __init__(
        self,
        message: str,
        test_file: Optional[Path] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
    ):
        """
        Initialize a PytestExecutionError with an error message, optional test file, and optional process output.
        
        Parameters:
            message (str): Human-readable error message describing the failure.
            test_file (Optional[Path]): Path to the test file associated with the error, if any.
            exit_code (Optional[int]): Process exit code produced by the pytest run, if available.
            stderr (Optional[str]): Captured standard error output from the pytest run, if available.
        
        Notes:
            The constructor stores `exit_code` and `stderr` on the instance and delegates message and `test_file` handling to the base exception.
        """
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(message, test_file)


class PytestTimeoutError(PytestExecutionError):
    """Test execution timeout"""

    def __init__(
        self, message: str, test_file: Optional[Path] = None, timeout: int = 0
    ):
        """
        Initialize a PytestTimeoutError with a message, optional associated test file, and a timeout.
        
        Parameters:
            message (str): Error message describing the timeout.
            test_file (Optional[Path]): Path to the test file associated with the error, if available.
            timeout (int): Timeout value in seconds that triggered the error.
        """
        self.timeout = timeout
        super().__init__(message, test_file)
