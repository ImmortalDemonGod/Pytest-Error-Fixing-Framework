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
    """
    Create a temporary package layout and write the module source file used by tests.
    
    Parameters:
        tmp_path_factory: pytest tmp_path_factory fixture used to create a temporary root directory.
    
    Returns:
        Path: Path to the written module file (temporary_root/e2e_src/src/math_ops/simple.py).
    """
    root = tmp_path_factory.mktemp("e2e_src")
    src = root / "src" / "math_ops"
    src.mkdir(parents=True)
    mod = src / "simple.py"
    mod.write_text(_TARGET_SOURCE, encoding="utf-8")
    return mod


@pytest.fixture(scope="module")
def generated_dir(tmp_path_factory):
    """
    Create and return a temporary output directory for generated tests.
    
    Returns:
        Path: Path to the created temporary directory named "e2e_out".
    """
    return tmp_path_factory.mktemp("e2e_out")


@pytest.fixture(scope="module")
def src_root(target_file):
    """
    Compute the filesystem path that should be added to PYTHONPATH so generated tests can import the target module.
    
    Parameters:
        target_file (Path): Path to the target Python file.
    
    Returns:
        str: Absolute path to the directory to add to PYTHONPATH. If a directory named "src" exists in the resolved path of `target_file`, returns that "src" directory; otherwise returns the parent directory of `target_file`.
    """
    parts = target_file.resolve().parts
    if "src" in parts:
        src_index = len(parts) - 1 - parts[::-1].index("src")
        return str(Path(*parts[: src_index + 1]))
    return str(target_file.parent)


@pytest.fixture(scope="module")
def completed_request(target_file, generated_dir):
    """
    Execute the generation orchestrator once for the given target file and output directory.
    
    Returns:
        result: An object representing the completed generation request, providing at least the attributes `status`, `attempts`, `successful_attempts`, and `failed_attempts`.
    """
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
        """
        Verify the pipeline recorded no failed generation attempts.
        
        Checks that `completed_request.failed_attempts` is an empty list (generation failures are treated as skipped).
        
        Parameters:
            completed_request: The orchestration result object returned by the generation pipeline fixture.
        """
        assert completed_request.failed_attempts == []


# ---------------------------------------------------------------------------
# File-level assertions
# ---------------------------------------------------------------------------


class TestGeneratedFiles:
    def test_output_dir_is_not_empty(self, generated_dir):
        """
        Asserts that the generated output directory contains at least one file whose name starts with `test_`.
        
        Parameters:
            generated_dir (Path): Path to the directory where generated test files are written.
        """
        py_files = list(generated_dir.glob("test_*.py"))
        assert len(py_files) > 0

    def test_all_files_are_valid_python(self, generated_dir):
        """
        Validates that every generated test file is syntactically valid Python.
        
        Parses each file in `generated_dir` matching `test_*.py` using the Python AST parser and fails the test if any file raises a `SyntaxError`, including the filename and exception message in the failure.
        
        Parameters:
            generated_dir (Path): Directory containing generated test files to validate.
        """
        for f in generated_dir.glob("test_*.py"):
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                pytest.fail(f"{f.name} is not valid Python: {exc}")

    def test_generated_files_start_with_test_prefix(self, generated_dir):
        """
        Asserts that every Python file in the generated output directory is prefixed with "test_".
        
        Parameters:
            generated_dir (Path): Directory containing the generated `.py` files to check.
        """
        for f in generated_dir.glob("*.py"):
            assert f.name.startswith("test_"), f"Unexpected file: {f.name}"

    def test_add_function_has_generated_test(self, generated_dir):
        """
        Asserts that at least one generated test filename references the `add` function.
        
        Parameters:
        	generated_dir (Path): Directory containing generated test files; the test searches files matching `test_*.py` and requires at least one filename to contain the substring `"add"`.
        """
        names = {f.name for f in generated_dir.glob("test_*.py")}
        assert any("add" in n for n in names), f"No test for 'add' in {names}"

    def test_multiply_function_has_generated_test(self, generated_dir):
        """
        Asserts that at least one generated test filename references the "multiply" function.
        
        Parameters:
            generated_dir (Path): Directory containing generated test files.
        
        Raises:
            AssertionError: If no filename in the directory contains the substring "multiply".
        """
        names = {f.name for f in generated_dir.glob("test_*.py")}
        assert any("multiply" in n for n in names), f"No test for 'multiply' in {names}"


# ---------------------------------------------------------------------------
# Runnability — generated tests must be collectable by pytest
# ---------------------------------------------------------------------------


class TestGeneratedTestsRunnable:
    def _pytest_env(self, src_root: str) -> dict:
        """
        Create an environment mapping with src_root prepended to PYTHONPATH.
        
        Parameters:
            src_root (str): Path to the directory to prepend to PYTHONPATH.
        
        Returns:
            dict: A copy of the current environment with `PYTHONPATH` updated so `src_root`
            is first (existing `PYTHONPATH` is preserved and appended if present).
        """
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_root}:{existing}" if existing else src_root
        return env

    def test_pytest_can_collect_generated_tests(self, generated_dir, src_root):
        """
        Verify that pytest can collect tests from the generated test directory without error.
        
        Runs `python -m pytest <generated_dir> --collect-only -q` with `PYTHONPATH` set to include `src_root`
        and asserts the process exits with code `0` or `5` (`5` means no tests collected). On failure,
        the assertion message includes truncated `stdout` and `stderr`.
        """
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
        """
        Verify that running pytest on the generated tests does not produce import-related errors.
        
        Asserts that neither `ImportError` nor `ModuleNotFoundError` appears in pytest's stdout or stderr when executing the generated test suite with `src_root` on `PYTHONPATH`.
        """
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(generated_dir), "-x", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            env=self._pytest_env(src_root),
        )
        assert "ImportError" not in result.stdout
        assert "ImportError" not in result.stderr
        assert "ModuleNotFoundError" not in result.stderr
