import sys
import types
from types import SimpleNamespace
from pathlib import Path
import click
import pytest

# Ensure any odd imports performed at module import time in the target module are stubbed.
# The run_cli module does: from src.dev.cli.generate import generate_command
# Provide a dummy module for that path so importing the target module won't fail.
_gen_mod = types.ModuleType("src.dev.cli.generate")
_gen_mod.generate_command = click.Command(name="generate")
sys.modules["src.dev.cli.generate"] = _gen_mod

# Now import the module under test using its dotted path.
import branch_fixer.utils.run_cli as run_cli


# Module-level fixtures (shared across test classes)
@pytest.fixture
def change_applier():
    return SimpleNamespace(name="change_applier")


@pytest.fixture
def test_file(tmp_path):
    p = tmp_path / "tests" / "test_example.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# test file\n")
    return p


class Test_get_version:
    def test_get_version_returns_metadata_version(self, monkeypatch):
        # Patch the importlib.metadata.version used inside the module
        monkeypatch.setattr(
            run_cli.importlib.metadata,
            "version",
            lambda pkg: "1.2.3",
        )
        assert run_cli.get_version() == "1.2.3"

    def test_get_version_package_not_installed_returns_fallback(self, monkeypatch):
        # Simulate PackageNotFoundError being raised
        def _raise(name):
            raise run_cli.importlib.metadata.PackageNotFoundError()

        monkeypatch.setattr(run_cli.importlib.metadata, "version", _raise)
        assert run_cli.get_version() == "unknown (package not installed)"


class Test_cli:
    def test_cli_is_click_group_and_has_fix_command(self):
        # cli should be a click Group and contain the 'fix' command registered by decorator
        assert hasattr(run_cli, "cli")
        assert isinstance(run_cli.cli, click.core.BaseCommand)
        # Commands are stored in the commands mapping on a Group
        assert "fix" in run_cli.cli.commands


class Test_fix:
    @pytest.fixture(autouse=True)
    def _no_logging(self, monkeypatch):
        # Avoid filesystem/logging side effects from setup_logging
        monkeypatch.setattr(run_cli, "setup_logging", lambda: None)

    def _make_fake_cli(self, *, setup_ok=True, service=None, run_fix_result=True, process_errors_result=0):
        """Helper to create a fake CLI instance."""
        class FakeCLI:
            def __init__(self):
                self._setup_called_with = None
                self.setup_ok = setup_ok
                self.cleanup_called = False
                self.service = service
                self._run_fix_result = run_fix_result
                self._process_errors_result = process_errors_result
                self.created_branches = set()

            def setup_components(self, config):
                self._setup_called_with = config
                return self.setup_ok

            def cleanup(self):
                self.cleanup_called = True

            def run_fix_workflow(self, error, interactive=False):
                self._last_run_error = error
                self._last_run_interactive = interactive
                return self._run_fix_result

            def process_errors(self, errors, interactive):
                self._last_process = (errors, interactive)
                return self._process_errors_result

        return FakeCLI()

    def _make_test_result(self, *, total_collected=0, failed=0, warnings=None, test_results=None, collection_errors=None):
        return SimpleNamespace(
            total_collected=total_collected,
            failed=failed,
            warnings=warnings or [],
            test_results=test_results or {},
            collection_errors=collection_errors or [],
        )

    def test_fix_setup_components_failure_returns_1(self, monkeypatch):
        fake_cli = self._make_fake_cli(setup_ok=False)
        monkeypatch.setattr(run_cli, "CLI", lambda: fake_cli)
        res = run_cli.fix.callback(
            api_key="key",
            max_retries=3,
            initial_temp=0.4,
            temp_increment=0.1,
            non_interactive=False,
            fast_run=False,
            test_path=None,
            test_function=None,
            cleanup_only=False,
            dev_force_success=False,
        )
        assert res == 1
        assert fake_cli._setup_called_with is not None
        assert getattr(fake_cli, "cleanup_called", False) is False

    def test_fix_cleanup_only_calls_cleanup_and_returns_0(self, monkeypatch):
        fake_cli = self._make_fake_cli(setup_ok=True)
        monkeypatch.setattr(run_cli, "CLI", lambda: fake_cli)
        res = run_cli.fix.callback(
            api_key="key",
            max_retries=3,
            initial_temp=0.4,
            temp_increment=0.1,
            non_interactive=False,
            fast_run=False,
            test_path=None,
            test_function=None,
            cleanup_only=True,
            dev_force_success=False,
        )
        assert res == 0
        assert fake_cli.cleanup_called is True

    def test_fix_no_service_returns_1(self, monkeypatch):
        fake_cli = self._make_fake_cli(setup_ok=True, service=None)
        monkeypatch.setattr(run_cli, "CLI", lambda: fake_cli)
        res = run_cli.fix.callback(
            api_key="key",
            max_retries=3,
            initial_temp=0.4,
            temp_increment=0.1,
            non_interactive=False,
            fast_run=False,
            test_path=None,
            test_function=None,
            cleanup_only=False,
            dev_force_success=False,
        )
        assert res == 1

    def test_fix_all_tests_passed_saves_session_and_returns_0(self, monkeypatch, tmp_path):
        # Prepare fake service and session_store
        test_result = self._make_test_result(total_collected=5, failed=0, warnings=["w1"])
        fake_test_runner = SimpleNamespace(run_test=lambda test_path, test_function: test_result)
        saved = {}
        class FakeSessionStore:
            def save_session(self, session):
                saved['session'] = session

        fake_service = SimpleNamespace(test_runner=fake_test_runner, session_store=None)
        fake_service.session_store = FakeSessionStore()

        fake_cli = self._make_fake_cli(setup_ok=True, service=fake_service)
        monkeypatch.setattr(run_cli, "CLI", lambda: fake_cli)

        # Provide a minimal FixSession and FixSessionState via the orchestrator module path
        orchestrator_mod = types.ModuleType("branch_fixer.orchestration.orchestrator")
        class FakeFixSession:
            def __init__(self):
                self.total_tests = 0
                self.failed_tests = None
                self.passed_tests = None
                self.state = None
                self.environment_info = {}
                self.warnings = []
        orchestrator_mod.FixSession = FakeFixSession
        orchestrator_mod.FixSessionState = SimpleNamespace(COMPLETED="completed")
        sys.modules["branch_fixer.orchestration.orchestrator"] = orchestrator_mod

        # Patch platform info for deterministic environment_info
        monkeypatch.setattr(run_cli.platform, "system", lambda: "TestOS")
        monkeypatch.setattr(run_cli.platform, "python_version", lambda: "3.9.test")

        res = run_cli.fix.callback(
            api_key="key",
            max_retries=3,
            initial_temp=0.4,
            temp_increment=0.1,
            non_interactive=False,
            fast_run=False,
            test_path=None,
            test_function=None,
            cleanup_only=False,
            dev_force_success=False,
        )
        assert res == 0
        assert "session" in saved
        sess = saved["session"]
        assert sess.failed_tests == 0
        assert sess.total_tests == 5
        assert sess.environment_info["os"] == "TestOS"
        assert sess.environment_info["python_version"] == "3.9.test"
        assert sess.warnings == ["w1"]

    def test_fix_failed_but_no_parsable_errors_returns_1(self, monkeypatch):
        # Setup service that reports failures
        test_result = self._make_test_result(total_collected=3, failed=2)
        fake_test_runner = SimpleNamespace(run_test=lambda test_path, test_function: test_result)
        fake_service = SimpleNamespace(test_runner=fake_test_runner)
        fake_cli = self._make_fake_cli(setup_ok=True, service=fake_service)
        monkeypatch.setattr(run_cli, "CLI", lambda: fake_cli)

        # Ensure process_pytest_results returns empty list
        err_proc_mod = types.ModuleType("branch_fixer.services.pytest.error_processor")
        err_proc_mod.process_pytest_results = lambda result: []
        sys.modules["branch_fixer.services.pytest.error_processor"] = err_proc_mod

        res = run_cli.fix.callback(
            api_key="key",
            max_retries=3,
            initial_temp=0.4,
            temp_increment=0.1,
            non_interactive=False,
            fast_run=False,
            test_path=None,
            test_function=None,
            cleanup_only=False,
            dev_force_success=False,
        )
        assert res == 1

    @pytest.mark.parametrize("workflow_result, expected_exit", [(True, 0), (False, 1)])
    def test_fix_fast_run_success_and_failure(self, monkeypatch, workflow_result, expected_exit):
        # service that reports one failure
        test_result = self._make_test_result(total_collected=1, failed=1)
        fake_test_runner = SimpleNamespace(run_test=lambda test_path, test_function: test_result)
        fake_service = SimpleNamespace(test_runner=fake_test_runner)
        fake_cli = self._make_fake_cli(setup_ok=True, service=fake_service, run_fix_result=workflow_result)
        monkeypatch.setattr(run_cli, "CLI", lambda: fake_cli)

        # Provide a simple error list via process_pytest_results
        def fake_process(result):
            return [SimpleNamespace(test_file=Path("tests/test_x.py"), test_function="test_x")]
        err_proc_mod = types.ModuleType("branch_fixer.services.pytest.error_processor")
        err_proc_mod.process_pytest_results = fake_process
        sys.modules["branch_fixer.services.pytest.error_processor"] = err_proc_mod

        res = run_cli.fix.callback(
            api_key="key",
            max_retries=1,
            initial_temp=0.4,
            temp_increment=0.1,
            non_interactive=True,
            fast_run=True,
            test_path=None,
            test_function=None,
            cleanup_only=False,
            dev_force_success=False,
        )
        assert res == expected_exit

    @pytest.mark.parametrize("process_return", [0, 1])
    def test_fix_delegate_to_process_errors(self, monkeypatch, process_return):
        test_result = self._make_test_result(total_collected=2, failed=2)
        fake_test_runner = SimpleNamespace(run_test=lambda test_path, test_function: test_result)
        fake_service = SimpleNamespace(test_runner=fake_test_runner)
        fake_cli = self._make_fake_cli(setup_ok=True, service=fake_service, process_errors_result=process_return)
        monkeypatch.setattr(run_cli, "CLI", lambda: fake_cli)

        # Return two fake errors
        err_proc_mod = types.ModuleType("branch_fixer.services.pytest.error_processor")
        err_proc_mod.process_pytest_results = lambda result: [SimpleNamespace(), SimpleNamespace()]
        sys.modules["branch_fixer.services.pytest.error_processor"] = err_proc_mod

        res = run_cli.fix.callback(
            api_key="key",
            max_retries=2,
            initial_temp=0.4,
            temp_increment=0.1,
            non_interactive=True,
            fast_run=False,
            test_path=None,
            test_function=None,
            cleanup_only=False,
            dev_force_success=False,
        )
        assert res == process_return


class Test_main:
    def test_main_calls_cli_callable(self, monkeypatch):
        # Replace run_cli.cli with a callable that returns sentinel
        monkeypatch.setattr(run_cli, "cli", lambda: "CALLED")
        assert run_cli.main() == "CALLED"