# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/storage/recovery.py`
**Commit:** `28c2fa0`
**Generated:** 2026-07-15T17:55:52Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/storage/recovery.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:55:52Z"
```

## Claim(s)

1. implements the converged plan for the finding per its acceptance condition
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L14](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L14)
- **Requirements Verified:** write-code: implement the converged plan within scope

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`28c2fa0`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/28c2fa07579ec547d98bd09d3455de56d2c20127))

- [`src/branch_fixer/storage/recovery.py#L135`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/28c2fa07579ec547d98bd09d3455de56d2c20127/src/branch_fixer/storage/recovery.py#L135)
- [`src/branch_fixer/storage/recovery.py#L174`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/28c2fa07579ec547d98bd09d3455de56d2c20127/src/branch_fixer/storage/recovery.py#L174)
- [`src/branch_fixer/storage/recovery.py#L225`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/28c2fa07579ec547d98bd09d3455de56d2c20127/src/branch_fixer/storage/recovery.py#L225)
- [`src/branch_fixer/storage/recovery.py#L259`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/28c2fa07579ec547d98bd09d3455de56d2c20127/src/branch_fixer/storage/recovery.py#L259)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`RecoveryManager`** (L135): PASS -- 27 test(s) call `RecoveryManager` directly
  - `tests/test_pef_p09_resolve_async_sync_mismatch.py::test_checkpointerror_pins_the_finding_defect`
  - `tests/unit/storage/test_recovery.py::test_init_creates_backup_dir_and_index`
  - `tests/unit/storage/test_recovery.py::test_init_raises_value_error_when_parent_missing`
  - `tests/unit/storage/test_recovery.py::test_init_raises_permission_error_when_not_writable`
  - `tests/unit/storage/test_recovery.py::test_create_checkpoint_saves_rp_and_calls_session_store`
  - `tests/unit/storage/test_recovery.py::test_create_checkpoint_propagates_as_checkpoint_error_on_inner_exception`
  - `tests/unit/storage/test_recovery.py::test_create_checkpoint_metadata_defaults_to_empty_dict`
  - `tests/unit/storage/test_recovery.py::test_restore_checkpoint_not_found_raises_restore_error`
  - `tests/unit/storage/test_recovery.py::test_restore_checkpoint_branch_matches_removes_checkpoint_when_cleanup_true`
  - `tests/unit/storage/test_recovery.py::test_restore_checkpoint_branch_mismatch_checkout_success`
- **`RecoveryManager.create_checkpoint`** (L174): PASS -- 5 test(s) call `create_checkpoint` directly
  - `tests/test_pef_p09_resolve_async_sync_mismatch.py::test_checkpointerror_pins_the_finding_defect`
  - `tests/unit/storage/test_recovery.py::test_create_checkpoint_saves_rp_and_calls_session_store`
  - `tests/unit/storage/test_recovery.py::test_create_checkpoint_propagates_as_checkpoint_error_on_inner_exception`
  - `tests/unit/storage/test_recovery.py::test_create_checkpoint_metadata_defaults_to_empty_dict`
  - `tests/unit/storage/test_recovery.py::test_end_to_end_checkpoint_and_restore_cycle`
- **`RecoveryManager.restore_checkpoint`** (L225): PASS -- 7 test(s) call `restore_checkpoint` directly
  - `tests/unit/storage/test_recovery.py::test_restore_checkpoint_not_found_raises_restore_error`
  - `tests/unit/storage/test_recovery.py::test_restore_checkpoint_branch_matches_removes_checkpoint_when_cleanup_true`
  - `tests/unit/storage/test_recovery.py::test_restore_checkpoint_branch_mismatch_checkout_success`
  - `tests/unit/storage/test_recovery.py::test_restore_checkpoint_checkout_failure_raises_restore_error_and_keeps_checkpoint`
  - `tests/unit/storage/test_recovery.py::test_restore_checkpoint_cleanup_false_keeps_checkpoint`
  - `tests/unit/storage/test_recovery.py::test_end_to_end_checkpoint_and_restore_cycle`
  - `tests/unit/storage/test_recovery.py::test_restore_with_checkout_sequence`
- **`RecoveryManager.handle_failure`** (L259): PASS -- 3 test(s) call `handle_failure` directly
  - `tests/unit/storage/test_recovery.py::test_handle_failure_no_checkpoints_returns_false`
  - `tests/unit/storage/test_recovery.py::test_handle_failure_calls_restore_with_cleanup_false_and_returns_true`
  - `tests/unit/storage/test_recovery.py::test_handle_failure_restore_raises_restoreerror_returns_false`

**Coverage summary:** 4/4 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 0 error(s)
- **mypy:** 

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | implements the converged plan for the finding per its accept... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (4/4 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

recovery.py for the finding
