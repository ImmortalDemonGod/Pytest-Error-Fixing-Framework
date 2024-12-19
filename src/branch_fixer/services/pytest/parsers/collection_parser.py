# branch_fixer/services/pytest/parsers/collection_parser.py
import re
from branch_fixer.services.pytest.error_info import ErrorInfo

# Using the exact pattern from the original working code
COLLECTION_PATTERN = r"ERROR collecting (.*?)\n(?:.*?\n)*?.*?which is not the same as the test file we want to collect:\n\s+(.*?)\n"

class CollectionParser:
    """Parser for pytest collection errors"""

    def parse_collection_errors(self, output: str) -> list[ErrorInfo]:
        """Parse collection errors from pytest output"""
        errors = []
        matches = re.finditer(COLLECTION_PATTERN, output, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            error = self.extract_collection_match(match)
            if self.validate_collection_error(error):
                errors.append(error)
        
        return errors

    def extract_collection_match(self, match: re.Match) -> ErrorInfo:
        """Extract error details from regex match"""
        test_file = match.group(1).strip()
        conflicting_path = match.group(2).strip()
        
        return ErrorInfo(
            test_file=test_file,
            function="collection",
            error_type="CollectionError",
            error_details=f"Import path mismatch with {conflicting_path}"
        )

    def validate_collection_error(self, error: ErrorInfo) -> bool:
        """Validate that the error matches collection error criteria"""
        return (
            error.function == "collection" and 
            error.error_type == "CollectionError" and
            error.error_details.startswith("Import path mismatch")
        )