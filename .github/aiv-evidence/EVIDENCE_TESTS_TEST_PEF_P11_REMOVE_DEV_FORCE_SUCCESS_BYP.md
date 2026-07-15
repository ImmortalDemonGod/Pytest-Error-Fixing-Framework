# AIV Evidence File (v1.0)

**File:** `tests/test_pef_p11_remove_dev_force_success_byp.py`
**Commit:** `06add09`
**Generated:** 2026-07-15T18:17:09Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/test_pef_p11_remove_dev_force_success_byp.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T18:17:09Z"
```

## Claim(s)

1. RED test pins the finding's defect against the cited baseline
2. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L24](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L24)
- **Requirements Verified:** design-tests: a failing test that names the finding's defect

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`06add09`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/06add096d507a8ffbb2527ab882d9c1058754f85))

- [`tests/test_pef_p11_remove_dev_force_success_byp.py#L1-L98`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/06add096d507a8ffbb2527ab882d9c1058754f85/tests/test_pef_p11_remove_dev_force_success_byp.py#L1-L98)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`tmp_file`** (L1-L98): FAIL -- WARNING: No tests import or call `tmp_file`
- **`fake_ai_manager`** (unknown): FAIL -- WARNING: No tests import or call `fake_ai_manager`
- **`fake_change_applier`** (unknown): FAIL -- WARNING: No tests import or call `fake_change_applier`
- **`fake_test_runner`** (unknown): FAIL -- WARNING: No tests import or call `fake_test_runner`
- **`workspace_validator_ok`** (unknown): FAIL -- WARNING: No tests import or call `workspace_validator_ok`
- **`test_attempt_fix_always_calls_generate_fix_no_dev_force_shortcut`** (unknown): FAIL -- WARNING: No tests import or call `test_attempt_fix_always_calls_generate_fix_no_dev_force_shortcut`
- **`V`** (unknown): FAIL -- WARNING: No tests import or call `V`
- **`V.validate_workspace`** (unknown): PASS -- 8 test(s) call `validate_workspace` directly
  - `tests/unit/utils/test_workspace_validator.py::test_validate_workspace_success`
  - `tests/unit/utils/test_workspace_validator.py::test_validate_workspace_dir_not_found`
  - `tests/unit/utils/test_workspace_validator.py::test_validate_workspace_dir_not_accessible`
  - `tests/unit/utils/test_workspace_validator.py::test_validate_workspace_no_git_dir`
  - `tests/unit/utils/test_workspace_validator.py::test_validate_workspace_bare_repo`
  - `tests/unit/utils/test_workspace_validator.py::test_validate_workspace_invalid_repo`
  - `tests/unit/utils/test_workspace_validator.py::test_validate_workspace_unknown_error`
  - `tests/unit/utils/test_workspace_validator.py::test_validate_then_check_dependencies_round_trip`
- **`V.check_dependencies`** (unknown): PASS -- 3 test(s) call `check_dependencies` directly
  - `tests/unit/utils/test_workspace_validator.py::test_validate_then_check_dependencies_round_trip`
  - `tests/unit/utils/test_workspace_validator.py::test_check_dependencies_success`
  - `tests/unit/utils/test_workspace_validator.py::test_check_dependencies_missing`

**Coverage summary:** 2/9 symbols verified by tests.

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
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (2/9 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

test_pef_p11_remove_dev_force_success_byp.py for the finding
