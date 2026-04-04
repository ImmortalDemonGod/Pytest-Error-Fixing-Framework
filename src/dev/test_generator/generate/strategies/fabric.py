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
        """
        Initialize FabricStrategy with model and generation settings.
        
        Parameters:
            model (str): LiteLLM model identifier used for completion calls.
            api_key (Optional[str]): Provider API key to pass to LiteLLM; may be `None` for local models.
            temperature (float): Sampling temperature controlling response variability.
            max_retries (int): Maximum number of LLM call attempts per generation phase.
        """
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
        """
        Generate tests for an entire source module using a two-phase LLM workflow.
        
        Performs an analysis phase to produce a structured test plan, then a writing phase that emits a single consolidated test file implementing that plan. If the analysis yields no plan or code generation fails after retries, returns None.
        
        Parameters:
            context (AnalysisContext): Analysis context describing the module and entities to test.
            hypothesis_templates (dict, optional): Mapping of hypothesis template names to template text used by prompt builders.
            module_dotpath (str, optional): Dotted import path of the target module (e.g. "dev.cli.generate"); used so generated tests import the module correctly.
        
        Returns:
            Optional[str]: Cleaned test source code as a single string, or `None` if generation failed.
        """
        templates = hypothesis_templates or {}

        # Phase 1: Analysis
        analysis_messages = [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_analysis_prompt(context, templates, module_dotpath),
            },
        ]
        plan = self._call_llm_raw(analysis_messages)
        if not plan:
            logger.warning("FabricStrategy: analysis phase returned no plan")
            return None
        logger.debug("FabricStrategy: analysis phase complete (%d chars)", len(plan))

        # Phase 2: Writing
        module_messages = [
            {"role": "system", "content": MODULE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_module_prompt(
                    context, plan, templates, module_dotpath
                ),
            },
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
        """
        Generate pytest tests for a single testable entity using the configured LLM.
        
        This legacy, per-entity generation path is retained for backward compatibility; prefer `generate_module()` for the two-phase module-level workflow.
        
        Parameters:
            hypothesis_template (str): Optional Hypothesis template string to include in the prompt.
        
        Returns:
            generated_code (Optional[str]): Cleaned generated test source as a string, or `None` if generation failed.
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
        """
        Call the LLM with the provided message list and return the trimmed textual response.
        
        Returns:
            Optional[str]: The response content with surrounding whitespace removed, or `None` if the response is empty or the call fails.
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
        """
        Perform a single LLM completion request and return cleaned generated code.
        
        Parameters:
            messages (list): Conversation messages to send to the model.
            attempt (int): Zero-based attempt index (used for logging).
        
        Returns:
            str: Cleaned generated code if the model produced valid output, `None` otherwise.
        """
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
        """
        Clean and validate LLM-generated code by removing surrounding whitespace and Markdown code fences, and enforcing a minimum content length.
        
        Parameters:
        	raw (Optional[str]): The raw text produced by the LLM, which may include Markdown code fences (e.g., ```python```).
        
        Returns:
        	clean_code (Optional[str]): The cleaned code string if it meets the minimum length requirement, `None` otherwise.
        """
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
