"""RED test for finding pef-p26 (F17 + F42).

F17: src/branch_fixer/services/ai/manager.py:217 has a redundant function-local
`import re` even though `re` is already imported at module level (line 3).

F42: src/branch_fixer/services/git/models.py:87-88 — `PRDetails.created_at` /
`.updated_at` default to naive datetimes via `field(default_factory=datetime.now)`,
which raises TypeError when compared against a tz-aware datetime.
"""

import ast
import inspect
from datetime import datetime, timezone

from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.git.models import PRDetails, PRStatus


def _is_import_re(node):
    return isinstance(node, ast.Import) and any(alias.name == "re" for alias in node.names)


def test_manager_module_has_exactly_one_import_re_and_no_inner_ones():
    module_file = inspect.getsourcefile(AIManager)
    source = open(module_file, encoding="utf-8").read()
    tree = ast.parse(source)

    module_level_import_re_count = sum(1 for node in tree.body if _is_import_re(node))

    inner_import_re_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if child is not node and _is_import_re(child):
                    inner_import_re_count += 1

    assert module_level_import_re_count == 1
    assert inner_import_re_count == 0


def test_pr_details_timestamps_are_timezone_aware():
    p = PRDetails(
        id=1,
        title="t",
        description="d",
        branch_name="b",
        status=PRStatus.OPEN,
    )

    assert p.created_at.tzinfo is not None
    assert p.updated_at.tzinfo is not None

    # Must not raise TypeError: can't subtract offset-naive and offset-aware datetimes
    _ = datetime.now(timezone.utc) - p.created_at
