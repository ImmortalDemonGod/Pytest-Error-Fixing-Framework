import re
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

from branch_fixer.services.pytest.parsers.unified_error_parser import (
    UnifiedErrorParser,
    parse_pytest_output,
    convert_errorinfo_to_testerror,
)
from branch_fixer.services.pytest.error_info import ErrorInfo
from branch_fixer.services.pytest.parsers.collection_parser import CollectionParser
from branch_fixer.services.pytest.parsers import collection_parser as coll_mod
from branch_fixer.services.pytest.parsers.failure_parser import FailureParser
from branch_fixer.services.pytest.parsers import failure_parser as fail_mod
import branch_fixer.core.models as core_models


# Module-level fixtures shared across test classes
@pytest.fixture(scope="module")
def collection_parser():
    """
    Pytest fixture that provides a fresh CollectionParser instance for tests (module scope).
    
    Returns:
        CollectionParser: a new CollectionParser instance
    """
    return CollectionParser()


@pytest.fixture(scope="module")
def failure_parser():
    """
    Provide a fresh FailureParser instance for tests.
    
    This is a module-scoped pytest fixture that yields a newly constructed FailureParser for use in test cases.
    
    Returns:
        FailureParser: A new FailureParser instance.
    """
    return FailureParser()


@pytest.fixture
def unified_parser():
    """
    Create a new UnifiedErrorParser instance.
    
    Returns:
        UnifiedErrorParser: A newly constructed parser for merging collection and failure parsing results.
    """
    return UnifiedErrorParser()


class TestUnifiedErrorParser:
    def test_constructor_initializes_parsers(self):
        u = UnifiedErrorParser()
        assert hasattr(u, "collection_parser")
        assert hasattr(u, "failure_parser")
        assert isinstance(u.collection_parser, CollectionParser)
        assert isinstance(u.failure_parser, FailureParser)

    def test_parse_pytest_output_merges_results(self, unified_parser):
        e1 = ErrorInfo(None, None, None, None)
        e1.test_file = "tests/test_coll.py"
        e1.function = "collection"
        e1.error_type = "CollectionError"
        e1.error_details = "Import path mismatch with /conflict/path.py"

        e2 = ErrorInfo(None, None, None, None)
        e2.test_file = "tests/test_fail.py"
        e2.function = "test_func"
        e2.error_type = "AssertionError"
        e2.error_details = "assert failed"

        with mock.patch.object(
            unified_parser.collection_parser, "parse_collection_errors", return_value=[e1]
        ) as mock_coll, mock.patch.object(
            unified_parser.failure_parser, "parse_test_failures", return_value=[e2]
        ) as mock_fail:
            merged = unified_parser.parse_pytest_output("some output")
            mock_coll.assert_called_once()
            mock_fail.assert_called_once()
            assert merged == [e1, e2]

    def test_parse_pytest_output_empty_returns_empty_list(self, unified_parser):
        with mock.patch.object(
            unified_parser.collection_parser, "parse_collection_errors", return_value=[]
        ), mock.patch.object(
            unified_parser.failure_parser, "parse_test_failures", return_value=[]
        ):
            result = unified_parser.parse_pytest_output("")
            assert result == []

    def test_parse_pytest_output_propagates_exception_from_collection_parser(self, unified_parser):
        def raise_err(*args, **kwargs):
            """
            Always raises a ValueError with the message "boom".
            
            Raises:
                ValueError: Always raised with message "boom".
            """
            raise ValueError("boom")

        with mock.patch.object(
            unified_parser.collection_parser, "parse_collection_errors", side_effect=raise_err
        ):
            with pytest.raises(ValueError, match="boom"):
                unified_parser.parse_pytest_output("irrelevant")


class Test_parse_pytest_output_function:
    def test_module_parse_pytest_output_delegates_to_class(self):
        sentinel = ["SENTINEL"]
        with mock.patch.object(
            UnifiedErrorParser, "parse_pytest_output", return_value=sentinel
        ) as mock_method:
            res = parse_pytest_output("text")
            mock_method.assert_called_once()
            assert res is sentinel

    def test_module_parse_pytest_output_propagates_exception(self):
        with mock.patch.object(
            UnifiedErrorParser, "parse_pytest_output", side_effect=RuntimeError("fail")
        ):
            with pytest.raises(RuntimeError, match="fail"):
                parse_pytest_output("x")


class TestConvertErrorInfoToTestError:
    def test_convert_maps_fields_with_stack_trace(self, tmp_path):
        einfo = ErrorInfo(None, None, None, None)
        einfo.test_file = "tests/test_example.py"
        einfo.function = "test_func"
        einfo.error_type = "AssertionError"
        einfo.error_details = "assertion failed"
        einfo.code_snippet = "Traceback (most recent call last):\n  ..."

        converted = convert_errorinfo_to_testerror([einfo])
        assert isinstance(converted, list)
        assert len(converted) == 1
        t_err = converted[0]
        # TestError.test_file is a Path and equals the provided path
        assert isinstance(t_err.test_file, Path)
        assert str(t_err.test_file) == "tests/test_example.py"
        assert t_err.test_function == "test_func"
        assert hasattr(t_err, "error_details")
        assert t_err.error_details.error_type == "AssertionError"
        assert t_err.error_details.message == "assertion failed"
        assert t_err.error_details.stack_trace == "Traceback (most recent call last):\n  ..."

    def test_convert_empty_snippet_maps_to_none(self):
        einfo = ErrorInfo(None, None, None, None)
        einfo.test_file = "a.py"
        einfo.function = "f"
        einfo.error_type = "TypeError"
        einfo.error_details = "wrong type"
        einfo.code_snippet = ""

        converted = convert_errorinfo_to_testerror([einfo])
        assert len(converted) == 1
        assert converted[0].error_details.stack_trace is None

    def test_convert_handles_multiple_errorinfos(self):
        e1 = ErrorInfo(None, None, None, None)
        e1.test_file = "t1.py"
        e1.function = "f1"
        e1.error_type = "E1"
        e1.error_details = "d1"
        e1.code_snippet = "s1"

        e2 = ErrorInfo(None, None, None, None)
        e2.test_file = "t2.py"
        e2.function = "f2"
        e2.error_type = "E2"
        e2.error_details = "d2"
        e2.code_snippet = ""

        converted = convert_errorinfo_to_testerror([e1, e2])
        assert len(converted) == 2
        assert str(converted[0].test_file).endswith("t1.py")
        assert converted[1].error_details.stack_trace is None

    def test_convert_propagates_constructor_exceptions(self, monkeypatch):
        # Create a fake module where TestError raises on instantiation
        fake_mod = types.ModuleType("branch_fixer.core.models")
        class BadTestError:
            def __init__(self, *args, **kwargs):
                """
                Constructor that always fails to instantiate the class.
                
                Raises:
                    ValueError: Always raised with the message "bad constructor".
                """
                raise ValueError("bad constructor")
        class GoodErrorDetails:
            def __init__(self, *args, **kwargs):
                """
                Initialize the object without performing any setup.
                
                Accepts arbitrary positional and keyword arguments for call-site compatibility; arguments are ignored.
                """
                pass

        fake_mod.TestError = BadTestError
        fake_mod.ErrorDetails = GoodErrorDetails

        monkeypatch.setitem(sys.modules, "branch_fixer.core.models", fake_mod)

        einfo = ErrorInfo(None, None, None, None)
        einfo.test_file = "a.py"
        einfo.function = "f"
        einfo.error_type = "X"
        einfo.error_details = "d"
        einfo.code_snippet = ""

        with pytest.raises(ValueError, match="bad constructor"):
            convert_errorinfo_to_testerror([einfo])


class TestCollectionParser:
    def test_parse_collection_errors_finds_and_validates(self, monkeypatch, collection_parser):
        # Pattern with three groups: group 1 = test file, group 2 = filler, group 3 = conflicting path
        monkeypatch.setattr(coll_mod, "COLLECTION_PATTERN", r"(test_[^\s]+)(.*)with\s+(\S+)")
        output = "Collecting test_foo.py something with /conflict/path.py\n"
        results = collection_parser.parse_collection_errors(output)
        assert len(results) == 1
        res = results[0]
        assert res.test_file == "test_foo.py"
        assert res.function == "collection"
        assert res.error_type == "CollectionError"
        assert res.error_details == "Import path mismatch with /conflict/path.py"

    def test_extract_collection_match_returns_expected_errorinfo(self, collection_parser):
        pattern = r"(test_[^\s]+)(.*)with\s+(\S+)"
        match = re.search(pattern, "Collecting test_bar.py blah with /p.py")
        assert match is not None
        einfo = collection_parser.extract_collection_match(match)
        assert einfo.test_file == "test_bar.py"
        assert "Import path mismatch with" in einfo.error_details
        assert einfo.function == "collection"

    def test_validate_collection_error_rejects_non_collection(self, collection_parser):
        bad = ErrorInfo(None, None, None, None)
        bad.test_file = "x"
        bad.function = "not_collection"
        bad.error_type = "CollectionError"
        bad.error_details = "Import path mismatch with /x"
        assert collection_parser.validate_collection_error(bad) is False

        bad2 = ErrorInfo(None, None, None, None)
        bad2.test_file = "x"
        bad2.function = "collection"
        bad2.error_type = "Other"
        bad2.error_details = "Import path mismatch with /x"
        assert collection_parser.validate_collection_error(bad2) is False

        bad3 = ErrorInfo(None, None, None, None)
        bad3.test_file = "x"
        bad3.function = "collection"
        bad3.error_type = "CollectionError"
        bad3.error_details = "Some other message"
        assert collection_parser.validate_collection_error(bad3) is False

    def test_parse_collection_errors_ignores_invalid_matches(self, monkeypatch, collection_parser):
        # Make the parser extract ok matches but validate return False -> should get empty list
        monkeypatch.setattr(coll_mod, "COLLECTION_PATTERN", r"(test_[^\s]+)(.*)with\s+(\S+)")
        with mock.patch.object(CollectionParser, "validate_collection_error", return_value=False):
            res = collection_parser.parse_collection_errors("Collecting test_x.py foo with /p.py")
            assert res == []


class TestFailureParser:
    @pytest.fixture(autouse=True)
    def _set_patterns(self, monkeypatch):
        """
        Set a deterministic failure-line pattern for tests.
        
        Monkeypatches the failure parser module's `PATTERNS` constant to a single regular expression that matches lines of the form `path.py:line: ErrorType`.
        
        Parameters:
            monkeypatch: pytest's `monkeypatch` fixture used to replace module attributes for the duration of the test.
        """
        monkeypatch.setattr(fail_mod, "PATTERNS", [r"(\S+\.py):(\d+):\s*(\w+)"])

    def test__get_test_name_from_header_returns_name(self, failure_parser):
        line = "_ module.Class.test_method _"
        assert failure_parser._get_test_name_from_header(line) == "test_method"

        line2 = "_ simple_test _"
        assert failure_parser._get_test_name_from_header(line2) == "simple_test"

    @pytest.mark.parametrize("input_line", ["FAILURES", "  FAILURES  ", "somethingFAILURESsomething"])
    def test__should_start_capturing_detects_failures(self, failure_parser, input_line):
        assert failure_parser._should_start_capturing(input_line)

    def test__get_test_name_from_header_returns_none_for_non_header(self, failure_parser):
        assert failure_parser._get_test_name_from_header("no underscores") is None
        assert failure_parser._get_test_name_from_header("__") is None
        assert failure_parser._get_test_name_from_header("_   _") is None

    def test__handle_test_header_sets_current_function_when_header(self, failure_parser):
        line = "_ module.TestCase.test_one _"
        current, tb, details = failure_parser._handle_test_header(line, line.strip(), None)
        assert current == "test_one"
        assert tb == [line]
        assert details == []

    def test__handle_test_header_treats_underscore_line_without_name_as_traceback(self, failure_parser):
        stripped = "____"
        line = "____"
        cur_fn = "prev"
        current, tb, details = failure_parser._handle_test_header(line, stripped, cur_fn)
        assert current == cur_fn
        assert tb == [line]
        assert details == []

    def test__handle_error_detail_appends_error_detail_and_traceback(self, failure_parser):
        line = "E AssertionError: expected 1"
        tb = []
        details = []
        failure_parser._handle_error_detail(line, line.strip(), tb, details)
        assert tb[-1] == line
        assert details[-1] == "AssertionError: expected 1"

    def test__is_checks(self, failure_parser):
        assert failure_parser._is_test_header("_a_")
        assert not failure_parser._is_test_header("a")
        assert failure_parser._is_error_detail("E something")
        assert not failure_parser._is_error_detail("something")
        assert failure_parser._is_failing_line_indicator("> code")
        assert not failure_parser._is_failing_line_indicator(" code")

    def test_process_failure_line_matches_and_returns_errorinfo(self, failure_parser):
        line = "tests/test_x.py:10: AssertionError"
        res = failure_parser.process_failure_line(line)
        assert isinstance(res, ErrorInfo)
        assert res.test_file == "tests/test_x.py"
        assert res.line_number == "10"
        assert res.error_type == "AssertionError"
        assert res.function == "unknown"
        assert res.error_details == ""

    def test_process_failure_line_returns_none_for_non_matching_or_empty(self, failure_parser):
        assert failure_parser.process_failure_line("") is None
        assert failure_parser.process_failure_line("no match here") is None

    def test__process_line_for_error_appends_traceback_and_returns_none_if_no_match(self, failure_parser):
        tb = []
        details = []
        line = "    some traceback line"
        res = failure_parser._process_line_for_error(line, None, tb, details)
        assert res is None
        assert tb and tb[-1].strip() == "some traceback line"

    def test__process_line_for_error_matches_and_creates_errorinfo(self, failure_parser):
        traceback_lines = ["_ module.test_x _", ">   assert 1 == 2", "E AssertionError: fail"]
        error_details_lines = ["AssertionError: fail"]
        line = "tests/test_x.py:20: AssertionError"
        res = failure_parser._process_line_for_error(line, "test_x", traceback_lines, error_details_lines)
        assert isinstance(res, ErrorInfo)
        assert res.test_file == "tests/test_x.py"
        assert res.line_number == "20"
        assert res.error_type == "AssertionError"
        assert res.function == "test_x"
        assert "assert 1 == 2" in res.code_snippet
        assert "AssertionError: fail" in res.error_details

    def test_parse_test_failures_full_flow_produces_errorinfos(self, failure_parser):
        output = "\n".join(
            [
                "some header",
                "FAILURES",
                "_ module.Class.test_method _",
                ">     assert x == y",
                "E AssertionError: expected 1",
                "tests/test_x.py:20: AssertionError",
            ]
        )
        results = failure_parser.parse_test_failures(output)
        assert len(results) == 1
        r = results[0]
        assert r.test_file == "tests/test_x.py"
        assert r.line_number == "20"
        assert r.error_type == "AssertionError"
        assert r.function == "test_method"
        assert "assert x == y" in r.code_snippet
        assert "expected 1" in r.error_details

    def test_parse_test_failures_multiple_errors(self, failure_parser):
        output = "\n".join(
            [
                "FAILURES",
                "_ mod.test_one _",
                ">  code1",
                "E AssertionError: a",
                "a.py:1: AssertionError",
                "_ mod.test_two _",
                ">  code2",
                "E AssertionError: b",
                "b.py:2: AssertionError",
            ]
        )
        res = failure_parser.parse_test_failures(output)
        assert len(res) == 2
        assert res[0].test_file == "a.py"
        assert res[1].test_file == "b.py"

    def test_extract_traceback_stops_on_pattern_match_and_returns_index(self, failure_parser):
        lines = [
            "_ header _",
            "some code line",
            "E Error: msg",
            "tests/t.py:5: ValueError",
            "after"
        ]
        tb, idx = failure_parser.extract_traceback(lines, 0)
        # should stop at the line matching pattern and return its index
        assert "some code line" in tb
        assert idx == 3

    def test_extract_traceback_handles_no_pattern_match(self, failure_parser):
        lines = ["_ header _", "line1", "line2"]
        tb, idx = failure_parser.extract_traceback(lines, 0)
        assert "line1" in tb
        assert idx == len(lines)


class TestErrorInfo:
    def test_file_path_returns_Path_and_formatted_error_and_has_traceback(self):
        e = ErrorInfo(None, None, None, None)
        e.test_file = "tests/foo.py"
        e.function = "f"
        e.error_type = "XError"
        e.error_details = "details"
        e.code_snippet = ""
        e.line_number = "0"

        assert isinstance(e.file_path, Path)
        assert str(e.file_path) == "tests/foo.py"
        assert e.formatted_error == "XError: details"
        assert not e.has_traceback

        e.update_snippet("trace")
        assert e.code_snippet == "trace"
        assert e.has_traceback

    def test_update_snippet_overwrites(self):
        e = ErrorInfo(None, None, None, None)
        e.code_snippet = "old"
        e.update_snippet("new")
        assert e.code_snippet == "new"