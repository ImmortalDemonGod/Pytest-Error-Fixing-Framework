"""Unit tests for generate/optimizer.py — GenerationOrchestrator"""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def _make_hybrid_orchestrator(hypothesis_returns=None, fabric_returns=None):
    """Return an orchestrator in hybrid mode with both strategies mocked."""
    hypothesis = MagicMock()
    hypothesis.generate.return_value = hypothesis_returns

    fabric = MagicMock()
    fabric.generate.return_value = fabric_returns

    gatherer = MagicMock()
    gatherer.gather.return_value = AnalysisContext.empty("def add(a, b): return a + b")

    return GenerationOrchestrator(
        strategy=hypothesis,
        fabric_strategy=fabric,
        context_gatherer=gatherer,
    ), hypothesis, fabric, gatherer


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
# Hybrid mode
# ---------------------------------------------------------------------------


class TestHybridMode:
    def test_strategy_name_is_hybrid(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, *_ = _make_hybrid_orchestrator(fabric_returns=LONG_CODE)
        request = orch.run(src, out)

        assert request.config.strategy_name == "hybrid"

    def test_fabric_output_used_when_successful(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        fabric_code = LONG_CODE + "# fabric output"
        orch, hypothesis, fabric, _ = _make_hybrid_orchestrator(
            hypothesis_returns=LONG_CODE,
            fabric_returns=fabric_code,
        )
        request = orch.run(src, out)

        assert request.status == "completed"
        assert all(
            a.generated_code == fabric_code
            for a in request.successful_attempts
        )

    def test_hypothesis_template_passed_to_fabric(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, hypothesis, fabric, _ = _make_hybrid_orchestrator(
            hypothesis_returns=LONG_CODE,
            fabric_returns=LONG_CODE,
        )
        orch.run(src, out)

        # fabric.generate must have been called with the hypothesis output
        call_kwargs = fabric.generate.call_args_list[0]
        assert call_kwargs[0][3] == LONG_CODE  # 4th positional: hypothesis_template

    def test_falls_back_to_hypothesis_when_fabric_returns_none(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, hypothesis, fabric, _ = _make_hybrid_orchestrator(
            hypothesis_returns=LONG_CODE,
            fabric_returns=None,  # fabric fails
        )
        request = orch.run(src, out)

        assert request.status == "completed"
        assert len(request.successful_attempts) > 0
        assert all(a.generated_code == LONG_CODE for a in request.successful_attempts)

    def test_skipped_when_both_strategies_fail(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch, *_ = _make_hybrid_orchestrator(
            hypothesis_returns=None,
            fabric_returns=None,
        )
        request = orch.run(src, out)

        assert request.status == "completed"
        assert all(a.status == "skipped" for a in request.attempts)

    def test_context_gatherer_called_once_per_run(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def add(a, b): return a + b\ndef sub(a, b): return a - b\n")
        out = tmp_path / "generated"

        orch, _, _, gatherer = _make_hybrid_orchestrator(fabric_returns=LONG_CODE)
        orch.run(src, out)

        gatherer.gather.assert_called_once_with(src)

    def test_hypothesis_only_mode_when_no_fabric(self, tmp_path):
        src = tmp_path / "mymod.py"
        src.write_text("def foo(): pass\n")
        out = tmp_path / "generated"

        orch = _make_orchestrator(generate_returns=LONG_CODE)
        request = orch.run(src, out)

        assert request.config.strategy_name == "hypothesis"
