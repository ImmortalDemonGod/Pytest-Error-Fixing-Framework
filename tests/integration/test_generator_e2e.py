"""
End-to-end integration tests for the test generation pipeline.

These tests call the *real* HypothesisStrategy (no mocks) against a small,
known source file.  They verify that:

1. The full pipeline (parse → select → hypothesis write → write files) runs
   without crashing.
2. Generated test files exist on disk and contain valid Python.
3. The generated tests can be collected and run by pytest.

Requirements: hypothesis[cli] and black must be installed in the active venv.
The tests are skipped automatically if the hypothesis CLI is unavailable.
"""

import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from src.dev.test_generator.generate.optimizer import GenerationOrchestrator
from src.dev.test_generator.generate.strategies.hypothesis import HypothesisStrategy

# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not HypothesisStrategy.is_available(),
        reason="hypothesis CLI not available in this venv",
    ),
]

# ---------------------------------------------------------------------------
# Target source file — small, self-contained, importable
# ---------------------------------------------------------------------------

_TARGET_SOURCE = textwrap.dedent("""\
    \"\"\"Simple math operations used as the E2E generation target.\"\"\"


    def add(a: int, b: int) -> int:
        return a + b


    def multiply(a: int, b: int) -> int:
        return a * b


    def negate(x: int) -> int:
        return -x
""")


@pytest.fixture(scope="module")
def target_file(tmp_path_factory):
    """Write the target source to a real file under a proper package structure."""
    root = tmp_path_factory.mktemp("e2e_src")
    src = root / "src" / "math_ops"
    src.mkdir(parents=True)
    mod = src / "simple.py"
    mod.write_text(_TARGET_SOURCE, encoding="utf-8")
    return mod


@pytest.fixture(scope="module")
def generated_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("e2e_out")


@pytest.fixture(scope="module")
def src_root(target_file):
    """The src/ directory that must be on PYTHONPATH for generated tests to import."""
    parts = target_file.resolve().parts
    if "src" in parts:
        src_index = len(parts) - 1 - parts[::-1].index("src")
        return str(Path(*parts[: src_index + 1]))
    return str(target_file.parent)


@pytest.fixture(scope="module")
def completed_request(target_file, generated_dir):
    """Run the full orchestration pipeline once and return the result."""
    strat = HypothesisStrategy(max_retries=2)
    orch = GenerationOrchestrator(strategy=strat)
    return orch.run(target_file, generated_dir)


# ---------------------------------------------------------------------------
# Pipeline-level assertions
# ---------------------------------------------------------------------------


class TestPipelineCompletes:
    def test_request_status_is_completed(self, completed_request):
        assert completed_request.status == "completed"

    def test_at_least_one_attempt_recorded(self, completed_request):
        assert len(completed_request.attempts) > 0

    def test_at_least_one_successful_attempt(self, completed_request):
        assert len(completed_request.successful_attempts) > 0

    def test_failed_attempts_is_zero(self, completed_request):
        # All generation failures should be "skipped", not "failed"
        assert completed_request.failed_attempts == []


# ---------------------------------------------------------------------------
# File-level assertions
# ---------------------------------------------------------------------------


class TestGeneratedFiles:
    def test_output_dir_is_not_empty(self, generated_dir):
        py_files = list(generated_dir.glob("test_*.py"))
        assert len(py_files) > 0

    def test_all_files_are_valid_python(self, generated_dir):
        for f in generated_dir.glob("test_*.py"):
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                pytest.fail(f"{f.name} is not valid Python: {exc}")

    def test_generated_files_start_with_test_prefix(self, generated_dir):
        for f in generated_dir.glob("*.py"):
            assert f.name.startswith("test_"), f"Unexpected file: {f.name}"

    def test_add_function_has_generated_test(self, generated_dir):
        names = {f.name for f in generated_dir.glob("test_*.py")}
        assert any("add" in n for n in names), f"No test for 'add' in {names}"

    def test_multiply_function_has_generated_test(self, generated_dir):
        names = {f.name for f in generated_dir.glob("test_*.py")}
        assert any("multiply" in n for n in names), f"No test for 'multiply' in {names}"


# ---------------------------------------------------------------------------
# Runnability — generated tests must be collectable by pytest
# ---------------------------------------------------------------------------


class TestGeneratedTestsRunnable:
    def _pytest_env(self, src_root: str) -> dict:
        """Build an env with the src root on PYTHONPATH so generated imports work."""
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_root}:{existing}" if existing else src_root
        return env

    def test_pytest_can_collect_generated_tests(self, generated_dir, src_root):
        """pytest --collect-only on the output dir must not error."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(generated_dir), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            env=self._pytest_env(src_root),
        )
        assert result.returncode in (0, 5), (
            f"pytest collection failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
        )  # 5 = no tests collected (acceptable if all skipped)

    def test_pytest_runs_generated_tests_without_import_error(self, generated_dir, src_root):
        """pytest must run without ImportError — modules must be importable."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(generated_dir), "-x", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            env=self._pytest_env(src_root),
        )
        assert "ImportError" not in result.stdout
        assert "ImportError" not in result.stderr
        assert "ModuleNotFoundError" not in result.stderr
