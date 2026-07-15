# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/orchestration/orchestrator.py`
**Commit:** `8985093`
**Generated:** 2026-07-15T07:26:06Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/orchestration/orchestrator.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T07:26:06Z"
```

## Claim(s)

1. implements the converged plan for the finding per its acceptance condition
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L16](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L16)
- **Requirements Verified:** write-code: implement the converged plan within scope

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`8985093`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/8985093ee13dc2db4b57ffc035624cc96d078792))

- [`src/branch_fixer/orchestration/orchestrator.py#L344`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/8985093ee13dc2db4b57ffc035624cc96d078792/src/branch_fixer/orchestration/orchestrator.py#L344)
- [`src/branch_fixer/orchestration/orchestrator.py#L358-L366`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/8985093ee13dc2db4b57ffc035624cc96d078792/src/branch_fixer/orchestration/orchestrator.py#L358-L366)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`FixOrchestrator`** (L344): PASS -- 36 test(s) call `FixOrchestrator` directly
  - `tests/test_pef_p06b_guard_transient_api.py::test_fix_error_retries_past_transient_fixserviceerror_and_preserves_message`
  - `tests/unit/orchestration/test_orchestrator.py::test_constructor_sets_defaults`
  - `tests/unit/orchestration/test_orchestrator.py::test_start_session_happy_and_sets_running`
  - `tests/unit/orchestration/test_orchestrator.py::test_start_session_empty_list_raises`
  - `tests/unit/orchestration/test_orchestrator.py::test_validate_session_happy`
  - `tests/unit/orchestration/test_orchestrator.py::test_validate_session_missing_raises`
  - `tests/unit/orchestration/test_orchestrator.py::test_validate_session_wrong_state_raises`
  - `tests/unit/orchestration/test_orchestrator.py::test_handle_error_fix_skips_if_already_fixed`
  - `tests/unit/orchestration/test_orchestrator.py::test_handle_error_fix_success_appends_completed`
  - `tests/unit/orchestration/test_orchestrator.py::test_handle_error_fix_failure_sets_session_failed`
- **`FixOrchestrator.fix_error`** (L358-L366): PASS -- 6 test(s) call `fix_error` directly
  - `tests/test_pef_p06b_guard_transient_api.py::test_fix_error_retries_past_transient_fixserviceerror_and_preserves_message`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_no_active_session_raises`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_success_first_attempt`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_retries_until_success`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_all_attempts_fail_returns_false`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_fixservice_raises_propagates`

**Coverage summary:** 2/2 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (2/2 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

orchestrator.py for the finding
