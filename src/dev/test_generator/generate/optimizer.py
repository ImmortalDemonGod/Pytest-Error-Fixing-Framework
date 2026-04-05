"""
GenerationOrchestrator — application layer.

Drives the end-to-end pipeline:
  parse → gather context → select variants → generate → write → record

Supports two modes:

  hypothesis-only (default):
    Calls ``hypothesis write`` per entity/variant. Produces multiple test
    files, one per entity. Fast and cheap.

  hybrid (two-phase module-level):
    1. Collects hypothesis scaffolds for all entities (for import/signature
       reference only).
    2. Calls FabricStrategy.generate_module() once for the whole module —
       Phase 1 analyzes all code paths and produces a structured plan, Phase 2
       writes a single consolidated test file with one TestClass per entity.
    3. Falls back to per-entity hypothesis output if the LLM fails entirely.

The two-phase module approach is the recommended mode. It substantially
reduces LLM hallucination by forcing analysis before writing, and produces a
single well-organized file instead of many disconnected ones.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from src.dev.test_generator.analyze.context import ContextGatherer
from src.dev.test_generator.analyze.extractor import select_variants
from src.dev.test_generator.analyze.parser import ModuleParser
from src.dev.test_generator.core.models import (
    AnalysisContext,
    GenerationAttempt,
    GenerationConfig,
    GenerationRequest,
    GenerationVariant,
    TestableEntity,
)
from src.dev.test_generator.generate.strategies.fabric import FabricStrategy
from src.dev.test_generator.generate.strategies.hypothesis import HypothesisStrategy
from src.dev.test_generator.output.writer import write_attempt, write_module_test

logger = logging.getLogger(__name__)


class GenerationOrchestrator:
    """Orchestrate test generation for a Python source file.

    Usage — hypothesis only (original behaviour)
    --------------------------------------------
    orch = GenerationOrchestrator()
    request = orch.run(source_path, output_dir)

    Usage — hybrid two-phase module mode (recommended)
    ---------------------------------------------------
    orch = GenerationOrchestrator(
        fabric_strategy=FabricStrategy(model="...", api_key=api_key),
        context_gatherer=ContextGatherer(),
    )
    request = orch.run(source_path, output_dir)
    """

    def __init__(
        self,
        strategy: Optional[HypothesisStrategy] = None,
        fabric_strategy: Optional[FabricStrategy] = None,
        context_gatherer: Optional[ContextGatherer] = None,
    ) -> None:
        self._strategy = strategy or HypothesisStrategy()
        self._fabric = fabric_strategy
        self._gatherer = context_gatherer
        self._parser = ModuleParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, source_path: Path, output_dir: Path) -> GenerationRequest:
        """Parse *source_path*, generate tests, write them to *output_dir*.

        Returns the completed GenerationRequest aggregate so the caller can
        inspect results.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        strategy_name = "hybrid" if self._fabric is not None else "hypothesis"
        config = GenerationConfig(output_dir=output_dir, strategy_name=strategy_name)

        _ensure_importable(source_path)

        parsed = self._parser.parse(source_path)
        request = GenerationRequest(parsed_module=parsed, config=config)
        request.start()

        try:
            context = self._gather_context(source_path)
            if context is not None and self._fabric is not None:
                self._process_module_level(request, source_path, context)
            else:
                self._process_per_entity(request, context)
        except Exception:
            logger.exception("Generation failed for %s", source_path)
            request.fail()
            return request

        request.complete()
        return request

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _gather_context(self, source_path: Path) -> Optional[AnalysisContext]:
        """Return AnalysisContext in hybrid mode, None in hypothesis-only mode."""
        if self._fabric is None:
            return None
        if self._gatherer is not None:
            return self._gatherer.gather(source_path)
        return AnalysisContext.empty(source_path.read_text(encoding="utf-8"))

    def _process_module_level(
        self,
        request: GenerationRequest,
        source_path: Path,
        context: AnalysisContext,
    ) -> None:
        """Two-phase module-level generation (hybrid mode).

        1. Collect hypothesis scaffolds for all entities — these give the LLM
           correct import paths and call signatures cheaply.
        2. Call generate_module() once — Phase 1 analyzes, Phase 2 writes.
        3. Write single consolidated test file.
        4. If the LLM fails, fall back to per-entity hypothesis output.
        """
        # Step 1: collect hypothesis templates for all entities
        hypothesis_templates: dict[str, str] = {}
        for entity in request.parsed_module.entities:
            for variant in select_variants(entity):
                template = self._strategy.generate(entity, variant)
                if template:
                    key = f"{entity.name}.{variant.value}"
                    hypothesis_templates[key] = template

        # Step 2: two-phase module-level LLM generation
        module_dotpath = request.parsed_module.module_dotpath
        code = self._fabric.generate_module(
            context, hypothesis_templates, module_dotpath
        )

        if code:
            # Represent as a single module-level attempt
            module_entity = TestableEntity(
                name=source_path.stem,
                module_path=request.parsed_module.module_dotpath,
                entity_type="module",
            )
            attempt = GenerationAttempt(
                entity=module_entity,
                variant=GenerationVariant.DEFAULT,
            )
            attempt.mark_success(code)
            try:
                write_module_test(code, source_path.stem, request.config.output_dir)
            except Exception as exc:
                attempt.mark_failed(str(exc))
            request.add_attempt(attempt)
        else:
            # LLM failed — fall back to individual hypothesis outputs
            self._process_per_entity_hypothesis_fallback(request, hypothesis_templates)

    def _process_per_entity_hypothesis_fallback(
        self,
        request: GenerationRequest,
        hypothesis_templates: dict[str, str],
    ) -> None:
        """Write whatever hypothesis templates we already collected."""
        for entity in request.parsed_module.entities:
            for variant in select_variants(entity):
                key = f"{entity.name}.{variant.value}"
                code = hypothesis_templates.get(key)
                attempt = GenerationAttempt(entity=entity, variant=variant)
                if code:
                    attempt.mark_success(code)
                    try:
                        write_attempt(attempt, request.config.output_dir)
                    except Exception as exc:
                        attempt.mark_failed(str(exc))
                else:
                    attempt.mark_skipped("hypothesis returned no output")
                request.add_attempt(attempt)

    def _process_per_entity(
        self,
        request: GenerationRequest,
        context: Optional[AnalysisContext],
    ) -> None:
        """Hypothesis-only per-entity generation (no fabric strategy)."""
        for entity in request.parsed_module.entities:
            for variant in select_variants(entity):
                attempt = GenerationAttempt(entity=entity, variant=variant)
                code = self._strategy.generate(entity, variant)
                if code:
                    attempt.mark_success(code)
                    try:
                        write_attempt(attempt, request.config.output_dir)
                    except Exception as exc:
                        attempt.mark_failed(str(exc))
                else:
                    attempt.mark_skipped("hypothesis returned no output")
                request.add_attempt(attempt)


def _ensure_importable(source_path: Path) -> None:
    """Add directories needed for ``hypothesis write`` to import the module."""
    resolved = source_path.resolve()
    parts = resolved.parts

    def _add(path: str) -> None:
        if path not in sys.path:
            sys.path.insert(0, path)

    _add(str(resolved.parent))

    if "src" in parts:
        src_index = len(parts) - 1 - parts[::-1].index("src")
        src_dir = str(Path(*parts[: src_index + 1]))
        _add(src_dir)
