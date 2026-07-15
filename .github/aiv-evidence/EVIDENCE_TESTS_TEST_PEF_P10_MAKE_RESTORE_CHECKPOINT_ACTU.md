# AIV Evidence File (v1.0)

**File:** `tests/test_pef_p10_make_restore_checkpoint_actu.py`
**Commit:** `347f8b1`
**Generated:** 2026-07-15T17:49:06Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef_p10_make_restore_checkpoint_actu.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:49:06Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L32](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L32)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`347f8b1`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/347f8b1cfa369f2a6df83214211474e4cf7a4985))

- [`tests/test_pef_p10_make_restore_checkpoint_actu.py#L1-L56`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/347f8b1cfa369f2a6df83214211474e4cf7a4985/tests/test_pef_p10_make_restore_checkpoint_actu.py#L1-L56)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`_session_store`** (L1-L56): PASS -- 2 test(s) call `_session_store` directly
  - `tests/test_pef_p10_make_restore_checkpoint_actu.py::test_restore_checkpoint_restores_modified_file_content_from_backup`
  - `tests/test_pef_p10_make_restore_checkpoint_actu.py::test_handle_failure_reports_diagnostics_via_logger_not_stdout`
- **`_git_repo`** (unknown): PASS -- 2 test(s) call `_git_repo` directly
  - `tests/test_pef_p10_make_restore_checkpoint_actu.py::test_restore_checkpoint_restores_modified_file_content_from_backup`
  - `tests/test_pef_p10_make_restore_checkpoint_actu.py::test_handle_failure_reports_diagnostics_via_logger_not_stdout`
- **`test_restore_checkpoint_restores_modified_file_content_from_backup`** (unknown): FAIL -- WARNING: No tests import or call `test_restore_checkpoint_restores_modified_file_content_from_backup`
- **`test_handle_failure_reports_diagnostics_via_logger_not_stdout`** (unknown): FAIL -- WARNING: No tests import or call `test_handle_failure_reports_diagnostics_via_logger_not_stdout`

**Coverage summary:** 2/4 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 0 error(s)
- **mypy:** 

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | RED test pins the finding's defect against the cited baselin... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (2/4 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pef_p10_make_restore_checkpoint_actu.py for the finding
