# AIV Evidence File (v1.0)

**File:** `tests/test_pef_p18_broaden_failure_parser_regex.py`
**Commit:** `675cde4`
**Generated:** 2026-07-15T17:45:24Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef_p18_broaden_failure_parser_regex.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:45:24Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L38](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L38)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`675cde4`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/675cde4ae3865b43cbccc11e058330e3093ca3eb))

- [`tests/test_pef_p18_broaden_failure_parser_regex.py#L1-L45`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/675cde4ae3865b43cbccc11e058330e3093ca3eb/tests/test_pef_p18_broaden_failure_parser_regex.py#L1-L45)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`test_parse_stop_iteration_non_error_failure`** (L1-L45): FAIL -- WARNING: No tests import or call `test_parse_stop_iteration_non_error_failure`
- **`test_parse_keyboard_interrupt_non_error_failure`** (unknown): FAIL -- WARNING: No tests import or call `test_parse_keyboard_interrupt_non_error_failure`
- **`test_parse_custom_exception_non_error_failure`** (unknown): FAIL -- WARNING: No tests import or call `test_parse_custom_exception_non_error_failure`

**Coverage summary:** 0/3 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/3 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pef_p18_broaden_failure_parser_regex.py for the finding
