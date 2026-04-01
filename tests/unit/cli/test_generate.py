import sys
from types import SimpleNamespace
from pathlib import Path
import pytest
from click.testing import CliRunner

import dev.cli.generate


@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    p = tmp_path / "module_under_test.py"
    p.write_text("x = 1\n")
    return p


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "outdir"
    d.mkdir()
    return d


@pytest.fixture
def echo_calls(monkeypatch):
    calls = []

    def fake_echo(message="", **kwargs):
        calls.append((message, kwargs))

    monkeypatch.setattr(dev.cli.generate.click, "echo", fake_echo)
    return calls


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestGenerateCommand:
    def test_happy_path_prints_summary_and_returns(
        self, monkeypatch, source_file, output_dir, echo_calls
    ):
        # Arrange: Hypothesis available and orchestrator returning a successful request
        class FakeHypothesisStrategy:
            @classmethod
            def is_available(cls):
                return True

            def __init__(self):
                # marker to identify instance
                self._marker = "hypothesis-instance"

        request = SimpleNamespace(
            successful_attempts=[1, 2],
            failed_attempts=[],
            attempts=[
                SimpleNamespace(status="skipped"),
                SimpleNamespace(status="ok"),
                SimpleNamespace(status="skipped"),
            ],
            status="success",
        )

        class FakeOrchestrator:
            def __init__(self, strategy):
                # record that init received the strategy instance
                self.strategy = strategy

            def run(self, source_path, output_dir):
                # validate that paths are Path instances
                assert isinstance(source_path, Path)
                assert isinstance(output_dir, Path)
                return request

        monkeypatch.setattr(
            dev.cli.generate, "HypothesisStrategy", FakeHypothesisStrategy
        )
        monkeypatch.setattr(
            dev.cli.generate, "GenerationOrchestrator", FakeOrchestrator
        )

        # Act: call the underlying callback function directly
        result = dev.cli.generate.generate_command.callback(
            source_file, output_dir, "hypothesis"
        )

        # Assert: function returned None and printed the expected messages
        assert result is None
        # Expect first two messages and final summary
        assert any(
            f"Generating tests for: {source_file}" == msg for msg, _ in echo_calls
        )
        assert any(
            f"Output directory: {output_dir}" == msg for msg, _ in echo_calls
        )
        assert any(
            msg.startswith("\nDone. 2 generated, 0 failed, 2 skipped")
            for msg, _ in echo_calls
        )

    def test_failed_request_causes_exit_1(self, monkeypatch, source_file, output_dir, echo_calls):
        # Arrange: Hypothesis available and orchestrator returning a failed request
        class FakeHypothesisStrategy:
            @classmethod
            def is_available(cls):
                return True

            def __init__(self):
                pass

        request = SimpleNamespace(
            successful_attempts=[1],
            failed_attempts=[1, 2],
            attempts=[SimpleNamespace(status="ok")],
            status="failed",
        )

        class FakeOrchestrator:
            def __init__(self, strategy):
                self.strategy = strategy

            def run(self, source_path, output_dir):
                return request

        monkeypatch.setattr(
            dev.cli.generate, "HypothesisStrategy", FakeHypothesisStrategy
        )
        monkeypatch.setattr(
            dev.cli.generate, "GenerationOrchestrator", FakeOrchestrator
        )

        # Act / Assert: SystemExit with code 1 is raised
        with pytest.raises(SystemExit) as exc:
            dev.cli.generate.generate_command.callback(source_file, output_dir, "hypothesis")
        assert exc.value.code == 1

        # Assert summary was printed before exit
        assert any(
            msg.startswith("\nDone. 1 generated, 2 failed, 0 skipped")
            for msg, _ in echo_calls
        )

    def test_hypothesis_unavailable_exits_with_message(self, monkeypatch, source_file, output_dir, echo_calls):
        # Arrange: HypothesisStrategy reports unavailable
        class FakeHypothesisStrategy:
            @classmethod
            def is_available(cls):
                return False

            def __init__(self):
                pass

        monkeypatch.setattr(
            dev.cli.generate, "HypothesisStrategy", FakeHypothesisStrategy
        )

        # Act / Assert: Should exit with code 1 and print the expected error to stderr (captured via echo_calls)
        with pytest.raises(SystemExit) as exc:
            dev.cli.generate.generate_command.callback(source_file, output_dir, "hypothesis")
        assert exc.value.code == 1

        # Check that the error message was printed with err=True
        assert any(
            "Error: 'hypothesis' CLI not found." in msg and kwargs.get("err", False)
            for msg, kwargs in echo_calls
        )

    @pytest.mark.parametrize("strategy_value", ["unknown", "not_supported"])
    def test_unknown_strategy_exits_with_message(self, strategy_value, source_file, output_dir, echo_calls):
        # No need to patch HypothesisStrategy since branch taken before that
        with pytest.raises(SystemExit) as exc:
            dev.cli.generate.generate_command.callback(source_file, output_dir, strategy_value)
        assert exc.value.code == 1

        # Error message should mention the unknown strategy and be marked err=True
        assert any(
            f"Unknown strategy: {strategy_value}" == msg and kwargs.get("err", False)
            for msg, kwargs in echo_calls
        )

    def test_orchestrator_constructed_with_hypothesis_strategy_instance(self, monkeypatch, source_file, output_dir):
        # Arrange: capture the instance created by HypothesisStrategy and the strategy passed to orchestrator
        instances = []

        class FakeHypothesisStrategy:
            @classmethod
            def is_available(cls):
                return True

            def __init__(self):
                instances.append(self)

        received = {}

        request = SimpleNamespace(
            successful_attempts=[],
            failed_attempts=[],
            attempts=[],
            status="success",
        )

        class FakeOrchestrator:
            def __init__(self, strategy):
                received["strategy"] = strategy

            def run(self, source_path, output_dir):
                return request

        monkeypatch.setattr(dev.cli.generate, "HypothesisStrategy", FakeHypothesisStrategy)
        monkeypatch.setattr(dev.cli.generate, "GenerationOrchestrator", FakeOrchestrator)
        # Act
        dev.cli.generate.generate_command.callback(source_file, output_dir, "hypothesis")
        # Assert: orchestrator received the exact instance created by HypothesisStrategy()
        assert "strategy" in received
        assert instances, "HypothesisStrategy should have been instantiated"
        assert received["strategy"] is instances[0]

    def test_cli_invocation_with_runner_respects_click_path_validation(self, monkeypatch, cli_runner, tmp_path):
        # Arrange: non-existent source path should fail validation
        non_existent = tmp_path / "does_not_exist.py"
        result = cli_runner.invoke(
            dev.cli.generate.generate_command,
            ["--source-path", str(non_existent), "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code != 0
        assert "does not exist" in result.output

        # Now create a real file and patch orchestrator/hypothesis to succeed
        real_file = tmp_path / "real.py"
        real_file.write_text("y = 2\n")
        outdir = tmp_path / "out"
        outdir.mkdir()

        class FakeHypothesisStrategy:
            @classmethod
            def is_available(cls):
                return True

            def __init__(self):
                pass

        request = SimpleNamespace(
            successful_attempts=[1],
            failed_attempts=[],
            attempts=[SimpleNamespace(status="ok")],
            status="success",
        )

        class FakeOrchestrator:
            def __init__(self, strategy):
                pass

            def run(self, source_path, output_dir):
                # ensure click.Path converted to Path and values passed through
                assert isinstance(source_path, Path)
                assert isinstance(output_dir, Path)
                return request

        monkeypatch.setattr(dev.cli.generate, "HypothesisStrategy", FakeHypothesisStrategy)
        monkeypatch.setattr(dev.cli.generate, "GenerationOrchestrator", FakeOrchestrator)

        result2 = cli_runner.invoke(
            dev.cli.generate.generate_command,
            ["--source-path", str(real_file), "--output-dir", str(outdir)],
        )
        assert result2.exit_code == 0
        assert f"Generating tests for: {real_file}" in result2.output
        assert "Done. 1 generated, 0 failed, 0 skipped" in result2.output

    def test_attempts_without_status_raises_attribute_error(self, monkeypatch, source_file, output_dir):
        # Arrange: orchestrator returns attempts items missing .status attribute
        class FakeHypothesisStrategy:
            @classmethod
            def is_available(cls):
                return True

            def __init__(self):
                pass

        request = SimpleNamespace(
            successful_attempts=[],
            failed_attempts=[],
            attempts=[object(), object()],
            status="success",
        )

        class FakeOrchestrator:
            def __init__(self, strategy):
                pass

            def run(self, source_path, output_dir):
                return request

        monkeypatch.setattr(dev.cli.generate, "HypothesisStrategy", FakeHypothesisStrategy)
        monkeypatch.setattr(dev.cli.generate, "GenerationOrchestrator", FakeOrchestrator)

        # Accessing a.status should raise AttributeError which should propagate
        with pytest.raises(AttributeError):
            dev.cli.generate.generate_command.callback(source_file, output_dir, "hypothesis")