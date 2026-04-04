import sys
from types import SimpleNamespace
from pathlib import Path
import pytest
from click.testing import CliRunner

import dev.cli.generate


@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    """
    Create a temporary Python source file named "module_under_test.py" containing a simple assignment and return its path.
    
    Parameters:
        tmp_path (Path): Pytest-provided temporary directory.
    
    Returns:
        Path: Path to the created "module_under_test.py" file (contains the text "x = 1\n").
    """
    p = tmp_path / "module_under_test.py"
    p.write_text("x = 1\n")
    return p


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """
    Create a subdirectory named "outdir" inside the given temporary path and return its Path.
    
    Parameters:
        tmp_path (Path): Base temporary directory in which to create the "outdir" folder.
    
    Returns:
        Path: Path to the newly created "outdir" directory.
    """
    d = tmp_path / "outdir"
    d.mkdir()
    return d


@pytest.fixture
def echo_calls(monkeypatch):
    """
    Replace dev.cli.generate.click.echo with a recorder that captures all calls.
    
    Returns:
        calls (list): List of tuples (message, kwargs) for each recorded echo invocation.
    """
    calls = []

    def fake_echo(message="", **kwargs):
        """
        Record an echo invocation by appending a tuple of (message, kwargs) to the shared `calls` list.
        
        Parameters:
            message (str): The message that would be echoed.
            **kwargs: Keyword arguments forwarded from the original echo call (for example `err=True`).
        """
        calls.append((message, kwargs))

    monkeypatch.setattr(dev.cli.generate.click, "echo", fake_echo)
    return calls


@pytest.fixture
def cli_runner():
    """
    Create a Click CliRunner suitable for invoking the command under test in unit tests.
    
    Returns:
        CliRunner: A fresh CliRunner instance for invoking Click commands and capturing output.
    """
    return CliRunner()


class TestGenerateCommand:
    def test_happy_path_prints_summary_and_returns(
        self, monkeypatch, source_file, output_dir, echo_calls
    ):
        # Arrange: Hypothesis available and orchestrator returning a successful request
        class FakeHypothesisStrategy:
            @classmethod
            def is_available(cls):
                """
                Check whether the strategy is available on the current system.
                
                Returns:
                    `True` if the strategy is available, `False` otherwise.
                """
                return True

            def __init__(self):
                # marker to identify instance
                """
                Initialize the strategy instance with an internal identification marker.
                
                Sets a private `_marker` attribute used to identify this HypothesisStrategy instance.
                """
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
                """
                Initialize the object with a generation strategy.
                
                Parameters:
                    strategy: Strategy instance used to drive generation; stored on the instance as `self.strategy`.
                """
                self.strategy = strategy

            def run(self, source_path, output_dir):
                # validate that paths are Path instances
                """
                Run the generation process for a given source file and place outputs in the specified directory.
                
                Parameters:
                    source_path (Path): Path to the Python source file to generate tests for.
                    output_dir (Path): Directory where generated test files should be written.
                
                Returns:
                    request (object): Result object describing the generation run, including fields such as
                    `attempts`, `successful_attempts`, `failed_attempts`, and `status`.
                """
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
                """
                Check whether the strategy is available on the current system.
                
                Returns:
                    `True` if the strategy is available, `False` otherwise.
                """
                return True

            def __init__(self):
                """
                Create a new instance without performing any initialization.
                """
                pass

        request = SimpleNamespace(
            successful_attempts=[1],
            failed_attempts=[1, 2],
            attempts=[SimpleNamespace(status="ok")],
            status="failed",
        )

        class FakeOrchestrator:
            def __init__(self, strategy):
                """
                Initialize the object with a generation strategy.
                
                Parameters:
                    strategy: Instance that provides the generation strategy used by this object.
                """
                self.strategy = strategy

            def run(self, source_path, output_dir):
                """
                Run the generation process for a source file and place outputs in the given directory.
                
                Parameters:
                    source_path (Path): Path to the source module to generate tests for.
                    output_dir (Path): Directory where generated tests should be written.
                
                Returns:
                    request: An object summarizing the generation run. Expected attributes:
                        - status (str): Overall outcome, e.g. "success" or "failed".
                        - successful_attempts (list): Items representing successful generation attempts.
                        - failed_attempts (list): Items representing failed attempts.
                        - attempts (list): All attempt objects; each attempt is expected to have a `status` attribute (e.g. "ok", "skipped").
                """
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
                """
                Check whether the external 'hypothesis' CLI is available in the environment.
                
                @returns
                    `True` if the 'hypothesis' CLI is available, `False` otherwise.
                """
                return False

            def __init__(self):
                """
                Create a new instance without performing any initialization.
                """
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
                """
                Check whether the strategy is available on the current system.
                
                Returns:
                    `True` if the strategy is available, `False` otherwise.
                """
                return True

            def __init__(self):
                """
                Register the new instance by appending it to the module-level `instances` list.
                """
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
                """
                Record the provided strategy instance for later inspection.
                
                Parameters:
                    strategy: The strategy instance passed into the constructor; stored in the shared `received` mapping under the "strategy" key.
                """
                received["strategy"] = strategy

            def run(self, source_path, output_dir):
                """
                Run the generation process for a source file and place outputs in the given directory.
                
                Parameters:
                    source_path (Path): Path to the source module to generate tests for.
                    output_dir (Path): Directory where generated tests should be written.
                
                Returns:
                    request: An object summarizing the generation run. Expected attributes:
                        - status (str): Overall outcome, e.g. "success" or "failed".
                        - successful_attempts (list): Items representing successful generation attempts.
                        - failed_attempts (list): Items representing failed attempts.
                        - attempts (list): All attempt objects; each attempt is expected to have a `status` attribute (e.g. "ok", "skipped").
                """
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
                """
                Check whether the strategy is available on the current system.
                
                Returns:
                    `True` if the strategy is available, `False` otherwise.
                """
                return True

            def __init__(self):
                """
                Create a new instance without performing any initialization.
                """
                pass

        request = SimpleNamespace(
            successful_attempts=[1],
            failed_attempts=[],
            attempts=[SimpleNamespace(status="ok")],
            status="success",
        )

        class FakeOrchestrator:
            def __init__(self, strategy):
                """
                Initialize the orchestrator with the strategy used to drive generation.
                
                Parameters:
                    strategy: The generation strategy instance the orchestrator will use to perform test generation.
                """
                pass

            def run(self, source_path, output_dir):
                # ensure click.Path converted to Path and values passed through
                """
                Execute generation for a source file into an output directory.
                
                Parameters:
                    source_path (Path): Path to the Python source file to generate tests for.
                    output_dir (Path): Directory where generated tests should be written.
                
                Returns:
                    request: An object summarizing the generation outcome. Expected attributes include
                        `status` (e.g., "success" or "failed"), `successful_attempts` (list), 
                        `failed_attempts` (list), and `attempts` (iterable of attempt objects with a
                        `status` attribute).
                """
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
                """
                Check whether the strategy is available on the current system.
                
                Returns:
                    `True` if the strategy is available, `False` otherwise.
                """
                return True

            def __init__(self):
                """
                Create a new instance without performing any initialization.
                """
                pass

        request = SimpleNamespace(
            successful_attempts=[],
            failed_attempts=[],
            attempts=[object(), object()],
            status="success",
        )

        class FakeOrchestrator:
            def __init__(self, strategy):
                """
                Initialize the orchestrator with the strategy used to drive generation.
                
                Parameters:
                    strategy: The generation strategy instance the orchestrator will use to perform test generation.
                """
                pass

            def run(self, source_path, output_dir):
                """
                Run the generation process for a source file and place outputs in the given directory.
                
                Parameters:
                    source_path (Path): Path to the source module to generate tests for.
                    output_dir (Path): Directory where generated tests should be written.
                
                Returns:
                    request: An object summarizing the generation run. Expected attributes:
                        - status (str): Overall outcome, e.g. "success" or "failed".
                        - successful_attempts (list): Items representing successful generation attempts.
                        - failed_attempts (list): Items representing failed attempts.
                        - attempts (list): All attempt objects; each attempt is expected to have a `status` attribute (e.g. "ok", "skipped").
                """
                return request

        monkeypatch.setattr(dev.cli.generate, "HypothesisStrategy", FakeHypothesisStrategy)
        monkeypatch.setattr(dev.cli.generate, "GenerationOrchestrator", FakeOrchestrator)

        # Accessing a.status should raise AttributeError which should propagate
        with pytest.raises(AttributeError):
            dev.cli.generate.generate_command.callback(source_file, output_dir, "hypothesis")