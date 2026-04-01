"""Unit tests for generate/optimizer.py — GenerationOrchestrator"""

import textwrap
from unittest.mock import MagicMock

import pytest

from src.dev.test_generator.core.models import AnalysisContext, GenerationVariant
from src.dev.test_generator.generate.optimizer import GenerationOrchestrator


SIMPLE_MODULE = textwrap.dedent("""\
    def add(a, b):
        return a + b

    def subtract(a, b):
        return a - b
""")

LONG_CODE = "# generated\n" + "x = 1\n" * 10  # > 50 chars so strategy accepts it


def _make_orchestrator(generate_returns=None):
    """Return an orchestrator with a mocked hypothesis strategy only."""
    strategy = MagicMock()
    strategy.generate.return_value = generate_returns
    return GenerationOrchestrator(strategy=strategy)


def _make_hybrid_orchestrator(hypothesis_returns=None, fabric_module_returns=None):
    """Return an orchestrator in hybrid mode with both strategies mocked.

    ``fabric_module_returns`` is the return value of ``fabric.generate_module()``.
    ``hypothesis_returns`` is the return value of ``hypothesis.generate()`` — used
    for collecting scaffolds (and as fallback when generate_module returns None).
    """
    hypothesis = MagicMock()
    hypothesis.generate.return_value = hypothesis_returns

    fabric = MagicMock()
    fabric.generate_module.return_value = fabric_module_returns

    gatherer = MagicMock()
    gatherer.gather.return_value = AnalysisContext.empty("def add(a, b): return a + b")

    return GenerationOrchestrator(
        strategy=hypothesis,
        fabric_strategy=fabric,
        context_gatherer=gatherer,
    ), hypothesis, fabric, gatherer


# ---------------------------------------------------------------------------
# Hypothesis-only mode
# ---------------------------------------------------------------------------


class TestRunReturnsCompletedRequest:
    def test_status_completed_when_strategy_succeeds(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text(SIMPLE_MODULE)
        out = tmp_path / "generated"

        orch = _make_orchestrator(generate_returns=LONG_CODE)
        request = orch.run(src, out)

        assert request.status == "completed"

    def test_output_dir_created(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "new_dir"

        orch = _make_orchestrator(generate_returns=LONG_CODE)
        orch.run(src, out)

        assert out.is_dir()

    def test_attempts_recorded_for_each_entity_variant(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text(SIMPLE_MODULE)
        out = tmp_path / "generated"

        orch = _make_orchestrator(generate_returns=LONG_CODE)
        request = orch.run(src, out)

        # add → [DEFAULT, BINARY_OP]; subtract → [DEFAULT]
        # so at least 3 attempts
        assert len(request.attempts) >= 3

    def test_successful_attempts_have_success_status(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch = _make_orchestrator(generate_returns=LONG_CODE)
        request = orch.run(src, out)

        assert len(request.successful_attempts) > 0

    def test_files_written_to_output_dir(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch = _make_orchestrator(generate_returns=LONG_CODE)
        orch.run(src, out)

        assert any(out.iterdir())


class TestRunWhenStrategyFails:
    def test_attempts_marked_skipped_when_no_output(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch = _make_orchestrator(generate_returns=None)
        request = orch.run(src, out)

        assert request.status == "completed"
        for a in request.attempts:
            assert a.status == "skipped"

    def test_no_files_written_when_strategy_returns_none(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"
        out.mkdir()

        orch = _make_orchestrator(generate_returns=None)
        orch.run(src, out)

        assert list(out.iterdir()) == []


class TestRunOnEmptyModule:
    def test_completed_with_zero_attempts(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("")  # empty module
        out = tmp_path / "generated"

        orch = _make_orchestrator()
        request = orch.run(src, out)

        assert request.status == "completed"
        assert request.attempts == []


# ---------------------------------------------------------------------------
# Hybrid mode — two-phase module-level generation
# ---------------------------------------------------------------------------


class TestHybridMode:
    def test_strategy_name_is_hybrid(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, *_ = _make_hybrid_orchestrator(fabric_module_returns=LONG_CODE)
        request = orch.run(src, out)

        assert request.config.strategy_name == "hybrid"

    def test_generate_module_called_once(self, tmp_path):
        """generate_module() must be called exactly once per run — not per entity."""
        src = tmp_path / "mymod.py"
        src.write_text(SIMPLE_MODULE)
        out = tmp_path / "generated"

        orch, _, fabric, _ = _make_hybrid_orchestrator(
            hypothesis_returns=LONG_CODE,
            fabric_module_returns=LONG_CODE,
        )
        orch.run(src, out)

        fabric.generate_module.assert_called_once()

    def test_one_consolidated_attempt_recorded_on_success(self, tmp_path):
        """Hybrid mode with a successful LLM call records exactly one attempt."""
        src = tmp_path / "mymod.py"
        src.write_text(SIMPLE_MODULE)
        out = tmp_path / "generated"

        orch, *_ = _make_hybrid_orchestrator(
            hypothesis_returns=LONG_CODE,
            fabric_module_returns=LONG_CODE,
        )
        request = orch.run(src, out)

        assert len(request.attempts) == 1
        assert request.attempts[0].status == "success"

    def test_module_attempt_entity_type_is_module(self, tmp_path):
        """The aggregate attempt tracks entity_type='module'."""
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, *_ = _make_hybrid_orchestrator(fabric_module_returns=LONG_CODE)
        request = orch.run(src, out)

        assert request.attempts[0].entity.entity_type == "module"

    def test_consolidated_file_named_after_source_stem(self, tmp_path):
        """Output file must be test_<source_stem>.py — not per-entity filenames."""
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, *_ = _make_hybrid_orchestrator(fabric_module_returns=LONG_CODE)
        orch.run(src, out)

        assert (out / "test_mymod.py").exists()

    def test_fabric_code_written_to_consolidated_file(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        fabric_code = LONG_CODE + "# fabric output"
        orch, *_ = _make_hybrid_orchestrator(fabric_module_returns=fabric_code)
        orch.run(src, out)

        written = (out / "test_mymod.py").read_text()
        assert written == fabric_code

    def test_hypothesis_templates_collected_before_generate_module(self, tmp_path):
        """generate_module() receives a non-empty templates dict when hypothesis produces output."""
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, hypothesis, fabric, _ = _make_hybrid_orchestrator(
            hypothesis_returns=LONG_CODE,
            fabric_module_returns=LONG_CODE,
        )
        orch.run(src, out)

        call_args = fabric.generate_module.call_args
        templates_arg = call_args[0][1]  # second positional: hypothesis_templates dict
        assert isinstance(templates_arg, dict)
        assert len(templates_arg) > 0

    def test_falls_back_to_per_entity_hypothesis_when_generate_module_returns_none(self, tmp_path):
        """When generate_module() returns None, write per-entity hypothesis files."""
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, hypothesis, fabric, _ = _make_hybrid_orchestrator(
            hypothesis_returns=LONG_CODE,
            fabric_module_returns=None,
        )
        request = orch.run(src, out)

        assert request.status == "completed"
        assert len(request.successful_attempts) > 0
        # Must be per-entity filenames, NOT test_mymod.py
        assert not (out / "test_mymod.py").exists()
        assert all(a.generated_code == LONG_CODE for a in request.successful_attempts)

    def test_skipped_when_both_strategies_fail(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, *_ = _make_hybrid_orchestrator(
            hypothesis_returns=None,
            fabric_module_returns=None,
        )
        request = orch.run(src, out)

        assert request.status == "completed"
        assert all(a.status == "skipped" for a in request.attempts)

    def test_context_gatherer_called_once_per_run(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def add(a, b): return a + b\ndef sub(a, b): return a - b\n")
        out = tmp_path / "generated"

        orch, _, _, gatherer = _make_hybrid_orchestrator(fabric_module_returns=LONG_CODE)
        orch.run(src, out)

        gatherer.gather.assert_called_once_with(src)

    def test_hypothesis_only_mode_when_no_fabric(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch = _make_orchestrator(generate_returns=LONG_CODE)
        request = orch.run(src, out)

        assert request.config.strategy_name == "hypothesis"
