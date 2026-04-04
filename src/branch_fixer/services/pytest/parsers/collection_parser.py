# src/branch_fixer/services/pytest/parsers/collection_parser.py
import re
from branch_fixer.services.pytest.error_info import ErrorInfo

# Corrected regex that explicitly matches the multi-line structure with newlines.
COLLECTION_PATTERN = r"^ERROR collecting (.+?)$.*?^imported module .*?__file__ attribute:.*?^\s*(.+?)$.*?^which is not the same as the test file we want to collect:.*?^\s*(.+?)$"


class CollectionParser:
    """Parser for pytest collection errors"""

    def parse_collection_errors(self, output: str) -> list[ErrorInfo]:
        """
        Extract validated pytest "ERROR collecting ..." blocks from the combined pytest output.
        
        Parameters:
            output (str): The full pytest stdout/stderr text to scan for collection error blocks.
        
        Returns:
            list[ErrorInfo]: A list of validated ErrorInfo objects representing parsed collection errors; empty if none were found.
        """
        errors = []
        # Use re.MULTILINE for ^/$ to match start/end of lines, re.DOTALL for .*? to match newlines
        matches = re.finditer(COLLECTION_PATTERN, output, re.MULTILINE | re.DOTALL)

        for match in matches:
            error = self.extract_collection_match(match)
            if self.validate_collection_error(error):
                errors.append(error)

        return errors

    def extract_collection_match(self, match: re.Match) -> ErrorInfo:
        """
        Build an ErrorInfo from a regex match of a pytest "ERROR collecting ..." block.
        
        Parameters:
        	match (re.Match): A regex match where group 1 is the collected test file name (e.g., "test_example.py") and group 3 is the conflicting import path.
        
        Returns:
        	ErrorInfo: An object with `test_file` set from group 1, `function` set to "collection", `error_type` set to "CollectionError", and `error_details` set to "Import path mismatch with {conflicting_path}".
        """
        # Group 1: The file being collected, e.g., 'test_example.py'
        test_file = match.group(1).strip()

        # Group 3: The conflicting path
        conflicting_path = match.group(3).strip()

        return ErrorInfo(
            test_file=test_file,
            function="collection",
            error_type="CollectionError",
            error_details=f"Import path mismatch with {conflicting_path}",
        )

    def validate_collection_error(self, error: ErrorInfo) -> bool:
        """
        Check whether an ErrorInfo represents a pytest collection import path mismatch.
        
        Parameters:
            error (ErrorInfo): The parsed error object to validate.
        
        Returns:
            bool: `True` if `error.function` is "collection", `error.error_type` is "CollectionError", and `error.error_details` starts with "Import path mismatch"; `False` otherwise.
        """
        return (
            error.function == "collection"
            and error.error_type == "CollectionError"
            and error.error_details.startswith("Import path mismatch")
        )
