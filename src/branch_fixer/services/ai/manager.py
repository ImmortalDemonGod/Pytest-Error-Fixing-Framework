# branch_fixer/services/ai/manager.py
import logging
import re
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
        Create an AI manager configured with API credentials, model selection, and a default generation temperature, and initialize its persistent conversation state.
        
        Parameters:
            api_key: Optional API key used for model requests (may be None for providers that do not require a key).
            model: Model identifier in the form "provider/model" (examples: "openrouter/openai/gpt-5-mini", "openrouter/anthropic/claude-3-5-sonnet", "ollama/codellama").
            base_temperature: Default sampling temperature for generations, typically in the range 0.0–1.0.
        
        Notes:
            Initializes an empty persistent message thread and clears the current error tracking state.
        """
        self.api_key = api_key
        self.model = model
        self.base_temperature = base_temperature

        # Persistent conversation thread — grows across retries for the same error
        self._messages: List[Dict[str, str]] = []
        self._current_error_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_fix(self, error: TestError, temperature: float) -> CodeChanges:
        """
        Generate a candidate code fix for the provided failing test error.
        
        On first call for a given error id, performs a low-temperature analysis and builds an initial prompt; on subsequent calls for the same error id, appends failure feedback to the existing conversation so the AI is instructed to try a different approach.
        
        Parameters:
            error (TestError): The failing test metadata and error details used to build context.
            temperature (float): Sampling temperature between 0.0 and 1.0 that controls AI creativity.
        
        Returns:
            CodeChanges: Object containing the AI-suggested modified file content.
        
        Raises:
            ValueError: If `temperature` is not between 0.0 and 1.0.
            CompletionError: If the AI request, response handling, or parsing fails.
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
                # Retry: the thread already has the previous attempt — inject specific
                # failure context so the AI knows exactly what still went wrong.
                logger.info(
                    f"Retry for {error.test_function} — injecting failure feedback into thread"
                )
                # Re-read the test file; it will be in its original broken state because
                # FixService restores the backup before calling generate_fix again.
                try:
                    current_code = error.test_file.read_text(encoding="utf-8")
                except Exception:
                    current_code = "[file unreadable]"

                stack_trace = self._clean_stack_trace(error.error_details.stack_trace)
                user_prompt = (
                    "That fix did not pass the tests. "
                    "Here is the original failure that still needs to be resolved:\n\n"
                    f"Error type: {error.error_details.error_type}\n"
                    f"Error message: {error.error_details.message}\n"
                    f"Stack trace:\n{stack_trace}\n\n"
                    f"Current file content (restored to broken state):\n```python\n{current_code}\n```\n\n"
                    "Try a completely different approach. "
                    "Return the complete fixed file content."
                )

            self._messages.append({"role": "user", "content": user_prompt})

            response = completion(
                model=self.model,
                messages=self._messages,
                temperature=temperature,
                api_key=self.api_key,
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
        """
        Reset the manager's conversation history to the initial system prompt.
        
        Replaces the internal message thread with a single system message containing the module's predefined `_SYSTEM_PROMPT`, clearing any prior assistant/user exchanges so subsequent requests start from a clean AI context.
        """
        self._messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

    @staticmethod
    def _clean_stack_trace(stack_trace: Optional[str]) -> str:
        """
        Clean a pytest longrepr stack trace by removing internal or irrelevant sections.
        
        Returns:
            A cleaned stack trace string suitable for presenting to a test author. If the input is falsy, returns the literal string "None". Otherwise, returns the portion of the trace before any long underscore separator with lines referencing ".venv/" removed; if cleaning yields an empty result, returns the first 300 characters of the original stack trace.
        """
        if not stack_trace:
            return "None"
        # Split on the separator line (underscores with spaces, e.g. "_ _ _ _ _")
        import re

        parts = re.split(r"\n[_ ]{10,}\n", stack_trace, maxsplit=1)
        cleaned = parts[0].strip()
        # Also strip lines that reference .venv internals as a fallback
        lines = [line for line in cleaned.splitlines() if ".venv/" not in line]
        return "\n".join(lines).strip() or stack_trace[:300]

    def _analyze_error(self, error: TestError) -> str:
        """
        Produce a concise 2–3 sentence analysis of a failing test's root cause and the type of fix likely needed.
        
        This performs a separate, low-temperature model call (temperature=0.1) and is not appended to the main fix conversation thread. The provided TestError is expected to include test metadata (test_function, test_file) and error_details (error_type, message, stack_trace).
        
        Parameters:
            error (TestError): The failing test information and associated error details.
        
        Returns:
            str: A short human-readable analysis (2–3 sentences) describing the root cause and a recommended fix approach.
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
            response = completion(
                model=self.model,
                messages=messages,
                temperature=0.1,
                api_key=self.api_key,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Analysis step failed (non-fatal): {e}")
            return f"{error.error_details.error_type}: {error.error_details.message}"

    def _build_initial_prompt(
        self, error: TestError, analysis: str, current_code: str
    ) -> str:
        """
        Builds the initial user prompt sent to the AI for fixing a failing test.
        
        The prompt includes the provided root-cause analysis, test function and file, error type and message, a cleaned stack trace, the current file content fenced as a Python code block, and a final instruction to return the complete fixed file.
        
        Parameters:
            error (TestError): The failing-test metadata and error details.
            analysis (str): Short root-cause and fix-strategy summary.
            current_code (str): The current contents of the file to be fixed.
        
        Returns:
            prompt (str): A single formatted string ready to be appended to the AI conversation.
        """
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
        Parse the AI model's textual reply and extract the modified source file as a CodeChanges object.
        
        Attempts to extract an `Explanation:` and `Confidence:` for observability (these are logged if present; a confidence below 0.5 emits a warning). The modified code is extracted with the following precedence: a fenced code block (``` or ```python), a `Modified code:` header, or the entire response as a fallback.
        
        Returns:
            CodeChanges: `original_code` is an empty string; `modified_code` contains the extracted file contents.
        
        Raises:
            ValueError: If parsing fails unexpectedly.
        """
        try:
            # Log explanation and confidence for observability
            m = re.search(r"Explanation:\s*(.+)", response)
            if m:
                logger.info(f"AI explanation: {m.group(1).strip()}")

            m = re.search(r"Confidence:\s*([0-9.]+)", response)
            if m:
                try:
                    confidence = float(m.group(1))
                    logger.info(f"AI confidence: {confidence:.2f}")
                    if confidence < 0.5:
                        logger.warning(
                            f"Low confidence fix ({confidence:.2f}) — may need retry"
                        )
                except ValueError:
                    pass

            # Prefer fenced code blocks; fall back to "Modified code:" header;
            # last resort: treat entire response as code.
            fence_match = re.search(r"```(?:python)?\n(.*?)```", response, re.DOTALL)
            if fence_match:
                modified_code = fence_match.group(1).strip()
            elif re.search(r"Modified code\s*:", response, re.IGNORECASE):
                modified_code = re.split(
                    r"Modified code\s*:", response, flags=re.IGNORECASE, maxsplit=1
                )[1].strip()
            else:
                modified_code = response.strip()

            return CodeChanges(original_code="", modified_code=modified_code)

        except Exception as e:
            raise ValueError(f"Failed to parse response: {str(e)}") from e
