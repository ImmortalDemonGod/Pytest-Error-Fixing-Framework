from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from branch_fixer.services.pytest.error_processor import (
    _extract_error_type,
    process_pytest_results,
)
from branch_fixer.services.pytest.models import SessionResult, TestResult


# Module-level fixtures
@pytest.fixture(scope="module")
def session_time():
    """
    Create a consistent test session time tuple for use in SessionResult fixtures.
    
    Returns:
        tuple: (start, end, duration, exit_code)
            start (datetime): session start timestamp.
            end (datetime): session end timestamp (start + 1 second).
            duration (float): session duration in seconds (1.0).
            exit_code (int): placeholder exit code (0).
    """
    start = datetime.now()
    end = start + timedelta(seconds=1)
    duration = 1.0
    exit_code = 0  # Simple stand-in for ExitCode
    return start, end, duration, exit_code


@pytest.fixture
def basic_session(session_time):
    """
    Create a minimal SessionResult with no test results or collection errors.
    
    Parameters:
        session_time (tuple): A 4-tuple (start, end, duration, exit_code) used to initialize the SessionResult.
    
    Returns:
        SessionResult: An instance initialized from `session_time` with `test_results` set to an empty dict and `collection_errors` set to an empty list.
    """
    start, end, duration, exit_code = session_time
    sr = SessionResult(start, end, duration, exit_code)
    # Ensure defaults are empty
    sr.test_results = {}
    sr.collection_errors = []
    return sr


class Test_extract_error_type:
    # Happy path: common error tokens
    @pytest.mark.parametrize(
        "input_msg,expected",
        [
            ("ValueError: invalid value", "ValueError"),
            ("AssertionError assert failed", "AssertionError"),
            ("MyCustomException: boom", "MyCustomException"),
            ("Failure: collection failed", "UnknownError"),
        ],
    )
    def test_matches_standard_error_tokens(self, input_msg, expected):
        assert _extract_error_type(input_msg) == expected

    def test_leading_whitespace_is_stripped_and_matches(self):
        assert _extract_error_type("   TypeError: x") == "TypeError"

    def test_unicode_token_matches(self):
        # \w includes many unicode letters in Python 3
        assert _extract_error_type("ÜnicodeError: problem") == "ÜnicodeError"

    # Edge cases
    @pytest.mark.parametrize(
        "input_msg",
        [
            "some random message without token",
            "Error not at start: ValueError occurred",
            "module.TypeError: something",  # dot is non-word so won't match at start
            "hyphen-error: oops",  # hyphen not matched by \w
        ],
    )
    def test_non_matching_messages_return_unknown(self, input_msg):
        assert _extract_error_type(input_msg) == "UnknownError"

    @pytest.mark.parametrize("input_msg", [None, "", "   "])
    def test_none_and_empty_strings_return_unknown(self, input_msg):
        assert _extract_error_type(input_msg) == "UnknownError"

    def test_token_without_error_exception_or_failure_suffix_returns_unknown(self):
        assert _extract_error_type("CustomProblem: something went wrong") == "UnknownError"


class Test_process_pytest_results:
    def test_no_errors_returns_empty_list(self, basic_session):
        res = process_pytest_results(basic_session)
        assert res == []

    def test_single_failed_test_full_fields(self, session_time):
        start, end, duration, exit_code = session_time
        tr = TestResult(
            nodeid="tests/test_file.py::test_foo",
            test_file=Path("tests/test_file.py"),
            test_function="test_foo",
            failed=True,
            error_message="AssertionError: expected x",
            longrepr="Traceback (most recent call)...",
        )
        sr = SessionResult(start, end, duration, exit_code)
        sr.test_results = {"tests/test_file.py::test_foo": tr}
        sr.collection_errors = []

        out = process_pytest_results(sr)
        assert len(out) == 1
        te = out[0]
        assert te.test_file == Path("tests/test_file.py")
        assert te.test_function == "test_foo"
        assert te.error_details.error_type == "AssertionError"
        assert te.error_details.message == "AssertionError: expected x"
        assert te.error_details.stack_trace == "Traceback (most recent call)..."

    def test_failed_test_missing_message_uses_defaults(self, session_time):
        start, end, duration, exit_code = session_time
        tr = TestResult(
            nodeid="node_missing_msg",
            test_file=None,
            test_function=None,
            failed=True,
            error_message=None,
            longrepr=None,
        )
        sr = SessionResult(start, end, duration, exit_code)
        sr.test_results = {"node_missing_msg": tr}
        sr.collection_errors = []

        out = process_pytest_results(sr)
        assert len(out) == 1
        te = out[0]
        assert te.error_details.error_type == "UnknownError"
        assert te.error_details.message == "No error message captured"
        assert te.error_details.stack_trace is None

    def test_ignores_nonfailed_tests(self, session_time):
        start, end, duration, exit_code = session_time
        tr_failed = TestResult(
            nodeid="node_failed",
            test_file=Path("f.py"),
            test_function="test_ok",
            failed=True,
            error_message="ValueError: bad",
            longrepr="stack",
        )
        tr_passed = TestResult(
            nodeid="node_passed",
            test_file=Path("f2.py"),
            test_function="test_no",
            failed=False,
            error_message=None,
            longrepr=None,
        )
        sr = SessionResult(start, end, duration, exit_code)
        # insertion order: failed then passed
        sr.test_results = {"node_failed": tr_failed, "node_passed": tr_passed}
        sr.collection_errors = []

        out = process_pytest_results(sr)
        assert len(out) == 1
        assert out[0].test_function == "test_ok"

    def test_multiple_failed_tests_and_collection_errors(self, session_time):
        start, end, duration, exit_code = session_time
        tr1 = TestResult(
            nodeid="n1",
            test_file=Path("a.py"),
            test_function="test_a",
            failed=True,
            error_message="TypeError: a",
            longrepr="stack a",
        )
        tr2 = TestResult(
            nodeid="n2",
            test_file=Path("b.py"),
            test_function="test_b",
            failed=True,
            error_message="MyCustomException: boom",
            longrepr="stack b",
        )
        collection_errors = ["CollectError: failed to collect tests", "Another collection error"]
        sr = SessionResult(start, end, duration, exit_code)
        sr.test_results = {"n1": tr1, "n2": tr2}
        sr.collection_errors = collection_errors

        out = process_pytest_results(sr)
        assert len(out) == 2 + len(collection_errors)

        # Verify collection errors are transformed as expected and appear after test errors
        col_errors = out[-len(collection_errors):]
        for idx, col in enumerate(collection_errors):
            te = col_errors[idx]
            assert te.test_file == Path("unknown_collection_file.py")
            assert te.test_function == "pytest_collection"
            assert te.error_details.error_type == "CollectionError"
            assert te.error_details.message == col
            assert te.error_details.stack_trace == col

        # Verify first two correspond to tr1 and tr2
        assert out[0].test_file == Path("a.py")
        assert out[0].error_details.error_type == "TypeError"
        assert out[1].test_file == Path("b.py")
        assert out[1].error_details.error_type == "MyCustomException"

    def test_preserves_none_test_file_and_function(self, session_time):
        start, end, duration, exit_code = session_time
        tr = TestResult(
            nodeid="n_none",
            test_file=None,
            test_function=None,
            failed=True,
            error_message="Failure: something",
            longrepr="stack",
        )
        sr = SessionResult(start, end, duration, exit_code)
        sr.test_results = {"n_none": tr}
        sr.collection_errors = []

        out = process_pytest_results(sr)
        assert len(out) == 1
        te = out[0]
        assert te.test_file is None
        assert te.test_function is None

    def test_uses_extract_for_error_type(self, session_time):
        start, end, duration, exit_code = session_time
        tr = TestResult(
            nodeid="n_custom",
            test_file=Path("c.py"),
            test_function="test_c",
            failed=True,
            error_message="MyCustomException: details",
            longrepr=None,
        )
        sr = SessionResult(start, end, duration, exit_code)
        sr.test_results = {"n_custom": tr}
        sr.collection_errors = []

        out = process_pytest_results(sr)
        assert out[0].error_details.error_type == "MyCustomException"

    def test_ordering_of_results_and_collections(self, session_time):
        start, end, duration, exit_code = session_time
        tr_a = TestResult(
            nodeid="a",
            test_file=Path("a.py"),
            test_function="test_a",
            failed=True,
            error_message="ValueError: a",
            longrepr="stack a",
        )
        tr_b = TestResult(
            nodeid="b",
            test_file=Path("b.py"),
            test_function="test_b",
            failed=True,
            error_message="ValueError: b",
            longrepr="stack b",
        )
        sr = SessionResult(start, end, duration, exit_code)
        # ensure insertion order a then b
        sr.test_results = {"a": tr_a, "b": tr_b}
        sr.collection_errors = ["coll err"]

        out = process_pytest_results(sr)
        assert len(out) == 3
        assert out[0].test_function == "test_a"
        assert out[1].test_function == "test_b"
        # last is collection
        assert out[2].test_function == "pytest_collection"

    def test_handles_longrepr_and_message_distinctly(self, session_time):
        start, end, duration, exit_code = session_time
        tr = TestResult(
            nodeid="n_long",
            test_file=Path("long.py"),
            test_function="test_long",
            failed=True,
            error_message="AssertionError: nope",
            longrepr="FullTracebackHere",
        )
        sr = SessionResult(start, end, duration, exit_code)
        sr.test_results = {"n_long": tr}
        sr.collection_errors = []

        out = process_pytest_results(sr)
        te = out[0]
        assert te.error_details.message == "AssertionError: nope"
        assert te.error_details.stack_trace == "FullTracebackHere"

    def test_propagates_exceptions_from_error_details_constructor(self, session_time):
        start, end, duration, exit_code = session_time
        tr = TestResult(
            nodeid="n_err",
            test_file=Path("err.py"),
            test_function="test_err",
            failed=True,
            error_message="SomeError: fail",
            longrepr="stack",
        )
        sr = SessionResult(start, end, duration, exit_code)
        sr.test_results = {"n_err": tr}
        sr.collection_errors = []

        # Patch ErrorDetails used inside the module to raise when called
        with patch("branch_fixer.services.pytest.error_processor.ErrorDetails", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                process_pytest_results(sr)