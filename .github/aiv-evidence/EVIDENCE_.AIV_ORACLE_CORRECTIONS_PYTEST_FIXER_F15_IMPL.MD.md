# AIV Evidence File (v1.0)

**File:** `.aiv/oracle-corrections/pytest-fixer-f15-impl.md`
**Commit:** `0345bdb`
**Generated:** 2026-06-21T04:31:17Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R0
  sod_mode: S0
  critical_surfaces: []
  blast_radius: ".aiv/oracle-corrections/pytest-fixer-f15-impl.md"
  classification_rationale: "R0: pure documentation file in .aiv/oracle-corrections/; no functional code; all governance evidence"
  classified_by: "ImmortalDemonGod"
  classified_at: "2026-06-21T04:31:17Z"
```

## Claim(s)

1. _handle_manual_fix_choice 'fixed' branch: old oracle asserted scalar True, encoding the bug that fix-outcome was discarded; correct oracle is (True, True)
2. _handle_ai_fix_choice: old oracle asserted True for BOTH success and failure branches, encoding the defect that failure was swallowed; correct oracles are (True,True) and (True,False)
3. _process_all_errors noninteractive: old oracle mocked return_value=None and asserted success_count==0, directly encoding the F15 counter bug; replaced by tests asserting success_count==3 on True and 0 on False
4. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L11](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L11)
- **Requirements Verified:** F15 audit record documents success_count never incremented; oracle-corrections justifies each test that encoded this defect as correct behaviour

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`0345bdb`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/0345bdb571af219ce1e988a1fffa02b2ee193fb3))

- [`.aiv/oracle-corrections/pytest-fixer-f15-impl.md#L1-L225`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/0345bdb571af219ce1e988a1fffa02b2ee193fb3/.aiv/oracle-corrections/pytest-fixer-f15-impl.md#L1-L225)

### Class A (Execution Evidence)

- Local checks skipped (--skip-checks).
- **Skip reason:** Documentation-only governance file: oracle justification for pre-existing test corrections; no production logic changes


---

## Verification Methodology

**R0 (trivial) -- local checks skipped.**
**Reason:** Documentation-only governance file: oracle justification for pre-existing test corrections; no production logic changes
Only git diff scope inventory was collected. No execution evidence.

---

## Summary

Justify each of the 6 pre-existing test oracles that encoded the F15 bug, per oracle-guard requirement
