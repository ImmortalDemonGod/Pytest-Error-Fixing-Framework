from typing import List

from branch_fixer.services.pytest.error_info import ErrorInfo
from branch_fixer.services.pytest.parsers.collection_parser import CollectionParser
from branch_fixer.services.pytest.parsers.failure_parser import FailureParser

# If needed, you could import error_processor for fallback logic:
# from branch_fixer.services.pytest import error_processor


class UnifiedErrorParser:
    """
    Coordinates the specialized parsers (collection_parser, failure_parser)
    to produce a single unified list of parsed errors.
    """

    def __init__(self) -> None:
        # Initialize specialized parsers
        self.collection_parser = CollectionParser()
        self.failure_parser = FailureParser()
        # self.legacy_processor = error_processor  # Optional fallback

    def parse_pytest_output(self, output: str) -> List[ErrorInfo]:
        """
        Parse raw pytest stdout/stderr and return a unified list of parsed errors.
        
        Parses collection/import errors and standard test failures from the provided pytest output and returns them combined in a single list. No deduplication is performed.
        
        Parameters:
            output (str): Raw pytest output containing collection messages and failure traces.
        
        Returns:
            List[ErrorInfo]: Combined list of parsed ErrorInfo objects containing file path, function, error type, and error details.
        """
        # 1) Parse collection errors
        collection_errors = self.collection_parser.parse_collection_errors(output)

        # 2) Parse standard test failures
        failure_errors = self.failure_parser.parse_test_failures(output)

        # 3) If you have leftover corner cases, you could try a fallback here:
        # fallback_errors = ...

        # Merge them. Currently no deduping is done, but you could filter duplicates if necessary.
        all_errors = collection_errors + failure_errors
        return all_errors


def parse_pytest_output(output: str) -> List[ErrorInfo]:
    """
    Convenience function for modules that don't want to instantiate UnifiedErrorParser.
    """
    parser = UnifiedErrorParser()
    return parser.parse_pytest_output(output)


# Optional utility if you want to go from ErrorInfo -> TestError in one step:
def convert_errorinfo_to_testerror(errors: List[ErrorInfo]):
    """
    Convert parsed ErrorInfo objects into TestError domain objects.
    
    Parameters:
        errors (List[ErrorInfo]): Parsed `ErrorInfo` instances to convert.
    
    Returns:
        List[TestError]: `TestError` domain objects with `ErrorDetails` constructed from each input `ErrorInfo`.
    """
    from branch_fixer.core.models import TestError, ErrorDetails

    converted = []
    for einfo in errors:
        detail = ErrorDetails(
            error_type=einfo.error_type,
            message=einfo.error_details,
            stack_trace=einfo.code_snippet or None,
        )
        t_err = TestError(
            test_file=einfo.file_path,
            test_function=einfo.function,
            error_details=detail,
        )
        converted.append(t_err)
    return converted


# End of unified_error_parser.py
# --------------------------------------------------
# Usage example:
#   from branch_fixer.services.pytest.parsers.unified_error_parser import parse_pytest_output
#   errors_info = parse_pytest_output(raw_output_string)
#   # returns List[ErrorInfo]
#
#   # If you want them as TestError:
#   test_errors = convert_errorinfo_to_testerror(errors_info)
#
# Then proceed in orchestrator or fix service as normal.
