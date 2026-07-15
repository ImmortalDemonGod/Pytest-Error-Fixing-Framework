# AIV Evidence File (v1.0)

**File:** `tests/test_pef_p16_fix_runner_nodeid_unpacking.py`
**Commit:** `1a9662f`
**Generated:** 2026-07-15T17:55:30Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef_p16_fix_runner_nodeid_unpacking.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:55:30Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L51](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L51)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`1a9662f`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/1a9662f5270de68245fe9357976828e18e8eed4a))

- [`tests/test_pef_p16_fix_runner_nodeid_unpacking.py#L1-L56`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/1a9662f5270de68245fe9357976828e18e8eed4a/tests/test_pef_p16_fix_runner_nodeid_unpacking.py#L1-L56)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`test_format_test_failures_nodeid_without_double_colons_handled_gracefully`** (L1-L56): FAIL -- WARNING: No tests import or call `test_format_test_failures_nodeid_without_double_colons_handled_gracefully`
- **`test_marker_skip_counted_as_skipped_not_passed`** (unknown): FAIL -- WARNING: No tests import or call `test_marker_skip_counted_as_skipped_not_passed`

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

test_pef_p16_fix_runner_nodeid_unpacking.py for the finding
