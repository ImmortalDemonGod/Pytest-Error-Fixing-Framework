# src/branch_fixer/services/pytest/error_processor.py
from typing import List
from pathlib import Path
from branch_fixer.core.models import TestError, ErrorDetails
from branch_fixer.services.pytest.parsers.unified_error_parser import (
    parse_pytest_output as _unified_parse_output,
)


def parse_pytest_errors(output: str) -> List[TestError]:
    """Parse pytest output and convert to TestError objects."""
    from branch_fixer.services.pytest.parsers.unified_error_parser import (
        UnifiedErrorParser,
    )
    parser = UnifiedErrorParser()
    error_info_list = parser.parse_pytest_output(output)

    test_errors: List[TestError] = []

    for einfo in error_info_list:
        ed = ErrorDetails(
            error_type=einfo.error_type,
            message=einfo.error_details,
            stack_trace=einfo.code_snippet or None,
        )
        test_err = TestError(
            test_file=einfo.file_path,
            test_function=einfo.function,
            error_details=ed
        )
        test_errors.append(test_err)

    return test_errors
