# branch_fixer/services/ai/manager.py
import logging
from typing import Optional, Dict, List

from litellm import completion

from branch_fixer.core.models import TestError, CodeChanges

logger = logging.getLogger(__name__)


class AIManagerError(Exception):
    """Base exception for AI manager errors"""
    pass


class PromptGenerationError(AIManagerError):
    """Raised when prompt construction fails"""
    pass


class CompletionError(AIManagerError):
    """Raised when AI request fails"""
    pass


_SYSTEM_PROMPT = """You are a Python testing expert specializing in fixing failing tests.

Your role:
1. Understand why the test is failing
2. Generate a minimal fix that makes it pass while preserving the test's intent
3. Never change what the test is testing — only fix syntax errors, import issues, wrong assertions, or missing setup

Respond in EXACTLY this format:
Explanation: [one sentence: what was wrong and what you changed]
Confidence: [0.0-1.0]
Modified code:
```python
[complete fixed file content — never partial snippets]
```"""


class AIManager:
    """
    Manages interactions with AI services for generating test fixes.
    Uses LiteLLM to support multiple providers including OpenAI and Ollama.

    Maintains a persistent conversation thread per error so that on retry
    the AI sees its previous failed attempt and tries a different approach.

    Example usage with OpenRouter:
        manager = AIManager(
            api_key="sk-or-...",
            model="openrouter/openai/gpt-4o-mini"
        )

    # -------------------------------------------------------------------------
    # Not yet implemented (from manager_design_draft.py):
    #
    # - Flaky test detection: run a test N times before fixing; if it has mixed
    #   pass/fail results it's flaky and shouldn't be "fixed" at all.
    #
    # - Line-level surgical edits: instead of replacing the whole file, generate
    #   LineChange(action, line_number, content) objects and apply in reverse line
    #   order to avoid index shifting. Requires a model that reliably produces
    #   structured diffs (current OpenRouter models don't).
    #
    # - Confidence-gated retry: if confidence score < threshold, skip straight to
    #   the next retry rather than applying a low-confidence fix.
    #
    # - Docker isolation: run verification tests inside a container so the fix
    #   doesn't depend on the local venv state.
    #
    # - ManagerState.success_rate: track all FixAttempt outcomes across a session
    #   to report per-model fix rates.
    # -------------------------------------------------------------------------
    """

    def __init__(
        self,
        api_key: Optional[str],
        model: str = "openrouter/openai/gpt-5-mini",
        base_temperature: float = 0.4,
    ):
        """
        Initialize AI manager.

        Args:
            api_key: API key (optional for some providers like Ollama)
            model: Model identifier in format "provider/model"
                   e.g. "openrouter/openai/gpt-4o-mini",
                        "openrouter/anthropic/claude-3-5-sonnet",
                        "ollama/codellama"
            base_temperature: Default temperature for generations
        """
        import os

        self.api_key = api_key
        self.model = model
        self.base_temperature = base_temperature

        # Persistent conversation thread — grows across retries for the same error
        self._messages: List[Dict[str, str]] = []
        self._current_error_id: Optional[str] = None

        # Set API key env var scoped to the provider prefix
        if api_key:
            provider = model.split("/")[0].lower()
            env_var_map = {
                "openrouter": "OPENROUTER_API_KEY",
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
            }
            env_var = env_var_map.get(provider)
            if env_var:
                os.environ[env_var] = api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_fix(self, error: TestError, temperature: float) -> CodeChanges:
        """
        Generate a fix attempt for the given test error.

        First call for an error: runs an analysis step then builds an initial fix prompt.
        Subsequent calls for the same error (retries): injects failure feedback into the
        existing thread so the AI knows to try a different approach.

        Args:
            error: TestError instance containing error details
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            CodeChanges object with suggested fix

        Raises:
            PromptGenerationError: If prompt construction fails
            CompletionError: If AI request fails
            ValueError: If temperature is out of range
        """
        if not 0 <= temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")

        try:
            is_new_error = str(error.id) != self._current_error_id

            if is_new_error:
                self._current_error_id = str(error.id)
                self._reset_thread()

                # Read the current test file for context
                try:
                    current_code = error.test_file.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(f"Could not read test file: {e}")
                    current_code = "[file unreadable]"

                # Analyze error separately at low temperature — factual, not creative
                analysis = self._analyze_error(error)
                logger.info(f"Error analysis for {error.test_function}: {analysis}")

                user_prompt = self._build_initial_prompt(error, analysis, current_code)
            else:
                # Retry: the thread already has the previous attempt — ask AI to reconsider
                logger.info(
                    f"Retry for {error.test_function} — injecting failure feedback into thread"
                )
                user_prompt = (
                    "That fix did not pass the tests. "
                    "Re-examine the error from a different angle and try a completely different approach. "
                    "Return the complete fixed file content in the same format as before."
                )

            self._messages.append({"role": "user", "content": user_prompt})

            response = completion(
                model=self.model,
                messages=self._messages,
                temperature=temperature,
            )

            reply = response.choices[0].message.content
            # Add to thread so next retry sees the full conversation
            self._messages.append({"role": "assistant", "content": reply})

            return self._parse_response(reply)

        except Exception as e:
            raise CompletionError(f"AI request failed: {str(e)}") from e

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _reset_thread(self) -> None:
        self._messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

    @staticmethod
    def _clean_stack_trace(stack_trace: Optional[str]) -> str:
        """
        Strip internal pytest frames from a longrepr string.

        The in-process runner with -p no:terminal causes pytest assertion
        introspection to fail, polluting the longrepr with internal venv
        tracebacks after the first '_ _ _' separator line.
        Only the section before that separator is relevant to the test author.
        """
        if not stack_trace:
            return "None"
        # Split on the separator line (underscores with spaces, e.g. "_ _ _ _ _")
        import re
        parts = re.split(r"\n[_ ]{10,}\n", stack_trace, maxsplit=1)
        cleaned = parts[0].strip()
        # Also strip lines that reference .venv internals as a fallback
        lines = [
            line for line in cleaned.splitlines()
            if ".venv/" not in line
        ]
        return "\n".join(lines).strip() or stack_trace[:300]

    def _analyze_error(self, error: TestError) -> str:
        """
        Quick analysis call — NOT added to the main fix thread.
        Returns a short description of root cause and fix strategy.
        Uses temperature=0.1 for factual, deterministic output.
        """
        stack_trace = self._clean_stack_trace(error.error_details.stack_trace)
        messages = [
            {
                "role": "system",
                "content": "You are a Python testing expert. Analyze failing test errors concisely.",
            },
            {
                "role": "user",
                "content": (
                    f"Analyze this test failure in 2-3 sentences: "
                    f"what is the root cause and what type of fix is needed?\n\n"
                    f"Test: {error.test_function} in {error.test_file}\n"
                    f"Error type: {error.error_details.error_type}\n"
                    f"Error message: {error.error_details.message}\n"
                    f"Stack trace: {stack_trace}"
                ),
            },
        ]
        try:
            response = completion(model=self.model, messages=messages, temperature=0.1)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Analysis step failed (non-fatal): {e}")
            return f"{error.error_details.error_type}: {error.error_details.message}"

    def _build_initial_prompt(
        self, error: TestError, analysis: str, current_code: str
    ) -> str:
        stack_trace = self._clean_stack_trace(error.error_details.stack_trace)
        return (
            f"Fix this failing test.\n\n"
            f"Root cause analysis: {analysis}\n\n"
            f"Test function: {error.test_function}\n"
            f"Test file: {error.test_file}\n"
            f"Error type: {error.error_details.error_type}\n"
            f"Error message: {error.error_details.message}\n"
            f"Stack trace:\n{stack_trace}\n\n"
            f"Current file content:\n```python\n{current_code}\n```\n\n"
            f"Provide the complete fixed file."
        )

    def _parse_response(self, response: str) -> CodeChanges:
        """
        Parse AI response into CodeChanges.

        Logs explanation and confidence if present.
        Passes raw modified_code through (fences stripped by ChangeApplier).

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Log explanation and confidence for observability
            if "Explanation:" in response:
                explanation = response.split("Explanation:")[1].split("\n")[0].strip()
                logger.info(f"AI explanation: {explanation}")

            if "Confidence:" in response:
                try:
                    confidence = float(
                        response.split("Confidence:")[1].split("\n")[0].strip()
                    )
                    logger.info(f"AI confidence: {confidence:.2f}")
                    if confidence < 0.5:
                        logger.warning(
                            f"Low confidence fix ({confidence:.2f}) — may need retry"
                        )
                except (ValueError, IndexError):
                    pass

            # Extract modified code — ChangeApplier handles fence stripping
            if "Modified code:" in response:
                modified_code = response.split("Modified code:")[1].strip()
            else:
                modified_code = response.strip()

            return CodeChanges(original_code="", modified_code=modified_code)

        except Exception as e:
            raise ValueError(f"Failed to parse response: {str(e)}") from e
