# src/branch_fixer/services/pytest/error_processor.py
from typing import List
from pathlib import Path
from branch_fixer.core.models import TestError, ErrorDetails
from branch_fixer.services.pytest.models import SessionResult


def process_pytest_results(result: SessionResult) -> List[TestError]:
    """
    Convert a SessionResult object directly into TestError domain objects.
    This bypasses the fragile string parsing.
    """
    test_errors: List[TestError] = []

    # Process standard test failures
    for test_result in result.test_results.values():
        if test_result.failed:
            # Extract error type from the error_message if possible
            error_type = "UnknownError"
            if test_result.error_message:
                # A simple heuristic to get the error type
                error_type = test_result.error_message.split(":")[0]

            ed = ErrorDetails(
                error_type=error_type,
                message=test_result.error_message or "No error message captured",
                stack_trace=test_result.longrepr,
            )
            test_err = TestError(
                test_file=test_result.test_file,
                test_function=test_result.test_function,
                error_details=ed
            )
            test_errors.append(test_err)

    # Process collection errors
    for collection_error_str in result.collection_errors:
        ed = ErrorDetails(
            error_type="CollectionError",
            message=collection_error_str,
            stack_trace=collection_error_str
        )
        test_err = TestError(
            # Heuristic to find file path, might need improvement
            test_file=Path("unknown_collection_file.py"),
            test_function="pytest_collection",
            error_details=ed
        )
        test_errors.append(test_err)

    return test_errors
