# Bug catalog — pef-p25-remove-misleading-empty-orig

| # | Location | Defect | Evidence (harness-executed) | Caught by |
|---|----------|--------|------------------------------|-----------|
| 1 | src/branch_fixer/core/models.py:112-115 | `CodeChanges` declares both `original_code: str` and `modified_code: str`, implying it carries a diff. However, `AIManager._parse_response` at `src/branch_fixer/services/ai/manager.py:317` always constructs it as `CodeChanges(original_code="", modified_code=modified_code)`. The `original_code` field is permanently empty, making the class a misleading wrapper around a single string. | .venv/bin/python -m pytest -q exits 0 after CodeChanges.original_code is removed (or populated with real pre-fix content); no source reads CodeChanges.original_code as a diff input (grep -rc 'original_code' src/branch_fixer resolves to only the single construction site, or 0 once removed). | `tests/test_pef_p25_remove_misleading_empty_orig.py` |

- **Expected (per the finding goal):** .venv/bin/python -m pytest -q exits 0 after CodeChanges.original_code is removed (or populated with real pre-fix content); no source reads CodeChanges.original_code as a diff input (grep -rc 'original_code' src/branch_fixer resolves to only the single construction site, or 0 once removed).
- Every row above is recorded ground truth (finding fields + harness-executed command outputs); no value is estimated.
