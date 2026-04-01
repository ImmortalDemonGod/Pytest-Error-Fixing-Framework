"""
FabricStrategy — infrastructure layer.

Generates high-quality example-based pytest tests by calling an LLM via
LiteLLM.  Accepts an optional hypothesis-generated scaffold as a template
to give the LLM correct imports and call signatures cheaply.

Mirrors the interface of HypothesisStrategy so the orchestrator can chain
or swap strategies without knowing which one it's using.
"""

import logging
from typing import Optional

from litellm import completion

from src.dev.test_generator.core.models import (
    AnalysisContext,
    GenerationVariant,
    TestableEntity,
)
from src.dev.test_generator.generate.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

# Minimum character count for generated code to be considered non-trivial.
_MIN_CONTENT_LENGTH = 50


class FabricStrategy:
    """Generate example-based pytest tests using an LLM.

    Parameters
    ----------
    model:
        LiteLLM model identifier, e.g. ``"openrouter/openai/gpt-4o-mini"``.
    api_key:
        Provider API key.  Pass None for local models (Ollama, etc.).
    temperature:
        Sampling temperature.  Lower values (0.2–0.4) produce more
        deterministic, syntactically correct code.
    max_retries:
        How many LLM calls to attempt before giving up on an entity.
    """

    def __init__(
        self,
        model: str = "openrouter/openai/gpt-4o-mini",
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 2,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API (matches HypothesisStrategy.generate signature + context)
    # ------------------------------------------------------------------

    def generate(
        self,
        entity: TestableEntity,
        variant: GenerationVariant,
        context: AnalysisContext,
        hypothesis_template: str = "",
    ) -> Optional[str]:
        """Call the LLM and return cleaned test code, or None on failure.

        Retries up to ``max_retries`` times.  Each retry resets the
        conversation so the LLM gets a fresh attempt (not a thread that
        includes a previous broken response).
        """
        user_prompt = build_user_prompt(entity, variant, context, hypothesis_template)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(max(1, self.max_retries)):
            raw = self._call_llm(messages, attempt)
            if raw is not None:
                return raw
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_llm(self, messages: list, attempt: int) -> Optional[str]:
        """Make one LLM completion call.  Returns cleaned code or None."""
        try:
            response = completion(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                api_key=self.api_key,
            )
            raw = response.choices[0].message.content
            return self._process_response(raw)
        except Exception as exc:
            logger.warning(
                "FabricStrategy LLM call failed (attempt %d): %s", attempt + 1, exc
            )
            return None

    @staticmethod
    def _process_response(raw: Optional[str]) -> Optional[str]:
        """Strip markdown fences and validate minimum length.

        Returns cleaned code string, or None if output is too short or empty.
        """
        if not raw:
            return None

        code = raw.strip()

        # Strip ``` fences if the LLM wrapped the output
        if code.startswith("```"):
            lines = code.splitlines()
            # Drop opening fence line (```python or ```)
            lines = lines[1:]
            # Drop closing fence if present
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines).strip()

        if len(code) < _MIN_CONTENT_LENGTH:
            return None

        return code
