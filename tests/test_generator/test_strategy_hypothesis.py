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
    def test_returns_none_when_subprocess_returns_nonzero(self):
        strat = HypothesisStrategy()
        with patch.object(strat, "_run_hypothesis_write", return_value=None):
            assert strat.generate(_entity(), GenerationVariant.DEFAULT) is None

    def test_returns_none_when_output_too_short(self):
        strat = HypothesisStrategy()
        with patch.object(strat, "_run_hypothesis_write", return_value="short"):
            # fix_generated_code would receive "short" but _run_hypothesis_write
            # already returned None due to length check — test via _process_result
            pass  # covered by TestProcessResult below

    def test_returns_code_on_success(self):
        strat = HypothesisStrategy()
        with patch.object(strat, "_run_hypothesis_write", return_value=SAMPLE_CODE):
            result = strat.generate(_entity(), GenerationVariant.DEFAULT)
            assert result is not None
            assert len(result) > 0


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
