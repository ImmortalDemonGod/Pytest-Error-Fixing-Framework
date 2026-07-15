"""RED test for F21: stale module-path header comment.

tests/unit/core/test_verify_fix_workflow.py:1 currently reads
`# src/branch_fixer/services/pytest/test_verify_fix_workflow.py`, a path the file has never
occupied in this tree. The correct header names the file's actual location (plan decision D-1).
"""
from pathlib import Path

TARGET = Path(__file__).parent / "unit" / "core" / "test_verify_fix_workflow.py"


def test_header_comment_names_actual_file_path():
    first_line = TARGET.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "# tests/unit/core/test_verify_fix_workflow.py"
