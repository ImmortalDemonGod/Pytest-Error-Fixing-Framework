# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/core/models.py`
**Commit:** `53ab8b5`
**Generated:** 2026-07-15T18:14:04Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/core/models.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T18:14:04Z"
```

## Claim(s)

1. implements the converged plan for the finding per its acceptance condition
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L65](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L65)
- **Requirements Verified:** write-code: implement the converged plan within scope

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`53ab8b5`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/53ab8b53f52d74624c84e302f6d67d4b92179795))

- [`src/branch_fixer/core/models.py#L1-L114`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/53ab8b53f52d74624c84e302f6d67d4b92179795/src/branch_fixer/core/models.py#L1-L114)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`ErrorDetails`** (L1-L114): PASS -- 36 test(s) call `ErrorDetails` directly
  - `tests/unit/ai/test_ai_manager.py::test_thread_resets_for_new_error`
  - `tests/unit/ai/test_ai_manager.py::test_retry_appends_failure_feedback_to_thread`
  - `tests/unit/ai/test_ai_manager.py::test_retry_does_not_reset_error_id`
  - `tests/unit/ai/test_ai_manager.py::test_stack_trace_none_handled`
  - `tests/unit/orchestration/test_orchestrator.py::test_run_session_updates_counts_and_marks_failed`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_dev_force_success_marks_fixed_and_updates_session`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_workspace_validation_failure_raises_fixserviceerror`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_returns_false_marks_attempt_failed`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_success_but_verification_fails_restores_and_returns_false`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_and_verify_success_marks_fixed_and_updates_session_and_state_manager`
- **`FixAttempt`** (unknown): PASS -- 4 test(s) call `FixAttempt` directly
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_fix_attempt_creation`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_fix_attempt_default_values`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_fix_attempt_round_trip`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_test_error_round_trip`
- **`TestError`** (unknown): PASS -- 23 test(s) call `TestError` directly
  - `tests/unit/ai/test_ai_manager.py::test_thread_resets_for_new_error`
  - `tests/unit/ai/test_ai_manager.py::test_retry_appends_failure_feedback_to_thread`
  - `tests/unit/ai/test_ai_manager.py::test_retry_does_not_reset_error_id`
  - `tests/unit/ai/test_ai_manager.py::test_stack_trace_none_handled`
  - `tests/unit/orchestration/test_orchestrator.py::test_run_session_updates_counts_and_marks_failed`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_dev_force_success_marks_fixed_and_updates_session`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_workspace_validation_failure_raises_fixserviceerror`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_returns_false_marks_attempt_failed`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_success_but_verification_fails_restores_and_returns_false`
  - `tests/unit/orchestration/test_fix_service.py::test_attempt_fix_apply_and_verify_success_marks_fixed_and_updates_session_and_state_manager`
- **`CodeChanges`** (unknown): PASS -- 16 test(s) call `CodeChanges` directly
  - `tests/test_generator/test_verify_fixer.py::test_returns_unchanged_result_when_all_passed`
  - `tests/test_generator/test_verify_fixer.py::test_calls_ai_manager_for_failing_file`
  - `tests/test_generator/test_verify_fixer.py::test_calls_change_applier_with_ai_output`
  - `tests/test_generator/test_verify_fixer.py::test_reruns_verification_after_fixes`
  - `tests/test_generator/test_verify_fixer.py::test_stops_after_successful_fix`
  - `tests/test_generator/test_verify_fixer.py::test_retries_up_to_max_attempts_on_apply_failure`
  - `tests/test_generator/test_verify_fixer.py::test_retries_when_verify_fails_after_apply`
  - `tests/test_generator/test_verify_fixer.py::test_rejects_fix_that_removes_all_tests`
  - `tests/test_generator/test_verify_fixer.py::test_groups_failures_by_file`
  - `tests/unit/code/test_change_applier.py::test_strips_markdown_code_fences`
- **`ErrorDetails.to_dict`** (unknown): PASS -- 5 test(s) call `to_dict` directly
  - `tests/test_generator/test_core_models.py::test_to_dict_contains_required_keys`
  - `tests/test_generator/test_core_models.py::test_to_dict_shape`
  - `tests/unit/orchestration/test_orchestrator.py::test_to_dict_and_create_snapshot_with_errors_and_warnings`
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_round_trip`
  - `tests/unit/orchestration/test_orchestrator.py::test_to_dict_handles_none_current_error`
- **`ErrorDetails.from_dict`** (unknown): PASS -- 2 test(s) call `from_dict` directly
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_round_trip`
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_missing_required_keys_raises`
- **`FixAttempt.to_dict`** (unknown): PASS -- 5 test(s) call `to_dict` directly
  - `tests/test_generator/test_core_models.py::test_to_dict_contains_required_keys`
  - `tests/test_generator/test_core_models.py::test_to_dict_shape`
  - `tests/unit/orchestration/test_orchestrator.py::test_to_dict_and_create_snapshot_with_errors_and_warnings`
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_round_trip`
  - `tests/unit/orchestration/test_orchestrator.py::test_to_dict_handles_none_current_error`
- **`FixAttempt.from_dict`** (unknown): PASS -- 2 test(s) call `from_dict` directly
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_round_trip`
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_missing_required_keys_raises`
- **`TestError.start_fix_attempt`** (unknown): PASS -- 11 test(s) call `start_fix_attempt` directly
  - `tests/unit/orchestration/test_fix_service.py::test_handle_failed_attempt_propagates_update_errors_as_fixserviceerror`
  - `tests/unit/orchestration/test_fix_service.py::test_verify_fix_behavior`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_start_fix_attempt`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_start_fix_attempt_on_fixed_error`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_start_fix_attempt_integrity`
  - `tests/unit/core/test_models.py::test_start_fix_attempt`
  - `tests/unit/core/test_models.py::test_mark_attempt_success`
  - `tests/unit/core/test_models.py::test_mark_attempt_failed`
  - `tests/unit/core/test_models.py::test_cannot_start_attempt_when_fixed`
  - `tests/unit/core/test_models.py::test_mark_fixed_with_foreign_attempt`
- **`TestError.mark_fixed`** (unknown): PASS -- 6 test(s) call `mark_fixed` directly
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_mark_fixed`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_mark_fixed_with_invalid_attempt`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_mark_fixed_changes_status_only_once`
  - `tests/unit/core/test_models.py::test_mark_attempt_success`
  - `tests/unit/core/test_models.py::test_cannot_start_attempt_when_fixed`
  - `tests/unit/core/test_models.py::test_mark_fixed_with_foreign_attempt`
- **`TestError.mark_attempt_failed`** (unknown): PASS -- 4 test(s) call `mark_attempt_failed` directly
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_mark_attempt_failed`
  - `tests/unit/core/test_branch_fixer_core_models_GS.py::test_mark_attempt_failed_with_invalid_attempt`
  - `tests/unit/core/test_models.py::test_mark_attempt_failed`
  - `tests/unit/core/test_models.py::test_mark_failed_with_foreign_attempt`
- **`TestError.to_dict`** (unknown): PASS -- 5 test(s) call `to_dict` directly
  - `tests/test_generator/test_core_models.py::test_to_dict_contains_required_keys`
  - `tests/test_generator/test_core_models.py::test_to_dict_shape`
  - `tests/unit/orchestration/test_orchestrator.py::test_to_dict_and_create_snapshot_with_errors_and_warnings`
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_round_trip`
  - `tests/unit/orchestration/test_orchestrator.py::test_to_dict_handles_none_current_error`
- **`TestError.from_dict`** (unknown): PASS -- 2 test(s) call `from_dict` directly
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_round_trip`
  - `tests/unit/orchestration/test_orchestrator.py::test_from_dict_missing_required_keys_raises`

**Coverage summary:** 13/13 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (13/13 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

models.py for the finding
