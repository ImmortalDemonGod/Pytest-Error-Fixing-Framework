"""RED test pinning F72/F73 (audit/02-static-audit.md L46).

Both findings are defects in *test source code*, not production code:

- F72: tests/unit/services/pytest/test_runner.py:470 —
  `assert "Duration: 1.23s" or "Duration: 1.2"` is a vacuous `str or str`
  expression that always evaluates truthy and never references `report`.
- F73: tests/unit/orchestration/test_orchestrator.py:583 —
  `raise SimpleNamespace.__class__("CheckpointError")("fail")` reduces to
  `raise str("fail")`, which raises `TypeError: exceptions must derive from
  BaseException` instead of a real `CheckpointError`.

`PytestRunner.format_report` (src/branch_fixer/services/pytest/runner.py:497)
and `FixOrchestrator._create_checkpoint_if_needed`
(src/branch_fixer/orchestration/orchestrator.py:500-521) already behave
correctly, so a test that merely calls those production symbols with correct
expectations would pass today and would not be RED. Instead this test parses
the exact buggy function's source out of the current test files via `ast` and
asserts the corrected pattern is present (F72) / the broken pattern is absent
(F73) — both assertions are false against the current buggy test files.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_TEST_PATH = REPO_ROOT / "tests" / "unit" / "services" / "pytest" / "test_runner.py"
ORCH_TEST_PATH = REPO_ROOT / "tests" / "unit" / "orchestration" / "test_orchestrator.py"


def _find_method_source(path: Path, class_name: str, func_name: str) -> str:
    source = path.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == func_name:
                    segment = ast.get_source_segment(source, sub)
                    assert segment is not None
                    return segment
    raise AssertionError(f"{class_name}.{func_name} not found in {path}")


def test_format_report_basic_assertion_checks_report_variable():
    """F72: the duration assertion must actually check `report`, not a vacuous `or` expression."""
    func_src = _find_method_source(RUNNER_TEST_PATH, "TestPytestRunner", "test_format_report_basic")
    assert 'assert "Duration: 1.23s" in report' in func_src


def test_checkpoint_fallback_raises_real_checkpoint_error():
    """F73: the checkpoint-error fallback must raise a real exception, not `str("fail")` via `type(...)`."""
    func_src = _find_method_source(
        ORCH_TEST_PATH, "TestFixOrchestrator", "test_create_checkpoint_handles_checkpoint_error"
    )
    assert 'SimpleNamespace.__class__("CheckpointError")("fail")' not in func_src
