# branch_fixer/services/pytest/exceptions.py
from typing import Optional
from pathlib import Path

class PytestError(Exception):
    """Base exception for pytest operations"""
    def __init__(self, message: str, test_file: Optional[Path] = None):
        self.test_file = test_file
        super().__init__(message)

class PytestConfigError(PytestError):
    """Configuration validation errors"""
    pass

class PytestExecutionError(PytestError):
    """Test execution failures"""
    def __init__(self, 
                 message: str, 
                 test_file: Optional[Path] = None,
                 exit_code: Optional[int] = None,
                 stderr: Optional[str] = None):
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(message, test_file)

class PytestTimeoutError(PytestExecutionError):
    """Test execution timeout"""
    def __init__(self, 
                 message: str, 
                 test_file: Optional[Path] = None,
                 timeout: int = 0):
        self.timeout = timeout
        super().__init__(message, test_file)