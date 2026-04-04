"""Tests for AIManager — prompt construction, response parsing, and LiteLLM integration."""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

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
    """
    Constructs a TestError for the test function `test_add` in `tests/test_math.py`.
    
    Returns:
        TestError: Instance with test_file set to Path("tests/test_math.py"), test_function "test_add",
        and error_details containing error_type "AssertionError", message "assert -1 == 5",
        and stack_trace "tests/test_math.py:8: AssertionError".
    """
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
    """
    Create a mocked LiteLLM-style response object whose first choice's message content is the given text.
    
    Parameters:
    	content (str): Text to set as response.choices[0].message.content.
    
    Returns:
    	MagicMock: Mock object shaped like a LiteLLM response with `.choices[0].message.content == content`.
    """
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


# Response using new format: Explanation / Confidence / Modified code
VALID_RESPONSE = (
    "Explanation: Changed assert to use correct expected value.\n"
    "Confidence: 0.9\n"
    "Modified code:\n"
    "```python\n"
    "def test_add():\n"
    "    assert add(2, 3) == 5\n"
    "```"
)

# Minimal valid response — just Modified code block
MINIMAL_RESPONSE = "Modified code:\n```python\ndef test_add():\n    assert True\n```"


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

    def test_api_key_stored_on_instance(self):
        # API key is no longer injected into os.environ — it's passed per-call
        before = os.environ.copy()
        mgr = AIManager(api_key="or-test-key", model="openrouter/openai/gpt-4o-mini")
        assert mgr.api_key == "or-test-key"
        # os.environ must not have been mutated
        assert os.environ == before

    def test_api_key_none_does_not_mutate_env(self):
        before = os.environ.copy()
        AIManager(api_key=None, model="ollama/codellama")
        assert os.environ == before

    def test_thread_starts_empty(self):
        m = AIManager(api_key=None)
        assert m._messages == []

    def test_current_error_id_starts_none(self):
        m = AIManager(api_key=None)
        assert m._current_error_id is None


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

    def test_boundary_zero_is_accepted(self, error, tmp_path):
        (tmp_path / "test_math.py").write_text("def test_add(): pass")
        error.test_file = tmp_path / "test_math.py"
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            result = m.generate_fix(error, temperature=0.0)
        assert isinstance(result, CodeChanges)

    def test_boundary_one_is_accepted(self, error, tmp_path):
        (tmp_path / "test_math.py").write_text("def test_add(): pass")
        error.test_file = tmp_path / "test_math.py"
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            result = m.generate_fix(error, temperature=1.0)
        assert isinstance(result, CodeChanges)


# ---------------------------------------------------------------------------
# generate_fix — LiteLLM integration
# ---------------------------------------------------------------------------

class TestGenerateFixIntegration:
    def test_calls_completion_with_correct_model(self, error, tmp_path):
        # generate_fix calls completion twice: once for analysis, once for fix
        (tmp_path / "test_math.py").write_text("def test_add(): pass")
        error.test_file = tmp_path / "test_math.py"
        m = AIManager(api_key=None, model="openrouter/openai/gpt-4o-mini")
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            m.generate_fix(error, temperature=0.4)
        # Both calls use the same model
        for c in mock_c.call_args_list:
            assert c.kwargs["model"] == "openrouter/openai/gpt-4o-mini"

    def test_fix_call_uses_requested_temperature(self, error, tmp_path):
        (tmp_path / "test_math.py").write_text("def test_add(): pass")
        error.test_file = tmp_path / "test_math.py"
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            m.generate_fix(error, temperature=0.7)
        # Last call (the fix call) uses the requested temperature
        fix_call = mock_c.call_args_list[-1]
        assert fix_call.kwargs["temperature"] == 0.7

    def test_analysis_call_uses_low_temperature(self, error, tmp_path):
        (tmp_path / "test_math.py").write_text("def test_add(): pass")
        error.test_file = tmp_path / "test_math.py"
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            m.generate_fix(error, temperature=0.7)
        # First call (analysis) uses temperature=0.1
        analysis_call = mock_c.call_args_list[0]
        assert analysis_call.kwargs["temperature"] == 0.1

    def test_returns_code_changes_on_success(self, error, tmp_path):
        (tmp_path / "test_math.py").write_text("def test_add(): pass")
        error.test_file = tmp_path / "test_math.py"
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            result = m.generate_fix(error, temperature=0.4)
        assert isinstance(result, CodeChanges)

    def test_wraps_litellm_exception_as_completion_error(self, error, tmp_path):
        (tmp_path / "test_math.py").write_text("def test_add(): pass")
        error.test_file = tmp_path / "test_math.py"
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion", side_effect=RuntimeError("timeout")):
            with pytest.raises(CompletionError):
                m.generate_fix(error, temperature=0.4)


# ---------------------------------------------------------------------------
# Thread persistence — new error vs retry behaviour
# ---------------------------------------------------------------------------

class TestThreadPersistence:
    def test_thread_resets_for_new_error(self, tmp_path):
        f = tmp_path / "test_foo.py"
        f.write_text("def test_foo(): pass")
        error1 = TestError(
            test_file=f,
            test_function="test_foo",
            error_details=ErrorDetails(error_type="AssertionError", message="fail"),
        )
        error2 = TestError(
            test_file=f,
            test_function="test_bar",
            error_details=ErrorDetails(error_type="AssertionError", message="fail2"),
        )
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            m.generate_fix(error1, temperature=0.4)
            msg_count_after_first = len(m._messages)
            m.generate_fix(error2, temperature=0.4)
            # Thread reset: message count should be back to a small number, not accumulated
            assert len(m._messages) <= msg_count_after_first

    def test_retry_appends_failure_feedback_to_thread(self, tmp_path):
        f = tmp_path / "test_foo.py"
        f.write_text("def test_foo(): pass")
        error = TestError(
            test_file=f,
            test_function="test_foo",
            error_details=ErrorDetails(error_type="AssertionError", message="fail"),
        )
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            m.generate_fix(error, temperature=0.4)
            messages_after_first = len(m._messages)
            m.generate_fix(error, temperature=0.5)
            # Thread grew: retry feedback + new user prompt + assistant reply
            assert len(m._messages) > messages_after_first

    def test_retry_does_not_reset_error_id(self, tmp_path):
        f = tmp_path / "test_foo.py"
        f.write_text("def test_foo(): pass")
        error = TestError(
            test_file=f,
            test_function="test_foo",
            error_details=ErrorDetails(error_type="AssertionError", message="fail"),
        )
        m = AIManager(api_key=None)
        with patch("branch_fixer.services.ai.manager.completion") as mock_c:
            mock_c.return_value = make_mock_response(VALID_RESPONSE)
            m.generate_fix(error, temperature=0.4)
            m.generate_fix(error, temperature=0.5)
        assert m._current_error_id == str(error.id)


# ---------------------------------------------------------------------------
# _build_initial_prompt
# ---------------------------------------------------------------------------

class TestBuildInitialPrompt:
    def test_contains_test_function(self, error):
        m = AIManager(api_key=None)
        prompt = m._build_initial_prompt(error, "analysis text", "def test_add(): pass")
        assert error.test_function in prompt

    def test_contains_error_type(self, error):
        m = AIManager(api_key=None)
        prompt = m._build_initial_prompt(error, "analysis text", "def test_add(): pass")
        assert error.error_details.error_type in prompt

    def test_contains_error_message(self, error):
        m = AIManager(api_key=None)
        prompt = m._build_initial_prompt(error, "analysis text", "def test_add(): pass")
        assert error.error_details.message in prompt

    def test_contains_analysis(self, error):
        m = AIManager(api_key=None)
        prompt = m._build_initial_prompt(error, "root cause: off-by-one", "code here")
        assert "root cause: off-by-one" in prompt

    def test_contains_current_code(self, error):
        m = AIManager(api_key=None)
        prompt = m._build_initial_prompt(error, "analysis", "def test_add(): assert 1==2")
        assert "def test_add(): assert 1==2" in prompt

    def test_stack_trace_none_handled(self):
        m = AIManager(api_key=None)
        error_no_trace = TestError(
            test_file=Path("test_foo.py"),
            test_function="test_foo",
            error_details=ErrorDetails(error_type="AssertionError", message="fail"),
        )
        prompt = m._build_initial_prompt(error_no_trace, "analysis", "code")
        assert "None" in prompt


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    def test_parses_modified_code_marker(self):
        m = AIManager(api_key=None)
        result = m._parse_response(VALID_RESPONSE)
        assert isinstance(result, CodeChanges)
        assert "def test_add" in result.modified_code

    def test_parses_minimal_response(self):
        m = AIManager(api_key=None)
        result = m._parse_response(MINIMAL_RESPONSE)
        assert isinstance(result, CodeChanges)

    def test_fallback_on_no_marker(self):
        m = AIManager(api_key=None)
        # No "Modified code:" marker — should fall back to whole response, not raise
        result = m._parse_response("def test_foo(): pass")
        assert result.modified_code == "def test_foo(): pass"

    def test_parses_multiline_modified_code(self):
        m = AIManager(api_key=None)
        response = "Modified code:\n```python\nx = 1\ny = 2\nz = 3\n```"
        result = m._parse_response(response)
        assert "y = 2" in result.modified_code

    def test_original_code_is_empty_string(self):
        m = AIManager(api_key=None)
        result = m._parse_response(VALID_RESPONSE)
        assert result.original_code == ""
