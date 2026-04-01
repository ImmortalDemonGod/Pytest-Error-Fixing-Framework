"""
GenerationOrchestrator — application layer.

Drives the end-to-end pipeline:
  parse → gather context → select variants → generate → write → record

Supports two modes:
  - hypothesis-only (default): fast fuzz tests via ``hypothesis write``
  - hybrid: hypothesis generates a scaffold, FabricStrategy uses it as a
    template to produce high-quality example-based tests via an LLM.
    Falls back to the hypothesis scaffold if the LLM call fails.

This replaces the procedural generate_all_tests() / process_entities() loop
in scripts/hypot_test_gen.py with a proper application service that operates
on domain objects and delegates I/O to the output layer.
"""

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
    ParsedModule,
    TestableEntity,
)
from src.dev.test_generator.generate.strategies.fabric import FabricStrategy
from src.dev.test_generator.generate.strategies.hypothesis import HypothesisStrategy
from src.dev.test_generator.output.writer import write_attempt


class GenerationOrchestrator:
    """Orchestrate test generation for a Python source file.

    Usage — hypothesis only (original behaviour)
    --------------------------------------------
    orch = GenerationOrchestrator()
    request = orch.run(source_path, output_dir)

    Usage — hybrid (LLM-enhanced)
    ------------------------------
    from src.dev.test_generator.analyze.context import ContextGatherer
    from src.dev.test_generator.generate.strategies.fabric import FabricStrategy

    orch = GenerationOrchestrator(
        fabric_strategy=FabricStrategy(model="openrouter/openai/gpt-4o-mini",
                                       api_key=api_key),
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

        Returns the completed (or failed) GenerationRequest aggregate so the
        caller can inspect results.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        strategy_name = "hybrid" if self._fabric is not None else "hypothesis"
        config = GenerationConfig(output_dir=output_dir, strategy_name=strategy_name)

        # Ensure the module is importable before calling hypothesis write
        _ensure_importable(source_path)

        parsed = self._parser.parse(source_path)
        request = GenerationRequest(parsed_module=parsed, config=config)
        request.start()

        # Gather analysis context once for the whole run (only in hybrid mode)
        context = self._gather_context(source_path)

        try:
            self._process_all_entities(request, context)
        except Exception:
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
        # Hybrid mode but no gatherer: use empty context (source code only)
        return AnalysisContext.empty(source_path.read_text(encoding="utf-8"))

    def _process_all_entities(
        self, request: GenerationRequest, context: Optional[AnalysisContext]
    ) -> None:
        for entity in request.parsed_module.entities:
            variants = select_variants(entity)
            for variant in variants:
                attempt = GenerationAttempt(entity=entity, variant=variant)
                code = self._generate(entity, variant, context)
                if code:
                    attempt.mark_success(code)
                    try:
                        write_attempt(attempt, request.config.output_dir)
                    except Exception as exc:
                        attempt.mark_failed(str(exc))
                else:
                    attempt.mark_skipped("strategy returned no output")
                request.add_attempt(attempt)

    def _generate(
        self,
        entity: TestableEntity,
        variant: GenerationVariant,
        context: Optional[AnalysisContext],
    ) -> Optional[str]:
        """Run the appropriate generation strategy.

        Hypothesis-only mode: call hypothesis strategy directly.
        Hybrid mode:
          1. Run hypothesis to get a cheap scaffold/template.
          2. Pass template + context to FabricStrategy for LLM enhancement.
          3. If LLM fails, fall back to the hypothesis scaffold.
        """
        if context is None or self._fabric is None:
            return self._strategy.generate(entity, variant)

        # Hybrid: hypothesis scaffold → LLM enhancement → fallback
        template = self._strategy.generate(entity, variant) or ""
        code = self._fabric.generate(entity, variant, context, template)
        if code is not None:
            return code
        # LLM failed — use hypothesis output if we have it
        return template or None


def _ensure_importable(source_path: Path) -> None:
    """Add the directories needed for ``hypothesis write`` to import the module.

    Mirrors the original scripts/hypot_test_gen.py fix_pythonpath() logic:
    1. Always adds the file's immediate parent directory.
    2. If the path contains a ``src/`` segment, also adds the src/ directory —
       this is the root under which top-level packages live in a src-layout.
    """
    resolved = source_path.resolve()
    parts = resolved.parts

    def _add(path: str) -> None:
        if path not in sys.path:
            sys.path.insert(0, path)

    # 1. Always add the parent directory
    _add(str(resolved.parent))

    # 2. For src-layout: add the src/ directory so dotted module paths work
    if "src" in parts:
        src_index = len(parts) - 1 - parts[::-1].index("src")
        src_dir = str(Path(*parts[: src_index + 1]))
        _add(src_dir)
