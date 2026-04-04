"""
ContextGatherer — infrastructure layer.

Runs mypy, ruff, and pytest-cov as subprocesses against a source file
and returns an AnalysisContext value object for use by LLM-based strategies.

All tools fail gracefully: if a tool is unavailable or times out the
corresponding field in AnalysisContext is left empty.
"""

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from src.dev.test_generator.core.models import AnalysisContext, CoverageGap


class ContextGatherer:
    """Collect static-analysis context for a Python source file.

    Usage
    -----
    gatherer = ContextGatherer()
    ctx = gatherer.gather(Path("src/my/module.py"))
    """

    def __init__(self, python_executable: str = sys.executable) -> None:
        """
        Initialize the ContextGatherer with the Python interpreter command to use for subprocess invocations.
        
        Parameters:
            python_executable (str): Command or path to the Python interpreter to run external tools (e.g., `mypy`, `ruff`, `coverage`). Defaults to the current interpreter.
        """
        self._python = python_executable

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def gather(self, source_path: Path) -> AnalysisContext:
        """
        Build an AnalysisContext for the given Python source file by running the configured static-analysis and test-coverage tools and extracting project-internal dependency snippets.
        
        Parameters:
            source_path (Path): Path to the Python source file to analyze; its UTF-8 contents are read and included in the returned context.
        
        Returns:
            AnalysisContext: Contains:
                - source_code: the UTF-8 source text of `source_path`.
                - mypy_issues: tuple of mypy error lines (empty tuple if mypy is unavailable or times out).
                - ruff_issues: tuple of ruff output lines (empty tuple if ruff is unavailable or times out).
                - coverage_gaps: tuple of CoverageGap entries found from the test coverage report (empty tuple if tests/coverage are unavailable, times out, or no matching test file).
                - dependency_code: concatenated snippets of classes/functions from project-internal imports, or an empty string if none could be extracted.
        """
        source_code = source_path.read_text(encoding="utf-8")
        return AnalysisContext(
            source_code=source_code,
            mypy_issues=self._gather_mypy(source_path),
            ruff_issues=self._gather_ruff(source_path),
            coverage_gaps=self._gather_coverage(source_path),
            dependency_code=_gather_dependency_code(source_path, source_code),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _gather_mypy(self, source_path: Path) -> Tuple[str, ...]:
        """
        Collects mypy error output for the given source file.
        
        Returns:
            tuple[str, ...]: Mypy error lines (each contains ": error:"); returns an empty tuple if the mypy executable is not found or the run times out.
        """
        try:
            result = subprocess.run(
                [self._python, "-m", "mypy", str(source_path), "--no-error-summary"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ()
        lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and ": error:" in line
        ]
        return tuple(lines)

    def _gather_ruff(self, source_path: Path) -> Tuple[str, ...]:
        """
        Collect ruff check output lines for the given source file.
        
        Runs `python -m ruff check <source_path>` and returns the non-empty, whitespace-stripped lines from ruff's standard output. If ruff is not installed or the subprocess times out, returns an empty tuple.
        
        Returns:
            tuple[str, ...]: Non-empty stripped stdout lines from ruff, or `()` on failure.
        """
        try:
            result = subprocess.run(
                [self._python, "-m", "ruff", "check", str(source_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ()
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return tuple(lines)

    def _gather_coverage(self, source_path: Path) -> Tuple[CoverageGap, ...]:
        """
        Collect per-function coverage gaps for the given source file by locating and running its tests.
        
        If no matching test file is found, or if coverage/pytest invocation fails due to a missing executable or a timeout, an empty tuple is returned.
        
        Returns:
            Tuple[CoverageGap, ...]: A tuple of CoverageGap entries describing functions with uncovered lines for the target source file; an empty tuple if no gaps are found or on failure.
        """
        test_file = find_test_file(source_path)
        if test_file is None:
            return ()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cov_json_path = Path(f.name)

        try:
            subprocess.run(
                [
                    self._python,
                    "-m",
                    "coverage",
                    "run",
                    "-m",
                    "pytest",
                    str(test_file),
                    "-q",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            subprocess.run(
                [self._python, "-m", "coverage", "json", "-o", str(cov_json_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return parse_coverage_json(cov_json_path, source_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ()
        finally:
            cov_json_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Module-level pure helpers (testable without instantiating the class)
# ---------------------------------------------------------------------------


def _gather_dependency_code(source_path: Path, source_code: str) -> str:
    """
    Extract top-level class and function definition snippets from project-internal modules imported by the provided source file.
    
    Parses the provided source text to discover names imported via `from ... import ...`, resolves those modules to `.py` files under the project's `src` root (or the source file's parent if no `src` directory is present), and extracts top-level `class`, `def`, and `async def` blocks from those dependency files. Each extracted block is prefixed with a comment of the form `# from <module>` and snippets are joined with a blank line. Returns an empty string if no snippets are found or if parsing/IO errors occur.
    
    Parameters:
        source_path (Path): Path to the source file being analyzed; used to infer project layout and resolve dependency file locations.
        source_code (str): UTF-8 decoded source text of `source_path`.
    
    Returns:
        str: Concatenated snippets of dependency definitions, or an empty string if none were extracted or on error.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return ""

    # Collect names imported from project-internal modules
    imported: dict[str, str] = {}  # name -> dotted_module
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                name = alias.asname or alias.name
                imported[name] = node.module

    if not imported:
        return ""

    # Find the project root (the directory containing 'src' or the source root)
    resolved = source_path.resolve()
    parts = resolved.parts
    if "src" in parts:
        src_index = len(parts) - 1 - parts[::-1].index("src")
        src_root = Path(*parts[: src_index + 1])
    else:
        src_root = resolved.parent

    snippets: list[str] = []
    seen_modules: set[str] = set()

    for _name, module_dotted in imported.items():
        if module_dotted in seen_modules:
            continue
        seen_modules.add(module_dotted)

        # Try to resolve dotted module to a file under src_root
        rel_path = Path(module_dotted.replace(".", "/") + ".py")
        candidate = src_root / rel_path
        if not candidate.exists():
            continue

        try:
            dep_source = candidate.read_text(encoding="utf-8")
            dep_tree = ast.parse(dep_source)
        except (OSError, SyntaxError):
            continue

        # Extract only class/function definitions (not the full file)
        dep_lines = dep_source.splitlines()
        for node in ast.walk(dep_tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", None)
                if end:
                    block = "\n".join(dep_lines[node.lineno - 1 : end])
                    snippets.append(f"# from {module_dotted}\n{block}")

    return "\n\n".join(snippets)


def find_test_file(source_path: Path) -> Optional[Path]:
    """
    Locate the first test file that corresponds to the given source file using a project-aware search order.
    
    Search order (checked in sequence):
    1. `test_<stem>.py` next to the source file
    2. `<stem>_test.py` next to the source file
    3. `tests/test_<stem>.py` under the project root (when the source path contains a `src` directory)
    4. `tests/test_generator/test_<stem>.py` under the project root
    
    Returns:
        Path: The first matching test file path, or `None` if no candidate exists.
    """
    stem = source_path.stem
    resolved = source_path.resolve()
    parts = resolved.parts

    candidates = [
        source_path.parent / f"test_{stem}.py",
        source_path.parent / f"{stem}_test.py",
    ]

    if "src" in parts:
        src_index = len(parts) - 1 - parts[::-1].index("src")
        project_root = Path(*parts[:src_index])
        candidates.extend(
            [
                project_root / "tests" / f"test_{stem}.py",
                project_root / "tests" / "test_generator" / f"test_{stem}.py",
            ]
        )

    return next((c for c in candidates if c.exists()), None)


def parse_coverage_json(json_path: Path, source_path: Path) -> Tuple[CoverageGap, ...]:
    """
    Extract per-function coverage gaps from a coverage.py JSON report for the given source file.
    
    The function locates the report entry for `source_path` by comparing the resolved source path against the report's `files` keys (using a suffix heuristic and filename fallback), then collects any `missing_lines` listed for each function into `CoverageGap` records. If the JSON cannot be read/parsed or the source file is not present in the report, an empty tuple is returned.
    
    Returns:
        tuple[CoverageGap, ...]: Coverage gaps for functions in the source file, or an empty tuple if none were found or on error.
    """
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return ()

    resolved_str = str(source_path.resolve())
    source_key: Optional[str] = None
    for key in data.get("files", {}):
        # coverage.py stores keys as relative paths; resolve both ends
        if resolved_str.endswith(key.replace("/", str(Path("/")))) or key.endswith(
            source_path.name
        ):
            source_key = key
            break

    if source_key is None:
        return ()

    gaps: list[CoverageGap] = []
    for func_name, func_data in data["files"][source_key].get("functions", {}).items():
        missing = func_data.get("missing_lines", [])
        if missing:
            gaps.append(
                CoverageGap(
                    entity_name=func_name,
                    uncovered_lines=tuple(sorted(missing)),
                )
            )
    return tuple(gaps)
