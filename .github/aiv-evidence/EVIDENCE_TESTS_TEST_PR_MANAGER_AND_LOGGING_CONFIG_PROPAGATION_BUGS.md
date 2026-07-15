# AIV Evidence File (v1.0)

**File:** `tests/test_pr_manager_and_logging_config_propagation_bugs.py`
**Commit:** `3f758b1`
**Generated:** 2026-07-15T17:54:34Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pr_manager_and_logging_config_propagation_bugs.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:54:34Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L57](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L57)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`3f758b1`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/3f758b18c109b72283896a3bd5913ba96c6abd8e))

- [`tests/test_pr_manager_and_logging_config_propagation_bugs.py#L1-L54`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/3f758b18c109b72283896a3bd5913ba96c6abd8e/tests/test_pr_manager_and_logging_config_propagation_bugs.py#L1-L54)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`test_create_pr_propagates_modified_files_and_metadata_into_pr_details`** (L1-L54): FAIL -- WARNING: No tests import or call `test_create_pr_propagates_modified_files_and_metadata_into_pr_details`
- **`test_repeated_setup_logging_calls_keep_snoop_handler_count_stable`** (unknown): FAIL -- WARNING: No tests import or call `test_repeated_setup_logging_calls_keep_snoop_handler_count_stable`

**Coverage summary:** 0/2 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/2 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pr_manager_and_logging_config_propagation_bugs.py for the finding
