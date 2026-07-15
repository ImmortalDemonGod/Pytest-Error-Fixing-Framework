# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/services/pytest/runner.py`
**Commit:** `22275a7`
**Generated:** 2026-07-15T18:09:09Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/services/pytest/runner.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T18:09:09Z"
```

## Claim(s)

1. implements the converged plan for the finding per its acceptance condition
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L51](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L51)
- **Requirements Verified:** write-code: implement the converged plan within scope

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`22275a7`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/22275a7dafe45a87b09d97cbaba64e701db60c36))

- [`src/branch_fixer/services/pytest/runner.py#L218-L221`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/22275a7dafe45a87b09d97cbaba64e701db60c36/src/branch_fixer/services/pytest/runner.py#L218-L221)
- [`src/branch_fixer/services/pytest/runner.py#L390`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/22275a7dafe45a87b09d97cbaba64e701db60c36/src/branch_fixer/services/pytest/runner.py#L390)
- [`src/branch_fixer/services/pytest/runner.py#L393`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/22275a7dafe45a87b09d97cbaba64e701db60c36/src/branch_fixer/services/pytest/runner.py#L393)
- [`src/branch_fixer/services/pytest/runner.py#L397-L402`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/22275a7dafe45a87b09d97cbaba64e701db60c36/src/branch_fixer/services/pytest/runner.py#L397-L402)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`PytestRunner`** (L218-L221): PASS -- 24 test(s) call `PytestRunner` directly
  - `tests/test_pef_p16_fix_runner_nodeid_unpacking.py::test_format_test_failures_nodeid_without_double_colons_handled_gracefully`
  - `tests/test_pef_p16_fix_runner_nodeid_unpacking.py::test_marker_skip_counted_as_skipped_not_passed`
  - `tests/unit/pytest/test_runner.py::test_defaults_to_cwd_when_no_working_dir`
  - `tests/unit/core/test_verify_fix_workflow.py::test_fix_workflow`
  - `tests/unit/services/pytest/test_runner.py::test_init_with_working_dir`
  - `tests/unit/services/pytest/test_runner.py::test_init_without_working_dir`
  - `tests/unit/services/pytest/test_runner.py::test_run_test_successful_flow`
  - `tests/unit/services/pytest/test_runner.py::test_run_test_with_pytest_main_exception_calls_cleanup_and_propagates`
  - `tests/unit/services/pytest/test_runner.py::test_run_test_build_args_called_with_parameters`
  - `tests/unit/services/pytest/test_runner.py::test_verify_fix_success_return_true`
- **`PytestRunner.format_test_failures`** (L390): PASS -- 8 test(s) call `format_test_failures` directly
  - `tests/test_pef_p16_fix_runner_nodeid_unpacking.py::test_format_test_failures_nodeid_without_double_colons_handled_gracefully`
  - `tests/unit/pytest/test_runner.py::test_format_test_failures_empty`
  - `tests/unit/pytest/test_runner.py::test_format_test_failures_includes_failed`
  - `tests/unit/pytest/test_runner.py::test_format_test_failures_excludes_passed`
  - `tests/unit/pytest/test_runner.py::test_no_session_returns_empty`
  - `tests/unit/services/pytest/test_runner.py::test_format_test_failures_no_session`
  - `tests/unit/services/pytest/test_runner.py::test_format_test_failures_single_failed_with_messages`
  - `tests/unit/services/pytest/test_runner.py::test_format_test_failures_nodeid_without_double_colons_handled_gracefully`
- **`PytestRunner._handle_outcome_logic`** (L393): FAIL -- WARNING: No tests import or call `_handle_outcome_logic`

**Coverage summary:** 2/3 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (2/3 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

runner.py for the finding
