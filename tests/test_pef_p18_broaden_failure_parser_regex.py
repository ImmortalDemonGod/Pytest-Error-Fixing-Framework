"""RED test for finding F52: failure_parser regex drops *Exception-suffixed failures.

PATTERNS[0] in src/branch_fixer/services/pytest/parsers/failure_parser.py only
matches exception type names ending in "Error", so failures raising
StopIteration, KeyboardInterrupt, or a custom *Exception class are silently
dropped instead of being captured as ErrorInfo.
"""

from branch_fixer.services.pytest.parsers.failure_parser import FailureParser


def test_parse_stop_iteration_non_error_failure():
    parser = FailureParser()
    line = "tests/test_x.py:10: StopIteration"

    result = parser.process_failure_line(line)

    assert result is not None
    assert result.error_type == "StopIteration"
    assert result.test_file == "tests/test_x.py"
    assert result.line_number == "10"


def test_parse_keyboard_interrupt_non_error_failure():
    parser = FailureParser()
    line = "tests/test_x.py:12: KeyboardInterrupt"

    result = parser.process_failure_line(line)

    assert result is not None
    assert result.error_type == "KeyboardInterrupt"
    assert result.test_file == "tests/test_x.py"
    assert result.line_number == "12"


def test_parse_custom_exception_non_error_failure():
    parser = FailureParser()
    line = "tests/test_x.py:15: CustomException"

    result = parser.process_failure_line(line)

    assert result is not None
    assert result.error_type == "CustomException"
    assert result.test_file == "tests/test_x.py"
    assert result.line_number == "15"
