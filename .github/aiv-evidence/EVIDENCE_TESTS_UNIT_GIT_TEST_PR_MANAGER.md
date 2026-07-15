# AIV Evidence File (v1.0)

**File:** `tests/unit/git/test_pr_manager.py`
**Commit:** `fceaf85`
**Previous:** `81d9aba`
**Generated:** 2026-07-15T18:08:18Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/unit/git/test_pr_manager.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T18:08:18Z"
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

**Scope Inventory** (SHA: [`fceaf85`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/fceaf8578f5f961c2b52885b070ea6b05ca20b8d))

- [`tests/unit/git/test_pr_manager.py#L24`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/fceaf8578f5f961c2b52885b070ea6b05ca20b8d/tests/unit/git/test_pr_manager.py#L24)
- [`tests/unit/git/test_pr_manager.py#L32-L33`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/fceaf8578f5f961c2b52885b070ea6b05ca20b8d/tests/unit/git/test_pr_manager.py#L32-L33)
- [`tests/unit/git/test_pr_manager.py#L141`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/fceaf8578f5f961c2b52885b070ea6b05ca20b8d/tests/unit/git/test_pr_manager.py#L141)
- [`tests/unit/git/test_pr_manager.py#L148-L150`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/fceaf8578f5f961c2b52885b070ea6b05ca20b8d/tests/unit/git/test_pr_manager.py#L148-L150)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`patched_types`** (L24): FAIL -- WARNING: No tests import or call `patched_types`
- **`FakePRDetails`** (L32-L33): FAIL -- WARNING: No tests import or call `FakePRDetails`
- **`FakePRDetails.__init__`** (L141): FAIL -- WARNING: No tests import or call `__init__`
- **`TestPRManager`** (L148-L150): FAIL -- WARNING: No tests import or call `TestPRManager`
- **`TestPRManager.test_create_pr_propagates_modified_files_and_metadata_into_pr_details`** (unknown): FAIL -- WARNING: No tests import or call `test_create_pr_propagates_modified_files_and_metadata_into_pr_details`

**Coverage summary:** 0/5 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/5 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pr_manager.py for the finding
