# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/services/git/branch_manager.py`
**Commit:** `4ee31be`
**Generated:** 2026-07-15T17:50:03Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/services/git/branch_manager.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:50:03Z"
```

## Claim(s)

1. implements the converged plan for the finding per its acceptance condition
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L19](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L19)
- **Requirements Verified:** write-code: implement the converged plan within scope

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`4ee31be`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/4ee31be9e97090f69816541551b8b4de7f7ec2f0))

- [`src/branch_fixer/services/git/branch_manager.py#L3-L4`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/4ee31be9e97090f69816541551b8b4de7f7ec2f0/src/branch_fixer/services/git/branch_manager.py#L3-L4)
- [`src/branch_fixer/services/git/branch_manager.py#L170-L196`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/4ee31be9e97090f69816541551b8b4de7f7ec2f0/src/branch_fixer/services/git/branch_manager.py#L170-L196)
- [`src/branch_fixer/services/git/branch_manager.py#L252-L262`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/4ee31be9e97090f69816541551b8b4de7f7ec2f0/src/branch_fixer/services/git/branch_manager.py#L252-L262)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`BranchManager`** (L3-L4): PASS -- 24 test(s) call `BranchManager` directly
  - `tests/unit/git/test_branch_manager.py::test_init_stores_repository_and_defaults`
  - `tests/unit/git/test_branch_manager.py::test_get_status_clean_repo_no_changes`
  - `tests/unit/git/test_branch_manager.py::test_get_status_dirty_repo_with_changes`
  - `tests/unit/git/test_branch_manager.py::test_create_fix_branch_success_default_base`
  - `tests/unit/git/test_branch_manager.py::test_create_fix_branch_success_with_from_branch`
  - `tests/unit/git/test_branch_manager.py::test_cleanup_fix_branch_returns_true_if_branch_does_not_exist`
  - `tests/unit/git/test_branch_manager.py::test_cleanup_fix_branch_delete_success_nonforce`
  - `tests/unit/git/test_branch_manager.py::test_cleanup_fix_branch_delete_success_force`
  - `tests/unit/git/test_branch_manager.py::test_cleanup_fix_branch_switches_branch_before_delete_when_current`
  - `tests/unit/git/test_branch_manager.py::test_validate_branch_name_accepts_valid_names`
- **`BranchManager.get_branch_metadata`** (L170-L196): PASS -- 2 test(s) call `get_branch_metadata` directly
  - `tests/test_pef-p12-implement-branch-manager-met.py::test_get_branch_metadata_returns_populated_metadata_for_known_branch`
  - `tests/unit/git/test_branch_manager.py::test_get_branch_metadata_raises_not_implemented`
- **`BranchManager.is_branch_merged`** (L252-L262): PASS -- 3 test(s) call `is_branch_merged` directly
  - `tests/test_pef-p12-implement-branch-manager-met.py::test_is_branch_merged_true_for_merged_branch`
  - `tests/test_pef-p12-implement-branch-manager-met.py::test_is_branch_merged_false_for_unmerged_branch`
  - `tests/unit/git/test_branch_manager.py::test_is_branch_merged_raises_not_implemented`

**Coverage summary:** 3/3 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (3/3 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

branch_manager.py for the finding
