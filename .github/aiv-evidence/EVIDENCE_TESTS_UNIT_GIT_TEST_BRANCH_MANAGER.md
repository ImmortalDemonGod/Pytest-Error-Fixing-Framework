# AIV Evidence File (v1.0)

**File:** `tests/unit/git/test_branch_manager.py`
**Commit:** `64111a2`
**Previous:** `0190e25`
**Generated:** 2026-07-15T17:57:10Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/unit/git/test_branch_manager.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:57:10Z"
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

**Scope Inventory** (SHA: [`64111a2`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/64111a2443445396a205b8270ec72f2ea3018339))

- [`tests/unit/git/test_branch_manager.py#L336-L346`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/64111a2443445396a205b8270ec72f2ea3018339/tests/unit/git/test_branch_manager.py#L336-L346)
- [`tests/unit/git/test_branch_manager.py#L348-L351`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/64111a2443445396a205b8270ec72f2ea3018339/tests/unit/git/test_branch_manager.py#L348-L351)
- [`tests/unit/git/test_branch_manager.py#L353`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/64111a2443445396a205b8270ec72f2ea3018339/tests/unit/git/test_branch_manager.py#L353)
- [`tests/unit/git/test_branch_manager.py#L355-L358`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/64111a2443445396a205b8270ec72f2ea3018339/tests/unit/git/test_branch_manager.py#L355-L358)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`TestBranchManager`** (L336-L346): FAIL -- WARNING: No tests import or call `TestBranchManager`
- **`TestBranchManager.test_get_branch_metadata_returns_populated_metadata`** (L348-L351): FAIL -- WARNING: No tests import or call `test_get_branch_metadata_returns_populated_metadata`
- **`TestBranchManager.test_is_branch_merged_true_for_merged_branch`** (L353): FAIL -- WARNING: No tests import or call `test_is_branch_merged_true_for_merged_branch`
- **`TestBranchManager.test_is_branch_merged_false_for_unmerged_branch`** (L355-L358): FAIL -- WARNING: No tests import or call `test_is_branch_merged_false_for_unmerged_branch`

**Coverage summary:** 0/4 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/4 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_branch_manager.py for the finding
