"""Unit tests for generate/strategies/hypothesis.py"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.dev.test_generator.core.models import GenerationVariant, TestableEntity
from src.dev.test_generator.generate.strategies.hypothesis import HypothesisStrategy

SAMPLE_CODE = "# generated\n" + "x = 1\n" * 10  # > 50 chars


def _entity(name: str = "add", entity_type: str = "function") -> TestableEntity:
    return TestableEntity(name=name, module_path="pkg.mod", entity_type=entity_type)


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


class TestIsAvailable:
    def test_returns_true_when_hypothesis_exits_zero(self):
        with patch("subprocess.run", return_value=_completed(returncode=0)):
            assert HypothesisStrategy.is_available() is True

    def test_returns_false_when_hypothesis_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert HypothesisStrategy.is_available() is False

    def test_returns_false_on_nonzero_exit(self):
        with patch("subprocess.run", return_value=_completed(returncode=1)):
            assert HypothesisStrategy.is_available() is False


class TestGenerate:
    def test_returns_none_when_all_attempts_fail(self):
        strat = HypothesisStrategy(max_retries=3)
        with patch.object(strat, "_run_hypothesis_write", return_value=None) as m:
            assert strat.generate(_entity(), GenerationVariant.DEFAULT) is None
            assert m.call_count == 3  # retried 3 times

    def test_returns_code_on_first_success(self):
        strat = HypothesisStrategy(max_retries=3)
        with patch.object(strat, "_run_hypothesis_write", return_value=SAMPLE_CODE) as m:
            result = strat.generate(_entity(), GenerationVariant.DEFAULT)
            assert result is not None
            assert m.call_count == 1  # succeeded first try — no extra retries

    def test_retries_until_success(self):
        strat = HypothesisStrategy(max_retries=3)
        # Fail twice, succeed on third attempt
        side_effects = [None, None, SAMPLE_CODE]
        with patch.object(strat, "_run_hypothesis_write", side_effect=side_effects) as m:
            result = strat.generate(_entity(), GenerationVariant.DEFAULT)
            assert result is not None
            assert m.call_count == 3

    def test_max_retries_one_makes_single_attempt(self):
        strat = HypothesisStrategy(max_retries=1)
        with patch.object(strat, "_run_hypothesis_write", return_value=None) as m:
            strat.generate(_entity(), GenerationVariant.DEFAULT)
            assert m.call_count == 1


class TestProcessResult:
    def test_valid_output_returned(self):
        result = HypothesisStrategy._process_result(_completed(stdout=SAMPLE_CODE))
        assert result == SAMPLE_CODE.strip()

    def test_too_short_output_returns_none(self):
        result = HypothesisStrategy._process_result(_completed(stdout="hi"))
        assert result is None

    def test_empty_stdout_returns_none(self):
        result = HypothesisStrategy._process_result(_completed(stdout=""))
        assert result is None

    def test_nonzero_return_code_returns_none(self):
        result = HypothesisStrategy._process_result(
            _completed(stdout=SAMPLE_CODE, returncode=1)
        )
        assert result is None

    def test_known_error_in_stderr_still_returns_none_gracefully(self):
        result = HypothesisStrategy._process_result(
            _completed(stdout="", stderr="InvalidArgument: Got non-callable", returncode=1)
        )
        assert result is None
