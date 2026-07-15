# AIV Evidence File (v1.0)

**File:** `tests/pef-p28-rewrite-codified-bug-tests-t.bug-catalog.md`
**Commit:** `e711a89`
**Generated:** 2026-07-15T17:54:31Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/pef-p28-rewrite-codified-bug-tests-t.bug-catalog.md"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:54:31Z"
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

**Scope Inventory** (SHA: [`e711a89`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/e711a89ad6e030f70f5c37b0c0d6f8040b0b0aee))

- [`tests/pef-p28-rewrite-codified-bug-tests-t.bug-catalog.md#L1-L32`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/e711a89ad6e030f70f5c37b0c0d6f8040b0b0aee/tests/pef-p28-rewrite-codified-bug-tests-t.bug-catalog.md#L1-L32)

### Class A (Execution Evidence)

**WARNING:** No tests found that directly import or reference the changed file.
This file has no claim-specific execution evidence.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), pytest (no claim-specific tests found).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

pef-p28-rewrite-codified-bug-tests-t.bug-catalog.md for the finding
