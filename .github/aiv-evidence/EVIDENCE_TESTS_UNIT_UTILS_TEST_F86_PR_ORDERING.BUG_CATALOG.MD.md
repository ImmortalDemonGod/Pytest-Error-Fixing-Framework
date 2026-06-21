# AIV Evidence File (v1.0)

**File:** `tests/unit/utils/test_f86_pr_ordering.bug-catalog.md`
**Commit:** `88edcf3`
**Generated:** 2026-06-21T08:57:51Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R0
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/unit/utils/test_f86_pr_ordering.bug-catalog.md"
  classification_rationale: "Documentation-only file, no code logic — R0 tier appropriate; --skip-checks because no Python to analyze"
  classified_by: "ImmortalDemonGod"
  classified_at: "2026-06-21T08:57:51Z"
```

## Claim(s)

1. Bug catalog documents B1 (gh pr create before push), B2 (push failure does not prevent PR creation), and B3 (silent gh swallow) for cli.py:220-226
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15)
- **Requirements Verified:** F86 requires documenting all plausible bugs at cli.py:220-226 and pr_manager.py:71-88 before writing RED tests

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`88edcf3`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/88edcf315af191ec0b8bc24a778858ed29f4b58a))

- [`tests/unit/utils/test_f86_pr_ordering.bug-catalog.md#L1-L143`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/88edcf315af191ec0b8bc24a778858ed29f4b58a/tests/unit/utils/test_f86_pr_ordering.bug-catalog.md#L1-L143)

### Class A (Execution Evidence)

- Local checks skipped (--skip-checks).
- **Skip reason:** Markdown documentation file only — no Python code, no tests to run, no lint/type targets


---

## Verification Methodology

**R0 (trivial) -- local checks skipped.**
**Reason:** Markdown documentation file only — no Python code, no tests to run, no lint/type targets
Only git diff scope inventory was collected. No execution evidence.

---

## Summary

Bug catalog for F86: PR creation before push ordering bug in _create_and_push_pr
