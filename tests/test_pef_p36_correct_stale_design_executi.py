"""RED test for the F44 doc-drift bundle (F44, F45, F55, F56, F4).

Operationalizes the GOAL condition verbatim (audit/05-plan.md:376): grep across docs returns no
'manager_design_draft', no '[Current Date]', no 'marvin' backend, and no `async def run_command`;
QUALITY_AUDIT.md row 46 is marked resolved. Per the plan's own test-strategy note (§12), this
docs-only change has no Python symbol to import — the file content itself is the unit under test,
read directly from disk (no caller supplies it), matching the plan's Layer A content assertions.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STRATEGIC_ANALYSIS = REPO_ROOT / "docs" / "design-and-research" / "01-strategic-analysis.md"
EXECUTION_FLOW = REPO_ROOT / "docs" / "developer-guide" / "04-execution-flow.md"
QUALITY_AUDIT = REPO_ROOT / "audits" / "QUALITY_AUDIT.md"

DRIFT_PATTERN = re.compile(r"manager_design_draft|\[Current Date\]|\bmarvin\b|async def run_command")
RESOLVED_PATTERN = re.compile(r"resolved|closed|done", re.IGNORECASE)


def test_strategic_analysis_and_execution_flow_have_no_stale_drift_patterns():
    combined = STRATEGIC_ANALYSIS.read_text(encoding="utf-8") + EXECUTION_FLOW.read_text(encoding="utf-8")

    matches = DRIFT_PATTERN.findall(combined)

    assert matches == []


def test_quality_audit_row_46_and_row_60_are_marked_resolved():
    lines = QUALITY_AUDIT.read_text(encoding="utf-8").splitlines()
    row_46 = lines[45]
    row_60_candidates = [line for line in lines if "services/ai/manager_design_draft.py" in line]
    assert row_60_candidates, "expected a QUALITY_AUDIT.md row referencing manager_design_draft.py"
    row_60 = row_60_candidates[0]

    assert RESOLVED_PATTERN.search(row_46) is not None
    assert RESOLVED_PATTERN.search(row_60) is not None
