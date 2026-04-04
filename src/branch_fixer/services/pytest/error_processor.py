# src/branch_fixer/services/pytest/error_processor.py
from typing import List
from pathlib import Path
import re
from branch_fixer.core.models import TestError, ErrorDetails
from branch_fixer.services.pytest.models import SessionResult


def _extract_error_type(error_message: str | None) -> str:
    """
    Derives a normalized error type string from a pytest error message.
    
    Parameters:
        error_message (str | None): The raw pytest error message to inspect. If `None` or empty, it is treated as unknown.
    
    Returns:
        str: The leading error type extracted (e.g. "ValueError", "AssertionError", "Failure"), or "UnknownError" if no recognizable type is found.
    """
    if not error_message:
        return "UnknownError"

    error_match = re.match(r"^(\w+(?:Error|Exception|Failure))", error_message.strip())
    return error_match.group(1) if error_match else "UnknownError"


def process_pytest_results(result: SessionResult) -> List[TestError]:
    """
    Convert a pytest SessionResult into a list of TestError domain objects.
    
    Includes both per-test failures (from result.test_results) and collection errors (from result.collection_errors).
    
    Parameters:
        result (SessionResult): The pytest session result containing per-test results and collection error strings.
    
    Returns:
        List[TestError]: A list of TestError objects representing each test failure and collection error.
    """
    test_errors: List[TestError] = []

    # Process standard test failures
    for test_result in result.test_results.values():
        if test_result.failed:
            error_type = _extract_error_type(test_result.error_message)

            ed = ErrorDetails(
                error_type=error_type,
                message=test_result.error_message or "No error message captured",
                stack_trace=test_result.longrepr,
            )
            test_err = TestError(
                test_file=test_result.test_file,
                test_function=test_result.test_function,
                error_details=ed,
            )
            test_errors.append(test_err)

    # Process collection errors
    for collection_error_str in result.collection_errors:
        ed = ErrorDetails(
            error_type="CollectionError",
            message=collection_error_str,
            stack_trace=collection_error_str,
        )
        test_err = TestError(
            # Heuristic to find file path, might need improvement
            test_file=Path("unknown_collection_file.py"),
            test_function="pytest_collection",
            error_details=ed,
        )
        test_errors.append(test_err)

    return test_errors
