# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/services/ai/manager.py`
**Commit:** `b9d0a1b`
**Generated:** 2026-07-15T18:14:10Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/services/ai/manager.py"
  classification_rationale: "R1"
  classified_by: "Claude"
  classified_at: "2026-07-15T18:14:10Z"
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

**Scope Inventory** (SHA: [`b9d0a1b`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/b9d0a1be6b1083d4f0126c0ee81beee50345e158))

- [`src/branch_fixer/services/ai/manager.py#L317`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b9d0a1be6b1083d4f0126c0ee81beee50345e158/src/branch_fixer/services/ai/manager.py#L317)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`AIManager`** (L317): PASS -- 30 test(s) call `AIManager` directly
  - `tests/unit/ai/test_ai_manager.py::test_stores_model`
  - `tests/unit/ai/test_ai_manager.py::test_stores_base_temperature`
  - `tests/unit/ai/test_ai_manager.py::test_no_api_key_does_not_mutate_env`
  - `tests/unit/ai/test_ai_manager.py::test_api_key_stored_on_instance`
  - `tests/unit/ai/test_ai_manager.py::test_api_key_none_does_not_mutate_env`
  - `tests/unit/ai/test_ai_manager.py::test_thread_starts_empty`
  - `tests/unit/ai/test_ai_manager.py::test_current_error_id_starts_none`
  - `tests/unit/ai/test_ai_manager.py::test_raises_on_temperature_below_zero`
  - `tests/unit/ai/test_ai_manager.py::test_raises_on_temperature_above_one`
  - `tests/unit/ai/test_ai_manager.py::test_boundary_zero_is_accepted`
- **`AIManager._parse_response`** (unknown): PASS -- 5 test(s) call `_parse_response` directly
  - `tests/unit/ai/test_ai_manager.py::test_parses_modified_code_marker`
  - `tests/unit/ai/test_ai_manager.py::test_parses_minimal_response`
  - `tests/unit/ai/test_ai_manager.py::test_fallback_on_no_marker`
  - `tests/unit/ai/test_ai_manager.py::test_parses_multiline_modified_code`
  - `tests/unit/ai/test_ai_manager.py::test_codechanges_has_no_original_code_field`

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

manager.py for the finding
