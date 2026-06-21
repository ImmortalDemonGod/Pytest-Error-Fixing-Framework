# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/utils/cli.py`
**Commit:** `7c8954b`
**Generated:** 2026-06-21T04:18:33Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/utils/cli.py"
  classification_rationale: "R1: pure Python control-flow change in a single method chain; no subprocess/network/DB boundary; all changed paths covered by updated unit tests"
  classified_by: "ImmortalDemonGod"
  classified_at: "2026-06-21T04:18:33Z"
```

## Claim(s)

1. _handle_ai_fix_choice returns (True, fixed) instead of always True
2. _handle_manual_fix_choice returns (continue, fixed) tuples for fixed/skip/quit paths
3. _process_interactive_error dispatches to tuple-returning handlers; wraps quit/skip inline
4. _process_non_interactive_error now returns bool (was implicit None)
5. _process_all_errors unpacks (should_continue, fixed) and increments success_count
6. process_errors exits 0 when success_count == total_processed, 1 otherwise
7. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L11](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L11)
- **Requirements Verified:** Audit records success_count always 0 and process_errors always returns 1; fix requires all three discard sites to propagate the fix-outcome bool from run_fix_workflow

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`7c8954b`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/7c8954b5a9f643f0a9c62584647023817f7cdb16))

- [`src/branch_fixer/utils/cli.py#L382`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L382)
- [`src/branch_fixer/utils/cli.py#L390`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L390)
- [`src/branch_fixer/utils/cli.py#L393-L394`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L393-L394)
- [`src/branch_fixer/utils/cli.py#L397`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L397)
- [`src/branch_fixer/utils/cli.py#L399`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L399)
- [`src/branch_fixer/utils/cli.py#L402-L403`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L402-L403)
- [`src/branch_fixer/utils/cli.py#L407`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L407)
- [`src/branch_fixer/utils/cli.py#L445`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L445)
- [`src/branch_fixer/utils/cli.py#L448`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L448)
- [`src/branch_fixer/utils/cli.py#L451-L462`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L451-L462)
- [`src/branch_fixer/utils/cli.py#L466-L467`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L466-L467)
- [`src/branch_fixer/utils/cli.py#L471`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L471)
- [`src/branch_fixer/utils/cli.py#L533-L534`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L533-L534)
- [`src/branch_fixer/utils/cli.py#L536-L537`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L536-L537)
- [`src/branch_fixer/utils/cli.py#L539-L540`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/7c8954b5a9f643f0a9c62584647023817f7cdb16/src/branch_fixer/utils/cli.py#L539-L540)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`CLI`** (L382): FAIL -- WARNING: 2 file(s) import `CLI` but 0 tests call it directly
  - Imported by: `tests/unit/utils/test_cli.py`
  - Imported by: `tests/unit/utils/test_cli_f15.py`
- **`CLI._handle_manual_fix_choice`** (L390): PASS -- 2 test(s) call `_handle_manual_fix_choice` directly
  - `tests/unit/utils/test_cli.py::test_handle_manual_fix_choice_fixed_returns_true`
  - `tests/unit/utils/test_cli.py::test_handle_manual_fix_choice_quit_returns_false`
- **`CLI._handle_ai_fix_choice`** (L393-L394): PASS -- 1 test(s) call `_handle_ai_fix_choice` directly
  - `tests/unit/utils/test_cli.py::test_handle_ai_fix_choice_success_and_failure`
- **`CLI._process_interactive_error`** (L397): PASS -- 1 test(s) call `_process_interactive_error` directly
  - `tests/unit/utils/test_cli.py::test__process_interactive_error_calls_correct_handler`
- **`CLI._process_non_interactive_error`** (L399): PASS -- 1 test(s) call `_process_non_interactive_error` directly
  - `tests/unit/utils/test_cli.py::test__process_non_interactive_error_prints_messages`
- **`CLI._process_all_errors`** (L402-L403): PASS -- 6 test(s) call `_process_all_errors` directly
  - `tests/unit/utils/test_cli.py::test__process_all_errors_noninteractive_iterates_all`
  - `tests/unit/utils/test_cli.py::test__process_all_errors_interactive_breaks_on_quit`
  - `tests/unit/utils/test_cli_f15.py::test_success_count_is_one_when_single_non_interactive_fix_succeeds`
  - `tests/unit/utils/test_cli_f15.py::test_success_count_is_zero_when_single_non_interactive_fix_fails`
  - `tests/unit/utils/test_cli_f15.py::test_success_count_tracks_partial_successes_across_multiple_errors`
  - `tests/unit/utils/test_cli_f15.py::test_success_count_equals_total_when_all_fixes_succeed`

**Coverage summary:** 5/6 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 0 error(s)
- **mypy:** 

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | _handle_ai_fix_choice returns (True, fixed) instead of alway... | symbol | 1 test(s) call `CLI._handle_ai_fix_choice` | PASS VERIFIED |
| 2 | _handle_manual_fix_choice returns (continue, fixed) tuples f... | symbol | 2 test(s) call `CLI._handle_manual_fix_choice` | PASS VERIFIED |
| 3 | _process_interactive_error dispatches to tuple-returning han... | symbol | 1 test(s) call `CLI._process_interactive_error` | PASS VERIFIED |
| 4 | _process_non_interactive_error now returns bool (was implici... | symbol | 1 test(s) call `CLI._process_non_interactive_error` | PASS VERIFIED |
| 5 | _process_all_errors unpacks (should_continue, fixed) and inc... | symbol | 6 test(s) call `CLI._process_all_errors` | PASS VERIFIED |
| 6 | process_errors exits 0 when success_count == total_processed... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 7 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 5 verified, 0 unverified, 2 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (5/6 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Fix success_count always-zero bug by propagating run_fix_workflow bool through all three caller sites
