# AIV Evidence File (v1.0)

**File:** `src/branch_fixer/utils/cli.py`
**Commit:** `3a24eaf`
**Generated:** 2026-06-21T09:15:27Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "src/branch_fixer/utils/cli.py"
  classification_rationale: "Two-file, ~18-line reorder in one local method; no schema change, no new dependency, no public API contract change"
  classified_by: "ImmortalDemonGod"
  classified_at: "2026-06-21T09:15:27Z"
```

## Claim(s)

1. _create_and_push_pr calls git push before gh pr create so the branch exists on remote when GitHub receives the PR request
2. push failure returns False immediately without calling create_pull_request_sync
3. service=None returns False (push impossible)
4. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15)
- **Requirements Verified:** audit/02-static-audit.md L15 records that gh pr create is invoked before git push, causing GitHub to reject the PR because the head branch does not exist on the remote; fix requires push-first ordering

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`3a24eaf`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/3a24eaf3c0dc0cff5ae0559ef1af6a1d60c8979c))

- [`src/branch_fixer/utils/cli.py#L219-L228`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/3a24eaf3c0dc0cff5ae0559ef1af6a1d60c8979c/src/branch_fixer/utils/cli.py#L219-L228)
- [`src/branch_fixer/utils/cli.py#L231-L232`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/3a24eaf3c0dc0cff5ae0559ef1af6a1d60c8979c/src/branch_fixer/utils/cli.py#L231-L232)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`CLI`** (L219-L228): FAIL -- WARNING: 2 file(s) import `CLI` but 0 tests call it directly
  - Imported by: `tests/unit/utils/test_cli.py`
  - Imported by: `tests/unit/utils/test_f86_pr_ordering.py`
- **`CLI._create_and_push_pr`** (L231-L232): PASS -- 6 test(s) call `_create_and_push_pr` directly
  - `tests/unit/utils/test_cli.py::test__create_and_push_pr_pr_and_push_success`
  - `tests/unit/utils/test_cli.py::test__create_and_push_pr_pr_success_push_fails`
  - `tests/unit/utils/test_cli.py::test__create_and_push_pr_pr_creation_returns_false_considered_success`
  - `tests/unit/utils/test_cli.py::test__create_and_push_pr_pr_creation_raises_propagates`
  - `tests/unit/utils/test_f86_pr_ordering.py::test_push_called_before_create_pull_request_sync_guards_against_branch_not_on_remote`
  - `tests/unit/utils/test_f86_pr_ordering.py::test_create_pull_request_sync_not_called_when_push_fails_guards_against_ghost_pr`

**Coverage summary:** 1/2 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 0 error(s)
- **mypy:** 

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | _create_and_push_pr calls git push before gh pr create so th... | symbol | 6 test(s) call `CLI._create_and_push_pr` | PASS VERIFIED |
| 2 | push failure returns False immediately without calling creat... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 3 | service=None returns False (push impossible) | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 4 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 1 verified, 0 unverified, 3 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (1/2 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Reorder _create_and_push_pr: push branch to remote first, then create PR
