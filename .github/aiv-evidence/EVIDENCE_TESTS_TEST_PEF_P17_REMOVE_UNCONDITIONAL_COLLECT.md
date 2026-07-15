# AIV Evidence File (v1.0)

**File:** `tests/test_pef_p17_remove_unconditional_collect.py`
**Commit:** `838a665`
**Generated:** 2026-07-15T17:44:32Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef_p17_remove_unconditional_collect.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:44:32Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L52](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L52)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`838a665`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/838a665e75c6771ac8f31262c8f5934b62bc4335))

- [`tests/test_pef_p17_remove_unconditional_collect.py#L1-L19`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/838a665e75c6771ac8f31262c8f5934b62bc4335/tests/test_pef_p17_remove_unconditional_collect.py#L1-L19)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`test_pytest_collection_modifyitems_emits_no_stdout`** (L1-L19): FAIL -- WARNING: No tests import or call `test_pytest_collection_modifyitems_emits_no_stdout`

**Coverage summary:** 0/1 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/1 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pef_p17_remove_unconditional_collect.py for the finding
