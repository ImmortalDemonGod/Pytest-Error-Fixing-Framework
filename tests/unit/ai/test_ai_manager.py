"""Tests for AIManager — prompt construction, response parsing, and LiteLLM integration."""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from branch_fixer.core.models import CodeChanges, ErrorDetails, TestError
from branch_fixer.services.ai.manager import (
    AIManager,
    CompletionError,
    PromptGenerationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def error():
    return TestError(
        test_file=Path("tests/test_math.py"),
        test_function="test_add",
        error_details=ErrorDetails(
            error_type="AssertionError",
            message="assert -1 == 5",
            stack_trace="tests/test_math.py:8: AssertionError",
        ),
    )


def make_mock_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


VALID_RESPONSE = (
    "Original code: def test_add():\n    assert add(2,3) == 5\n"
    "Modified code: def test_add():\n    assert add(2,3) == 5  # fixed"
)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_stores_model(self):
        m = AIManager(api_key=None, model="ollama/codellama")
        assert m.model == "ollama/codellama"

    def test_stores_base_temperature(self):
        m = AIManager(api_key=None, base_temperature=0.7)
        assert m.base_temperature == 0.7

    def test_no_api_key_does_not_mutate_env(self):
        before = os.environ.copy()
        AIManager(api_key=None)
        assert os.environ.get("OPENROUTER_API_KEY") == before.get("OPENROUTER_API_KEY")

    def test_openrouter_key_set_in_env(self):
        AIManager(api_key="or-test-key", model="openrouter/openai/gpt-4o-mini")
        assert os.environ.get("OPENROUTER_API_KEY") == "or-test-key"

    def test_openai_key_set_in_env(self):
        AIManager(api_key="sk-test", model="openai/gpt-4o")
        assert os.environ.get("OPENAI_API_KEY") == "sk-test"

    def test_anthropic_key_set_in_env(self):
        AIManager(api_key="ant-test", model="anthropic/claude-3")
        assert os.environ.get("ANTHROPIC_API_KEY") == "ant-test"

    def test_unknown_provider_does_not_set_env(self):
        before = os.environ.copy()
        AIManager(api_key="key", model="ollama/codellama")
        # ollama has no env var mapping — should not add any new keys
        new_keys = set(os.environ) - set(before)
        assert not new_keys


# ---------------------------------------------------------------------------
# generate_fix — temperature validation
# ---------------------------------------------------------------------------

class TestGenerateFixTemperature:
    def test_raises_on_temperature_below_zero(self, error):
        m = AIManager(api_key=None)
        with pytest.raises(ValueError):
            m.generate_fix(error, temperature=-0.1)

    def test_raises_on_temperature_above_one(self, error):
        m = AIManager(api_key=None)
        with pytest.raises(ValueError):
            m.generate_fix(error, temperature=1.1)

    def test_boundary_zero_is_accepted(self, error):
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            result = m.generate_fix(error, temperature=0.0)
        assert isinstance(result, CodeChanges)

    def test_boundary_one_is_accepted(self, error):
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            result = m.generate_fix(error, temperature=1.0)
        assert isinstance(result, CodeChanges)


# ---------------------------------------------------------------------------
# generate_fix — LiteLLM integration
# ---------------------------------------------------------------------------

class TestGenerateFixIntegration:
    def test_calls_completion_with_correct_model(self, error):
        m = AIManager(api_key=None, model="openrouter/openai/gpt-4o-mini")
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            m.generate_fix(error, temperature=0.4)
        mock_c.assert_called_once()
        call_kwargs = mock_c.call_args.kwargs
        assert call_kwargs["model"] == "openrouter/openai/gpt-4o-mini"

    def test_calls_completion_with_correct_temperature(self, error):
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            m.generate_fix(error, temperature=0.7)
        assert mock_c.call_args.kwargs["temperature"] == 0.7

    def test_returns_code_changes_on_success(self, error):
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            result = m.generate_fix(error, temperature=0.4)
        assert isinstance(result, CodeChanges)

    def test_wraps_litellm_exception_as_completion_error(self, error):
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion", side_effect=RuntimeError("timeout")):
            with pytest.raises(CompletionError):
                m.generate_fix(error, temperature=0.4)


# ---------------------------------------------------------------------------
# _construct_messages
# ---------------------------------------------------------------------------

class TestConstructMessages:
    def test_returns_two_messages(self, error):
        m = AIManager(api_key=None)
        messages = m._construct_messages(error)
        assert len(messages) == 2

    def test_first_message_is_system(self, error):
        m = AIManager(api_key=None)
        messages = m._construct_messages(error)
        assert messages[0]["role"] == "system"

    def test_second_message_is_user(self, error):
        m = AIManager(api_key=None)
        messages = m._construct_messages(error)
        assert messages[1]["role"] == "user"

    def test_user_message_contains_test_function(self, error):
        m = AIManager(api_key=None)
        messages = m._construct_messages(error)
        assert error.test_function in messages[1]["content"]

    def test_user_message_contains_error_type(self, error):
        m = AIManager(api_key=None)
        messages = m._construct_messages(error)
        assert error.error_details.error_type in messages[1]["content"]

    def test_user_message_contains_error_message(self, error):
        m = AIManager(api_key=None)
        messages = m._construct_messages(error)
        assert error.error_details.message in messages[1]["content"]

    def test_stack_trace_none_handled_gracefully(self):
        m = AIManager(api_key=None)
        error_no_trace = TestError(
            test_file=Path("test_foo.py"),
            test_function="test_foo",
            error_details=ErrorDetails(error_type="AssertionError", message="fail"),
        )
        messages = m._construct_messages(error_no_trace)
        assert "None" in messages[1]["content"]


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    def test_parses_well_formed_response(self):
        m = AIManager(api_key=None)
        response = "Original code: old code\nModified code: new code"
        result = m._parse_response(response)
        assert result.original_code == "old code"
        assert result.modified_code == "new code"

    def test_parses_multiline_modified_code(self):
        m = AIManager(api_key=None)
        response = "Original code: x = 1\nModified code: x = 1\ny = 2\nz = 3"
        result = m._parse_response(response)
        assert "y = 2" in result.modified_code

    def test_raises_on_missing_original_code_marker(self):
        m = AIManager(api_key=None)
        with pytest.raises(ValueError):
            m._parse_response("Modified code: new code")

    def test_raises_on_missing_modified_code_marker(self):
        m = AIManager(api_key=None)
        with pytest.raises(ValueError):
            m._parse_response("Original code: old code")

    def test_raises_on_empty_response(self):
        m = AIManager(api_key=None)
        with pytest.raises(ValueError):
            m._parse_response("")
