# AIV Evidence File (v1.0)

**File:** `tests/unit/utils/test_cli.py`
**Commit:** `b677cd7`
**Generated:** 2026-06-21T09:16:45Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/unit/utils/test_cli.py"
  classification_rationale: "Test-only change; no production logic changed; same risk tier as the production commit it validates"
  classified_by: "ImmortalDemonGod"
  classified_at: "2026-06-21T09:16:45Z"
```

## Claim(s)

1. _create_and_push_pr ordering test asserts push is called before create_pull_request_sync using assert_has_calls with any_order=False
2. push-fails test asserts create_pull_request_sync is NOT called when push returns False
3. all four _create_and_push_pr tests pass under the corrected push-first implementation
4. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15)
- **Requirements Verified:** audit/02-static-audit.md L15 requires tests to enforce that push precedes PR creation; the ordering assertion directly encodes this invariant

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`b677cd7`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/b677cd7fc47f969dc0f6425c582700da5e1d9d32))

- [`tests/unit/utils/test_cli.py#L4`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/tests/unit/utils/test_cli.py#L4)
- [`tests/unit/utils/test_cli.py#L207`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/tests/unit/utils/test_cli.py#L207)
- [`tests/unit/utils/test_cli.py#L210-L214`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/tests/unit/utils/test_cli.py#L210-L214)
- [`tests/unit/utils/test_cli.py#L216`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/tests/unit/utils/test_cli.py#L216)
- [`tests/unit/utils/test_cli.py#L221`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/tests/unit/utils/test_cli.py#L221)
- [`tests/unit/utils/test_cli.py#L225`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/tests/unit/utils/test_cli.py#L225)
- [`tests/unit/utils/test_cli.py#L231`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/tests/unit/utils/test_cli.py#L231)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`TestCLI`** (L4): FAIL -- WARNING: No tests import or call `TestCLI`
- **`TestCLI.test__create_and_push_pr_pr_and_push_success`** (L207): FAIL -- WARNING: No tests import or call `test__create_and_push_pr_pr_and_push_success`
- **`TestCLI.test__create_and_push_pr_push_fails_returns_false`** (L210-L214): FAIL -- WARNING: No tests import or call `test__create_and_push_pr_push_fails_returns_false`
- **`TestCLI.test__create_and_push_pr_pr_creation_returns_false_considered_success`** (L216): FAIL -- WARNING: No tests import or call `test__create_and_push_pr_pr_creation_returns_false_considered_success`
- **`TestCLI.test__create_and_push_pr_pr_creation_raises_propagates`** (L221): FAIL -- WARNING: No tests import or call `test__create_and_push_pr_pr_creation_raises_propagates`

**Coverage summary:** 0/5 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 0 error(s)
- **mypy:** 

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | _create_and_push_pr ordering test asserts push is called bef... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | push-fails test asserts create_pull_request_sync is NOT call... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 3 | all four _create_and_push_pr tests pass under the corrected ... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 4 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 4 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/5 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Update four _create_and_push_pr tests for push-first semantics; add ordering assertion
