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
    """Parse pytest output and convert to TestError objects."""
    failed_test_pattern = r'FAILED (.*?)::(.+?)\n((?:.*?\n)*?(?=FAILED|\Z))'
    matches = re.finditer(failed_test_pattern, output, re.MULTILINE)
    
    test_errors = []
    for match in matches:
        # Capture raw groups
        raw_test_file = match.group(1)
        raw_test_func = match.group(2)
        error_block   = match.group(3)

        # --- FIX: strip everything after `.py`
        if ".py " in raw_test_file:
            raw_test_file = raw_test_file.split(".py", 1)[0] + ".py"

        # Clean up whitespace
        raw_test_file = raw_test_file.strip()
        raw_test_func = raw_test_func.strip()

        # Extract error details from the error block
        error_line_pattern = r'E\s+([\w\.]+Error):\s+(.+)'
        error_match = re.search(error_line_pattern, error_block)
        
        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)

            # Construct TestError
            test_errors.append(
                TestError(
                    test_file=Path(raw_test_file),
                    test_function=raw_test_func,
                    error_details=ErrorDetails(
                        error_type=error_type,
                        message=error_message,
                        stack_trace=error_block.strip() if error_block else None
                    )
                )
            )

    return test_errors