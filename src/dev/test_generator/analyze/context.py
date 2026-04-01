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
        self._python = python_executable

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def gather(self, source_path: Path) -> AnalysisContext:
        """Run all tools and return an AnalysisContext for *source_path*."""
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
        """Run mypy and return error lines. Returns () on failure."""
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
        """Run ruff check and return violation lines. Returns () on failure."""
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
        """Find test file, run coverage, return per-function gaps. Returns () on failure."""
        test_file = find_test_file(source_path)
        if test_file is None:
            return ()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cov_json_path = Path(f.name)

        try:
            subprocess.run(
                [self._python, "-m", "coverage", "run", "-m", "pytest", str(test_file), "-q"],
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
    """Return source snippets of classes/functions imported from project modules.

    Parses the source file's imports, finds project-internal modules (same src/
    root), reads their source, and extracts class/function definitions that are
    referenced in the source file. This gives the LLM constructor signatures
    for types it would otherwise not be able to see.

    Returns an empty string if nothing useful is found or on any error.
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
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                end = getattr(node, "end_lineno", None)
                if end:
                    block = "\n".join(dep_lines[node.lineno - 1: end])
                    snippets.append(f"# from {module_dotted}\n{block}")

    return "\n\n".join(snippets)


def find_test_file(source_path: Path) -> Optional[Path]:
    """Return the first matching test file for *source_path*, or None.

    Search order:
    1. ``test_<stem>.py`` next to the source file
    2. ``<stem>_test.py`` next to the source file
    3. ``tests/test_<stem>.py`` under the project root (src-layout aware)
    4. ``tests/test_generator/test_<stem>.py`` (this project's convention)
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
        candidates.extend([
            project_root / "tests" / f"test_{stem}.py",
            project_root / "tests" / "test_generator" / f"test_{stem}.py",
        ])

    return next((c for c in candidates if c.exists()), None)


def parse_coverage_json(
    json_path: Path, source_path: Path
) -> Tuple[CoverageGap, ...]:
    """Parse a ``coverage json`` report and return per-function CoverageGaps.

    Matches the source file by checking whether *source_path* is a suffix of
    any key in the report's ``files`` dict (coverage.py uses relative paths).
    Returns () if the file is not in the report or the JSON is malformed.
    """
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return ()

    resolved_str = str(source_path.resolve())
    source_key: Optional[str] = None
    for key in data.get("files", {}):
        # coverage.py stores keys as relative paths; resolve both ends
        if resolved_str.endswith(key.replace("/", str(Path("/")))
                                  ) or key.endswith(source_path.name):
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
