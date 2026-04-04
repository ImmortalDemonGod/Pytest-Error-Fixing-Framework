# branch_fixer/services/pytest/error_info.py
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ErrorInfo:
    test_file: str
    function: str
    error_type: str
    error_details: str
    line_number: str = "0"
    code_snippet: str = ""

    @property
    def file_path(self) -> Path:
        """Returns Path object for test file"""
        return Path(self.test_file)

    @property
    def formatted_error(self) -> str:
        """Returns formatted error message"""
        return f"{self.error_type}: {self.error_details}"

    @property
    def has_traceback(self) -> bool:
        """Checks if error has traceback"""
        return bool(self.code_snippet)

    def update_snippet(self, new_snippet: str) -> None:
        """
        Replace the stored code snippet with the provided string.
        
        Parameters:
            new_snippet (str): The new code snippet to store; replaces any existing snippet without validation.
        """
        self.code_snippet = new_snippet
