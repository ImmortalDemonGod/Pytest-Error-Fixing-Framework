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
        """
        Initialize the GenerationOrchestrator with the strategies and context gatherer it will use.
        
        Parameters:
            strategy (Optional[HypothesisStrategy]): Strategy used to produce per-entity Hypothesis templates; defaults to a new `HypothesisStrategy` if not provided.
            fabric_strategy (Optional[FabricStrategy]): When provided, enables hybrid module-level generation using the fabric strategy.
            context_gatherer (Optional[ContextGatherer]): Optional gatherer used to obtain analysis context for fabric-driven generation.
        """
        self._strategy = strategy or HypothesisStrategy()
        self._fabric = fabric_strategy
        self._gatherer = context_gatherer
        self._parser = ModuleParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, source_path: Path, output_dir: Path) -> GenerationRequest:
        """
        Orchestrates parsing of a Python source file, generation of tests, and writing of outputs to the specified directory.
        
        Creates and starts a GenerationRequest for the parsed module, chooses a generation flow (hybrid module-level when a FabricStrategy is configured, otherwise per-entity Hypothesis generation), records per-entity or module-level GenerationAttempt results, and writes generated tests to output_dir. If an error occurs during generation, the request is marked failed and returned.
        
        Returns:
            GenerationRequest: The request containing aggregated generation attempts and final status (`complete` on success, `failed` on error).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        strategy_name = "hybrid" if self._fabric is not None else "hypothesis"
        config = GenerationConfig(output_dir=output_dir, strategy_name=strategy_name)

        _ensure_importable(source_path)

        parsed = self._parser.parse(source_path)
        request = GenerationRequest(parsed_module=parsed, config=config)
        request.start()

        context = self._gather_context(source_path)

        try:
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
        """
        Return an analysis context for hybrid generation or `None` when running hypothesis-only.
        
        Parameters:
            source_path (Path): Path to the Python source file for which context should be gathered.
        
        Returns:
            AnalysisContext or `None`: An AnalysisContext built from the provided source when a FabricStrategy is configured; `None` when no FabricStrategy is set. If a ContextGatherer was provided, its gathered context is returned; otherwise a context is created from the file's text.
        """
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
        """
        Orchestrates hybrid (Fabric + Hypothesis) module-level test generation, producing a consolidated module test file or falling back to per-entity hypothesis outputs.
        
        Collects per-entity Hypothesis templates, invokes the configured FabricStrategy once to generate module-level test code, and records a single GenerationAttempt on success. If FabricStrategy produces no code, falls back to writing per-entity Hypothesis outputs using the previously collected templates and records corresponding attempts on the request.
        
        Parameters:
            request (GenerationRequest): The active generation request to record attempts and read parsed module/configuration from.
            source_path (Path): Path to the source module being tested; used for module naming and writing output.
            context (AnalysisContext): Analysis context provided by the context gatherer, used by the FabricStrategy for module generation.
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
        """
        Write per-entity test files from pre-collected Hypothesis templates and record generation attempts.
        
        Parameters:
            request (GenerationRequest): The active generation request whose parsed module supplies entities and which will collect GenerationAttempt records.
            hypothesis_templates (dict[str, str]): Mapping from "{entity_name}.{variant_value}" to generated test code; entries with no mapping are treated as no output.
        
        Behavior:
            For each entity and variant in the parsed module, creates a GenerationAttempt and:
            - if corresponding template code exists, marks the attempt successful and writes the test file to request.config.output_dir (on write failure the attempt is marked failed);
            - if no template exists, marks the attempt skipped.
        """
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
        """
        Generate tests for each parsed entity and its variants using the configured Hypothesis strategy, write any produced code to the output directory, and record a GenerationAttempt for each variant.
        
        Parameters:
            request (GenerationRequest): The active generation request whose parsed_module supplies entities and which will collect GenerationAttempt records.
            context (Optional[AnalysisContext]): Optional analysis context; not required for hypothesis-only per-entity generation.
        """
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
    """
    Make the module at source_path importable by adding its parent directory and, if present, the nearest enclosing `src` directory to `sys.path`.
    
    Parameters:
        source_path (Path): Path to the Python source file whose importability should be ensured.
    """
    resolved = source_path.resolve()
    parts = resolved.parts

    def _add(path: str) -> None:
        """
        Insert the given path at the front of sys.path if it is not already present.
        
        Parameters:
            path (str): Filesystem path to add to Python import search paths; inserted at index 0.
        
        Notes:
            This function mutates the global `sys.path`.
        """
        if path not in sys.path:
            sys.path.insert(0, path)

    _add(str(resolved.parent))

    if "src" in parts:
        src_index = len(parts) - 1 - parts[::-1].index("src")
        src_dir = str(Path(*parts[: src_index + 1]))
        _add(src_dir)
