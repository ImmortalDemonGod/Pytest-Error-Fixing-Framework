# AIV Evidence File (v1.0)

**File:** `tests/test_pef-p01-remove-hardcoded-codescene-a.py`
**Commit:** `3654b40`
**Generated:** 2026-07-15T17:48:35Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef-p01-remove-hardcoded-codescene-a.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:48:35Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L12](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L12)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`3654b40`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/3654b40280c938616311d55953c2e9daaac397b3))

- [`tests/test_pef-p01-remove-hardcoded-codescene-a.py#L1-L79`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/3654b40280c938616311d55953c2e9daaac397b3/tests/test_pef-p01-remove-hardcoded-codescene-a.py#L1-L79)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`_write_stub_executable`** (L1-L79): PASS -- 1 test(s) call `_write_stub_executable` directly
  - `tests/test_pef-p01-remove-hardcoded-codescene-a.py::test_missing_cs_access_token_fails_fast_without_hardcoded_fallback`
- **`test_missing_cs_access_token_fails_fast_without_hardcoded_fallback`** (unknown): FAIL -- WARNING: No tests import or call `test_missing_cs_access_token_fails_fast_without_hardcoded_fallback`

**Coverage summary:** 1/2 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/2 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pef-p01-remove-hardcoded-codescene-a.py for the finding
