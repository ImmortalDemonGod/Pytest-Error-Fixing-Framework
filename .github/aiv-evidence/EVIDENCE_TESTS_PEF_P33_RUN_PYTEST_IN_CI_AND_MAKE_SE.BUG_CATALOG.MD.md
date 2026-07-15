# AIV Evidence File (v1.0)

**File:** `tests/pef-p33-run-pytest-in-ci-and-make-se.bug-catalog.md`
**Commit:** `ca17a71`
**Generated:** 2026-07-15T17:52:13Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/pef-p33-run-pytest-in-ci-and-make-se.bug-catalog.md"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:52:13Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L28](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L28)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`ca17a71`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/ca17a712262c9b9960ff0c4033316d72dd3e2f30))

- [`tests/pef-p33-run-pytest-in-ci-and-make-se.bug-catalog.md#L1-L21`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/ca17a712262c9b9960ff0c4033316d72dd3e2f30/tests/pef-p33-run-pytest-in-ci-and-make-se.bug-catalog.md#L1-L21)

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

pef-p33-run-pytest-in-ci-and-make-se.bug-catalog.md for the finding
