# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/services/git/pr_manager.py`
**Commit:** `53a6029`
**Generated:** 2026-07-15T18:02:17Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/services/git/pr_manager.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T18:02:17Z"
```

## Claim(s)

1. implements the converged plan for the finding per its acceptance condition
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L57](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L57)
- **Requirements Verified:** write-code: implement the converged plan within scope

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`53a6029`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/53a6029b7eec5420ee8b8b0e5e87508dd5ee0544))

- [`src/branch_fixer/services/git/pr_manager.py#L110-L111`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/53a6029b7eec5420ee8b8b0e5e87508dd5ee0544/src/branch_fixer/services/git/pr_manager.py#L110-L111)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`PRManager`** (L110-L111): PASS -- 13 test(s) call `PRManager` directly
  - `tests/test_pr_manager_and_logging_config_propagation_bugs.py::test_create_pr_propagates_modified_files_and_metadata_into_pr_details`
  - `tests/unit/git/test_pr_manager.py::test___init___positive_max_files_sets_attributes`
  - `tests/unit/git/test_pr_manager.py::test___init___default_required_checks_is_empty_list_and_independent`
  - `tests/unit/git/test_pr_manager.py::test___init___invalid_max_files_raises`
  - `tests/unit/git/test_pr_manager.py::test_create_pr_returns_PRDetails_and_stores_it`
  - `tests/unit/git/test_pr_manager.py::test_create_pr_increments_pr_id_on_multiple_creates`
  - `tests/unit/git/test_pr_manager.py::test_create_pr_propagates_modified_files_and_metadata_into_pr_details`
  - `tests/unit/git/test_pr_manager.py::test_update_pr_returns_existing_pr`
  - `tests/unit/git/test_pr_manager.py::test_update_pr_missing_pr_raises_PRUpdateError`
  - `tests/unit/git/test_pr_manager.py::test_validate_pr_returns_true_for_existing_pr`
- **`PRManager.create_pr`** (unknown): PASS -- 6 test(s) call `create_pr` directly
  - `tests/test_pr_manager_and_logging_config_propagation_bugs.py::test_create_pr_propagates_modified_files_and_metadata_into_pr_details`
  - `tests/unit/git/test_pr_manager.py::test_create_pr_returns_PRDetails_and_stores_it`
  - `tests/unit/git/test_pr_manager.py::test_create_pr_increments_pr_id_on_multiple_creates`
  - `tests/unit/git/test_pr_manager.py::test_create_pr_propagates_modified_files_and_metadata_into_pr_details`
  - `tests/unit/git/test_pr_manager.py::test_update_pr_returns_existing_pr`
  - `tests/unit/git/test_pr_manager.py::test_validate_pr_returns_true_for_existing_pr`

**Coverage summary:** 2/2 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (2/2 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

pr_manager.py for the finding
