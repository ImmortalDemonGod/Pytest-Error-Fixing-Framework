# AIV Evidence File (v1.0)

**File:** `scripts/analyze_code.sh`
**Commit:** `e1fd05f`
**Generated:** 2026-07-15T17:57:39Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "scripts/analyze_code.sh"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T17:57:39Z"
```

## Claim(s)

1. implements the converged plan for the finding per its acceptance condition
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L21](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L21)
- **Requirements Verified:** write-code: implement the converged plan within scope

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`e1fd05f`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/e1fd05f09f76d42ae417051c38eeb0e5f1dcc3b0))

- [`scripts/analyze_code.sh#L96-L99`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/e1fd05f09f76d42ae417051c38eeb0e5f1dcc3b0/scripts/analyze_code.sh#L96-L99)
- [`scripts/analyze_code.sh#L101`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/e1fd05f09f76d42ae417051c38eeb0e5f1dcc3b0/scripts/analyze_code.sh#L101)
- [`scripts/analyze_code.sh#L104-L114`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/e1fd05f09f76d42ae417051c38eeb0e5f1dcc3b0/scripts/analyze_code.sh#L104-L114)

### Class A (Execution Evidence)

**WARNING:** No tests found that directly import or reference the changed file.
This file has no claim-specific execution evidence.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), pytest (no claim-specific tests found).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

analyze_code.sh for the finding
