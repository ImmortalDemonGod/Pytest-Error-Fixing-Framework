# src/branch_fixer/services/pytest/error_processor.py
import snoop
from typing import List
from pathlib import Path
from branch_fixer.services.pytest.parsers.collection_parser import CollectionParser
from branch_fixer.services.pytest.parsers.failure_parser import FailureParser
from branch_fixer.services.pytest.error_info import ErrorInfo
from branch_fixer.core.models import TestError, ErrorDetails
import re 


def parse_pytest_errors(output: str) -> List[TestError]:
    """Parse pytest output and convert to TestError objects.
    
    Args:
        output: Raw pytest output string
        
    Returns:
        List of TestError objects for each failure
    """
    # Extract test results using regex
    failed_test_pattern = r'FAILED (.*?)::(.+?)\n((?:.*?\n)*?(?=FAILED|\Z))'
    matches = re.finditer(failed_test_pattern, output, re.MULTILINE)
    
    test_errors = []
    for match in matches:
        test_file, test_function = match.group(1), match.group(2)
        error_block = match.group(3)
        
        # Extract error type and message
        error_line_pattern = r'E\s+([\w\.]+Error):\s+(.+)'
        error_match = re.search(error_line_pattern, error_block)
        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)
            
            test_errors.append(TestError(
                test_file=Path(test_file.strip()),
                test_function=test_function.strip(),
                error_details=ErrorDetails(
                    error_type=error_type,
                    message=error_message,
                    stack_trace=error_block.strip() if error_block else None
                )
            ))

    return test_errors