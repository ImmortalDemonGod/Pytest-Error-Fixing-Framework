"""
FabricStrategy — infrastructure layer.

Generates high-quality example-based pytest tests by calling an LLM via
LiteLLM.

Two modes:
  - generate(): per-entity mode (legacy) — one LLM call per entity/variant
  - generate_module(): two-phase module mode (new) — first analyzes all code
    paths and produces a structured test plan, then writes a consolidated test
    file for the entire module. Substantially reduces hallucination by forcing
    the LLM to reason before writing.
"""

import logging
from typing import Optional

from litellm import completion

from src.dev.test_generator.core.models import (
    AnalysisContext,
    GenerationVariant,
    TestableEntity,
)
from src.dev.test_generator.generate.prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    MODULE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_analysis_prompt,
    build_module_prompt,
    build_user_prompt,
)

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
        How many LLM calls to attempt before giving up.
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
    # Public API — two-phase module-level generation (preferred)
    # ------------------------------------------------------------------

    def generate_module(
        self,
        context: AnalysisContext,
        hypothesis_templates: Optional[dict] = None,
        module_dotpath: str = "",
    ) -> Optional[str]:
        """Two-phase generation for an entire source module.

        Phase 1 (Analysis): Ask the LLM to enumerate all code paths and
        produce a structured test plan — no code written yet. This forces
        the model to reason about exception handling, constructor signatures,
        and setup requirements before writing any tests.

        Phase 2 (Writing): Ask the LLM to implement the plan as a single
        consolidated test file with one class per entity.

        Parameters
        ----------
        module_dotpath:
            Dotted import path of the source module, e.g. ``"dev.cli.generate"``.
            Passed to prompt builders so the LLM uses the correct import path.

        Returns the cleaned test source code, or None if either phase fails.
        """
        templates = hypothesis_templates or {}

        # Phase 1: Analysis
        analysis_messages = [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": build_analysis_prompt(context, templates, module_dotpath)},
        ]
        plan = self._call_llm_raw(analysis_messages)
        if not plan:
            logger.warning("FabricStrategy: analysis phase returned no plan")
            return None
        logger.debug("FabricStrategy: analysis phase complete (%d chars)", len(plan))

        # Phase 2: Writing
        module_messages = [
            {"role": "system", "content": MODULE_SYSTEM_PROMPT},
            {"role": "user", "content": build_module_prompt(context, plan, templates, module_dotpath)},
        ]
        for attempt in range(max(1, self.max_retries)):
            code = self._call_llm(module_messages, attempt)
            if code is not None:
                return code
        return None

    # ------------------------------------------------------------------
    # Public API — per-entity generation (legacy, hypothesis-only fallback)
    # ------------------------------------------------------------------

    def generate(
        self,
        entity: TestableEntity,
        variant: GenerationVariant,
        context: AnalysisContext,
        hypothesis_template: str = "",
    ) -> Optional[str]:
        """Single-entity LLM generation (legacy mode).

        Kept for backwards compatibility with the orchestrator's per-entity
        fallback path. Prefer generate_module() for hybrid mode.
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

    def _call_llm_raw(self, messages: list) -> Optional[str]:
        """Make one LLM call and return the raw text (no length validation).

        Used for Phase 1 (analysis) where the output is prose, not code.
        """
        try:
            response = completion(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                api_key=self.api_key,
            )
            raw = response.choices[0].message.content
            return raw.strip() if raw else None
        except Exception as exc:
            logger.warning("FabricStrategy analysis call failed: %s", exc)
            return None

    def _call_llm(self, messages: list, attempt: int) -> Optional[str]:
        """Make one LLM completion call. Returns cleaned code or None."""
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
        """Strip markdown fences and validate minimum length."""
        if not raw:
            return None

        code = raw.strip()

        # Strip ``` fences if the LLM wrapped the output
        if code.startswith("```"):
            lines = code.splitlines()
            lines = lines[1:]  # drop opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines).strip()

        if len(code) < _MIN_CONTENT_LENGTH:
            return None

        return code
