# AIV Evidence File (v1.0)

**File:** `tests/test_pef_p27_fix_orchestrator_per_error_t.py`
**Commit:** `9f03219`
**Generated:** 2026-07-15T18:05:19Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef_p27_fix_orchestrator_per_error_t.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T18:05:19Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L78](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L78)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`9f03219`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/9f0321929e20ba696a1481f6ba306904f4c882ef))

- [`tests/test_pef_p27_fix_orchestrator_per_error_t.py#L1-L153`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/9f0321929e20ba696a1481f6ba306904f4c882ef/tests/test_pef_p27_fix_orchestrator_per_error_t.py#L1-L153)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`_inject_fake_fix_service`** (L1-L153): PASS -- 5 test(s) call `_inject_fake_fix_service` directly
  - `tests/test_pef_p27_fix_orchestrator_per_error_t.py::test_get_progress_temperature_reflects_current_error_not_global_retry_count`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_success_first_attempt`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_retries_until_success`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_all_attempts_fail_returns_false`
  - `tests/unit/orchestration/test_orchestrator.py::test_fix_error_fixservice_raises_propagates`
- **`_make_error`** (unknown): PASS -- 3 test(s) call `_make_error` directly
  - `tests/test_pef_p27_fix_orchestrator_per_error_t.py::test_get_progress_temperature_reflects_current_error_not_global_retry_count`
  - `tests/test_pef_p27_fix_orchestrator_per_error_t.py::test_run_session_persists_correct_counts_when_error_left_unfixed`
  - `tests/test_pef_p27_fix_orchestrator_per_error_t.py::test_fixservice_constructed_once_per_error_not_per_retry_attempt`
- **`_make_orchestrator`** (unknown): PASS -- 12 test(s) call `_make_orchestrator` directly
  - `tests/test_pef_p27_fix_orchestrator_per_error_t.py::test_get_progress_temperature_reflects_current_error_not_global_retry_count`
  - `tests/test_pef_p27_fix_orchestrator_per_error_t.py::test_run_session_persists_correct_counts_when_error_left_unfixed`
  - `tests/test_pef_p27_fix_orchestrator_per_error_t.py::test_fixservice_constructed_once_per_error_not_per_retry_attempt`
  - `tests/test_generator/test_generate_optimizer.py::test_status_completed_when_strategy_succeeds`
  - `tests/test_generator/test_generate_optimizer.py::test_output_dir_created`
  - `tests/test_generator/test_generate_optimizer.py::test_attempts_recorded_for_each_entity_variant`
  - `tests/test_generator/test_generate_optimizer.py::test_successful_attempts_have_success_status`
  - `tests/test_generator/test_generate_optimizer.py::test_files_written_to_output_dir`
  - `tests/test_generator/test_generate_optimizer.py::test_attempts_marked_skipped_when_no_output`
  - `tests/test_generator/test_generate_optimizer.py::test_no_files_written_when_strategy_returns_none`
- **`test_get_progress_temperature_reflects_current_error_not_global_retry_count`** (unknown): FAIL -- WARNING: No tests import or call `test_get_progress_temperature_reflects_current_error_not_global_retry_count`
- **`test_run_session_persists_correct_counts_when_error_left_unfixed`** (unknown): FAIL -- WARNING: No tests import or call `test_run_session_persists_correct_counts_when_error_left_unfixed`
- **`test_fixservice_constructed_once_per_error_not_per_retry_attempt`** (unknown): FAIL -- WARNING: No tests import or call `test_fixservice_constructed_once_per_error_not_per_retry_attempt`
- **`FakeFixService`** (unknown): FAIL -- WARNING: No tests import or call `FakeFixService`
- **`attempt_fix_impl`** (unknown): PASS -- 1 test(s) call `attempt_fix_impl` directly
  - `tests/test_pef_p27_fix_orchestrator_per_error_t.py::test_get_progress_temperature_reflects_current_error_not_global_retry_count`
- **`FakeFixService.__init__`** (unknown): FAIL -- WARNING: No tests import or call `__init__`
- **`FakeFixService.attempt_fix`** (unknown): PASS -- 6 test(s) call `attempt_fix` directly
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_dev_force_success_marks_fixed_and_updates_session`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_workspace_validation_failure_raises_fixserviceerror`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_returns_false_marks_attempt_failed`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_success_but_verification_fails_restores_and_returns_false`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_and_verify_success_marks_fixed_and_updates_session_and_state_manager`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_inner_exception_after_applying_raises_and_restores_backup`

**Coverage summary:** 5/10 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (5/10 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pef_p27_fix_orchestrator_per_error_t.py for the finding
