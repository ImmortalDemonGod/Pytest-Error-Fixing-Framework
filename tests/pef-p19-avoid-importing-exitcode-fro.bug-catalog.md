# Bug catalog — pef-p19-avoid-importing-exitcode-fro

| # | Location | Defect | Evidence (harness-executed) | Caught by |
|---|----------|--------|------------------------------|-----------|
| 1 | src/branch_fixer/services/pytest/models.py:7 | `from _pytest.main import ExitCode` imports from pytest's private internal module (prefixed `_pytest`). Private APIs are not covered by pytest's public stability contract and may change or be removed without notice across minor version bumps, breaking SessionResult at import time. | models.py imports successfully without referencing the `_pytest` private package; grep shows no `_pytest` import remaining. | `tests/test_pef_p19_avoid_importing_exitcode_fro.py` |

- **Expected (per the finding goal):** models.py imports successfully without referencing the `_pytest` private package; grep shows no `_pytest` import remaining.
- Every row above is recorded ground truth (finding fields + harness-executed command outputs); no value is estimated.
