"""
GenerationOrchestrator — application layer.

Drives the end-to-end pipeline:
  parse → select variants → generate (via strategy) → write → record in aggregate

This replaces the procedural generate_all_tests() / process_entities() loop
in scripts/hypot_test_gen.py with a proper application service that operates
on domain objects and delegates I/O to the output layer.
"""

import sys
from pathlib import Path
from typing import Optional

from src.dev.test_generator.analyze.extractor import select_variants
from src.dev.test_generator.analyze.parser import ModuleParser
from src.dev.test_generator.core.models import (
    GenerationAttempt,
    GenerationConfig,
    GenerationRequest,
    ParsedModule,
)
from src.dev.test_generator.generate.strategies.hypothesis import HypothesisStrategy
from src.dev.test_generator.output.writer import write_attempt


class GenerationOrchestrator:
    """Orchestrate test generation for a Python source file.

    Usage
    -----
    orchestrator = GenerationOrchestrator()
    request = orchestrator.run(source_path, output_dir)
    print(request.successful_attempts)  # list of GenerationAttempt
    """

    def __init__(self, strategy: Optional[HypothesisStrategy] = None) -> None:
        self._strategy = strategy or HypothesisStrategy()
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
        config = GenerationConfig(output_dir=output_dir, strategy_name="hypothesis")

        # Ensure the module is importable before calling hypothesis write
        _ensure_importable(source_path)

        parsed = self._parser.parse(source_path)
        request = GenerationRequest(parsed_module=parsed, config=config)
        request.start()

        try:
            self._process_all_entities(request)
        except Exception:
            request.fail()
            return request

        request.complete()
        return request

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _process_all_entities(self, request: GenerationRequest) -> None:
        for entity in request.parsed_module.entities:
            variants = select_variants(entity)
            for variant in variants:
                attempt = GenerationAttempt(entity=entity, variant=variant)
                code = self._strategy.generate(entity, variant)
                if code:
                    attempt.mark_success(code)
                    try:
                        write_attempt(attempt, request.config.output_dir)
                    except Exception as exc:
                        attempt.mark_failed(str(exc))
                else:
                    attempt.mark_skipped("strategy returned no output")
                request.add_attempt(attempt)


def _ensure_importable(source_path: Path) -> None:
    """Add the source file's package root (or directory) to sys.path."""
    resolved = source_path.resolve()
    parent = resolved.parent
    # Walk up to find the top-level package root
    while (parent / "__init__.py").exists():
        parent = parent.parent
    path_str = str(parent)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
