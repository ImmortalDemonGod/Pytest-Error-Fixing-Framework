# src/branch_fixer/services/pytest/error_processor.py

from typing import List
from pathlib import Path
from branch_fixer.services.pytest.parsers.collection_parser import CollectionParser
from branch_fixer.services.pytest.parsers.failure_parser import FailureParser
from branch_fixer.services.pytest.error_info import ErrorInfo
from branch_fixer.core.models import TestError, ErrorDetails

def parse_pytest_errors(output: str) -> List[TestError]:
    """
    Parse all types of pytest errors from test output.
    
    Uses both collection and failure parsers to capture all error types:
    - Collection errors (import errors, module issues)
    - Test failures (assertion errors, exceptions)
    
    Args:
        output: String output from pytest execution
        
    Returns:
        List[TestError]: List of all errors found, converted to domain model format
    """
    # Initialize parsers
    collection_parser = CollectionParser()
    failure_parser = FailureParser()
    
    # Get all error infos
    error_infos: List[ErrorInfo] = []
    error_infos.extend(collection_parser.parse_collection_errors(output))
    error_infos.extend(failure_parser.parse_test_failures(output))
    
    # Convert to domain model TestErrors
    test_errors: List[TestError] = []
    
    for info in error_infos:
        test_errors.append(
            TestError(
                test_file=Path(info.test_file),
                test_function=info.function,
                error_details=ErrorDetails(
                    error_type=info.error_type,
                    message=info.error_details,
                    stack_trace=info.code_snippet if info.has_traceback else None
                )
            )
        )
    
    return test_errors