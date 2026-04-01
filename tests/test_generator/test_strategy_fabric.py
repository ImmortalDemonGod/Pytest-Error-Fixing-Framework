"""Unit tests for generate/strategies/fabric.py

LiteLLM calls are fully mocked — no network access in tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.dev.test_generator.core.models import (
    AnalysisContext,
    GenerationVariant,
    TestableEntity,
)
from src.dev.test_generator.generate.strategies.fabric import FabricStrategy

# Realistic-looking generated test code (> 50 chars)
SAMPLE_CODE = """\
import pytest
from pkg.mod import add

def test_add_positive():
    assert add(2, 3) == 5

def test_add_zero():
    assert add(0, 0) == 0
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(name: str = "add", entity_type: str = "function") -> TestableEntity:
    return TestableEntity(name=name, module_path="pkg.mod", entity_type=entity_type)


def _ctx() -> AnalysisContext:
    return AnalysisContext.empty("def add(a, b): return a + b")


def _make_response(content: str):
    """Build a minimal litellm-style response object."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# FabricStrategy.generate
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_returns_code_on_first_success(self):
        strat = FabricStrategy(max_retries=3)
        with patch("src.dev.test_generator.generate.strategies.fabric.completion",
                   return_value=_make_response(SAMPLE_CODE)) as mock_llm:
            result = strat.generate(_entity(), GenerationVariant.DEFAULT, _ctx())
        assert result is not None
        assert "test_add_positive" in result
        assert mock_llm.call_count == 1

    def test_retries_on_failure_then_succeeds(self):
        strat = FabricStrategy(max_retries=3)
        responses = [
            Exception("network error"),
            _make_response(SAMPLE_CODE),
        ]
        with patch("src.dev.test_generator.generate.strategies.fabric.completion",
                   side_effect=responses) as mock_llm:
            result = strat.generate(_entity(), GenerationVariant.DEFAULT, _ctx())
        assert result is not None
        assert mock_llm.call_count == 2

    def test_returns_none_when_all_retries_fail(self):
        strat = FabricStrategy(max_retries=3)
        with patch("src.dev.test_generator.generate.strategies.fabric.completion",
                   side_effect=Exception("fail")):
            result = strat.generate(_entity(), GenerationVariant.DEFAULT, _ctx())
        assert result is None

    def test_max_retries_one_makes_single_attempt(self):
        strat = FabricStrategy(max_retries=1)
        with patch("src.dev.test_generator.generate.strategies.fabric.completion",
                   side_effect=Exception("fail")) as mock_llm:
            strat.generate(_entity(), GenerationVariant.DEFAULT, _ctx())
        assert mock_llm.call_count == 1

    def test_passes_hypothesis_template_to_prompt(self):
        """The hypothesis scaffold must appear in the messages sent to LLM."""
        strat = FabricStrategy(max_retries=1)
        captured = {}

        def capture_call(**kwargs):
            captured["messages"] = kwargs["messages"]
            return _make_response(SAMPLE_CODE)

        with patch("src.dev.test_generator.generate.strategies.fabric.completion",
                   side_effect=capture_call):
            strat.generate(
                _entity(),
                GenerationVariant.DEFAULT,
                _ctx(),
                hypothesis_template="class TestFuzzAdd: pass",
            )

        user_msg = captured["messages"][1]["content"]
        assert "TestFuzzAdd" in user_msg

    def test_sends_system_prompt(self):
        """System message must be the first message."""
        strat = FabricStrategy(max_retries=1)
        captured = {}

        def capture_call(**kwargs):
            captured["messages"] = kwargs["messages"]
            return _make_response(SAMPLE_CODE)

        with patch("src.dev.test_generator.generate.strategies.fabric.completion",
                   side_effect=capture_call):
            strat.generate(_entity(), GenerationVariant.DEFAULT, _ctx())

        assert captured["messages"][0]["role"] == "system"
        assert "pytest" in captured["messages"][0]["content"].lower()

    def test_passes_temperature_to_llm(self):
        strat = FabricStrategy(temperature=0.1, max_retries=1)
        captured = {}

        def capture_call(**kwargs):
            captured["kwargs"] = kwargs
            return _make_response(SAMPLE_CODE)

        with patch("src.dev.test_generator.generate.strategies.fabric.completion",
                   side_effect=capture_call):
            strat.generate(_entity(), GenerationVariant.DEFAULT, _ctx())

        assert captured["kwargs"]["temperature"] == 0.1


# ---------------------------------------------------------------------------
# FabricStrategy._process_response
# ---------------------------------------------------------------------------


class TestProcessResponse:
    def test_returns_code_as_is_when_no_fence(self):
        code = "import pytest\n" + "x = 1\n" * 10  # >50 chars
        result = FabricStrategy._process_response(code)
        assert result == code.strip()

    def test_strips_python_fence(self):
        wrapped = f"```python\n{SAMPLE_CODE}\n```"
        result = FabricStrategy._process_response(wrapped)
        assert result is not None
        assert "```" not in result

    def test_strips_plain_fence(self):
        wrapped = f"```\n{SAMPLE_CODE}\n```"
        result = FabricStrategy._process_response(wrapped)
        assert result is not None
        assert "```" not in result

    def test_returns_none_for_empty_string(self):
        assert FabricStrategy._process_response("") is None

    def test_returns_none_for_none(self):
        assert FabricStrategy._process_response(None) is None

    def test_returns_none_when_too_short(self):
        assert FabricStrategy._process_response("hi") is None

    def test_strips_leading_trailing_whitespace(self):
        code = "\n\n" + SAMPLE_CODE + "\n\n"
        result = FabricStrategy._process_response(code)
        assert result == SAMPLE_CODE.strip()
