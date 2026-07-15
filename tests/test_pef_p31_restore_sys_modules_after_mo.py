import sys

import pytest

# Finding F25 (audit/02-static-audit.md#L25): tests/unit/utils/test_run_cli.py
# injects fake modules into sys.modules at 4 sites (lines 179, 217, 247, 274)
# with no restoration, permanently polluting sys.modules for the rest of the
# pytest session. This is the completion contract's goal_condition (VERIFY [1]),
# run in-process as a nested pytest.main() invocation over the target file.
_KEYS = (
    "branch_fixer.orchestration.orchestrator",
    "branch_fixer.services.pytest.error_processor",
)


def test_test_run_cli_leaves_sys_modules_unpolluted():
    before = {k: sys.modules.get(k) for k in _KEYS}

    rc = pytest.main(["tests/unit/utils/test_run_cli.py", "-q"])

    after = {k: sys.modules.get(k) for k in _KEYS}

    assert rc == 0, f"pytest exited {rc}"
    assert after == before, (
        "sys.modules polluted after test run: "
        f"{[k for k in _KEYS if before[k] is not after[k]]}"
    )
