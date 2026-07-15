# AIV Evidence File (v1.0)

**File:** `tests/test_pef-p12-implement-branch-manager-met.py`
**Commit:** `4d804de`
**Generated:** 2026-07-15T17:46:19Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef-p12-implement-branch-manager-met.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:46:19Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L19](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L19)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`4d804de`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/4d804deb4a9146f8732c2c5749715f6118002413))

- [`tests/test_pef-p12-implement-branch-manager-met.py#L1-L75`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/4d804deb4a9146f8732c2c5749715f6118002413/tests/test_pef-p12-implement-branch-manager-met.py#L1-L75)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`git_repo`** (L1-L75): FAIL -- WARNING: No tests import or call `git_repo`
- **`test_get_branch_metadata_returns_populated_metadata_for_known_branch`** (unknown): FAIL -- WARNING: No tests import or call `test_get_branch_metadata_returns_populated_metadata_for_known_branch`
- **`test_is_branch_merged_true_for_merged_branch`** (unknown): FAIL -- WARNING: No tests import or call `test_is_branch_merged_true_for_merged_branch`
- **`test_is_branch_merged_false_for_unmerged_branch`** (unknown): FAIL -- WARNING: No tests import or call `test_is_branch_merged_false_for_unmerged_branch`

**Coverage summary:** 0/4 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/4 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pef-p12-implement-branch-manager-met.py for the finding
