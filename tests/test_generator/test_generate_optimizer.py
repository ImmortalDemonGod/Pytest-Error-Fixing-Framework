"""Unit tests for generate/optimizer.py — GenerationOrchestrator"""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.dev.test_generator.core.models import GenerationVariant
from src.dev.test_generator.generate.optimizer import GenerationOrchestrator


SIMPLE_MODULE = textwrap.dedent("""\
    def add(a, b):
        return a + b

    def subtract(a, b):
        return a - b
""")

LONG_CODE = "# generated\n" + "x = 1\n" * 10  # > 50 chars so strategy accepts it


def _make_orchestrator(generate_returns=None):
    """Return an orchestrator with a mocked strategy."""
    strategy = MagicMock()
    strategy.generate.return_value = generate_returns
    return GenerationOrchestrator(strategy=strategy)


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
