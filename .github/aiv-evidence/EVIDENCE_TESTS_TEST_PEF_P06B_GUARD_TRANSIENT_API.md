# AIV Evidence File (v1.0)

**File:** `tests/test_pef_p06b_guard_transient_api.py`
**Commit:** `319e66f`
**Generated:** 2026-07-15T07:17:54Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef_p06b_guard_transient_api.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T07:17:54Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L16](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L16)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`319e66f`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/319e66f958577778ea99a4cca72fca930f890289))

- [`tests/test_pef_p06b_guard_transient_api.py#L1-L108`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/319e66f958577778ea99a4cca72fca930f890289/tests/test_pef_p06b_guard_transient_api.py#L1-L108)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`_inject_fake_fix_service`** (L1-L108): PASS -- 5 test(s) call `_inject_fake_fix_service` directly
  - `tests/test_pef_p06b_guard_transient_api.py::test_fix_error_retries_past_transient_fixserviceerror_and_preserves_message`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_success_first_attempt`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_retries_until_success`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_all_attempts_fail_returns_false`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_fixservice_raises_propagates`
- **`simple_error`** (unknown): FAIL -- WARNING: No tests import or call `simple_error`
- **`test_fix_error_retries_past_transient_fixserviceerror_and_preserves_message`** (unknown): FAIL -- WARNING: No tests import or call `test_fix_error_retries_past_transient_fixserviceerror_and_preserves_message`
- **`FakeFixService`** (unknown): FAIL -- WARNING: No tests import or call `FakeFixService`
- **`FakeFixService.__init__`** (unknown): FAIL -- WARNING: No tests import or call `__init__`
- **`FakeFixService.attempt_fix`** (unknown): PASS -- 6 test(s) call `attempt_fix` directly
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_dev_force_success_marks_fixed_and_updates_session`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_workspace_validation_failure_raises_fixserviceerror`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_returns_false_marks_attempt_failed`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_success_but_verification_fails_restores_and_returns_false`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_and_verify_success_marks_fixed_and_updates_session_and_state_manager`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_inner_exception_after_applying_raises_and_restores_backup`

**Coverage summary:** 2/6 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (2/6 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pef_p06b_guard_transient_api.py for the finding
