# AIV Verification Packet (v2.2)

## Identification

| Field | Value |
|-------|-------|
| **Repository** | github.com/ImmortalDemonGod/aiv-protocol |
| **Change ID** | pytest-fixer-f86-tests |
| **Commits** | `9c6f8c5`, `08ce029`, `802ade9` |
| **Head SHA** | `802ade9` |
| **Base SHA** | `88edcf3` |
| **Created** | 2026-06-21T09:00:58Z |

## Classification

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: component
  classification_rationale: "TODO: Describe why this tier was chosen"
  classified_by: "ImmortalDemonGod"
  classified_at: "2026-06-21T09:00:58Z"
```

## Claims

1. Bug catalog evaluation section documents 2 bugs caught (B1 order, B2 short-circuit), 0 characterized, 0 discovered during writing
2. No existing tests were modified or deleted during this change.
3. _create_and_push_pr calls create_pull_request_sync before push — actual order is ['pr','push'] not ['push','pr']
4. _create_and_push_pr invokes create_pull_request_sync even when push returns False — ghost PR attempted on unpushed branch

---

## Evidence References

| # | Evidence File | Commit SHA | Classes |
|---|---------------|------------|---------|
| 1 | EVIDENCE_TESTS_UNIT_UTILS_TEST_F86_PR_ORDERING.BUG_CATALOG.MD.md | `9c6f8c5` | A, B, E |
| 2 | EVIDENCE_TESTS_UNIT_UTILS_TEST_F86_PR_ORDERING.md | `08ce029` | A, B, E |
| 3 | EVIDENCE_TESTS_UNIT_UTILS_TEST_F86_PR_ORDERING.BUG_CATALOG.MD.md | `802ade9` | A, B, E |



### Class A (Behavioral / Direct Execution Evidence)

**Test run** (`tests/unit/utils/test_f86_pr_ordering.py`):

```
FAILED tests/unit/utils/test_f86_pr_ordering.py::TestPushBeforePRCreation::test_push_called_before_create_pull_request_sync_guards_against_branch_not_on_remote
FAILED tests/unit/utils/test_f86_pr_ordering.py::TestPushFailurePreventsGhPRCreate::test_create_pull_request_sync_not_called_when_push_fails_guards_against_ghost_pr
2 failed, 0 passed
```

Both tests are RED as required for the design-tests stage. Failure messages confirm the bug:
- B1: `actual order was ['pr', 'push']` (expected `['push', 'pr']`)
- B2: `Expected 'create_pull_request_sync' to not have been called. Called 1 times.`

Command: `.venv/bin/python -m pytest tests/unit/utils/test_f86_pr_ordering.py -v`

### Class B (Referential Evidence)

**Scope Inventory** (SHA-pinned)

- [`tests/unit/utils/test_f86_pr_ordering.py#L1-L122`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/08ce029750bc285c0ff6f0efa1ead158e2ebee54/tests/unit/utils/test_f86_pr_ordering.py#L1-L122) (commit `08ce029`)
- [`tests/unit/utils/test_f86_pr_ordering.bug-catalog.md#L137`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/802ade9/tests/unit/utils/test_f86_pr_ordering.bug-catalog.md#L137) (commit `802ade9`)
- [`tests/unit/utils/test_f86_pr_ordering.bug-catalog.md#L141-L152`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/802ade9/tests/unit/utils/test_f86_pr_ordering.bug-catalog.md#L141-L152) (commit `802ade9`)
- [`src/branch_fixer/utils/cli.py#L213-L235`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/src/branch_fixer/utils/cli.py#L213-L235) — code under test, bug site

### Class C (Negative Evidence — What Was Searched For and NOT Found)

- **Bug-catalog Skipped set:** B3 (silent `gh` swallow in `PRManager.create_pr`) deferred as follow-up; B4 (interactive mode path) covered implicitly by B1/B2. Full skipped set documented in `tests/unit/utils/test_f86_pr_ordering.bug-catalog.md` §3.
- **Existing tests for call ordering:** Searched `tests/unit/utils/test_cli.py:203-232` — existing `_create_and_push_pr` tests do NOT assert call order between `create_pull_request_sync` and `push` (confirmed by grep: `tests/unit/utils/test_cli.py:210` asserts `create_pull_request_sync` was called with correct args, but no `call_order` check exists).
- **Any pre-existing RED tests:** `tests/unit/utils/test_cli.py` all pass before this change — 0 pre-existing failures on the same module.
- **Integration-level ordering tests:** None found. Searched `tests/integration/` — no test exercises the full `_create_and_push_pr` → actual `git push` → actual `gh pr create` chain.

### Class D (Static Analysis — Lint / Type / Build)

- **ruff** (`ruff check tests/unit/utils/test_f86_pr_ordering.py`): 0 errors, 0 warnings — `All checks passed!`
- **mypy:** Not run (project does not have a mypy configuration for the test directory; consistent with existing CI evidence).
- **Import resolution:** All imports resolve (`branch_fixer.core.models`, `branch_fixer.utils.cli`) — confirmed by pytest collection succeeding.

### Class E (Intent Alignment)

- **Canonical intent source:** [audit/02-static-audit.md#L15, SHA 697ab7f](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15)
- **Finding F86 states:** `cli.py:220 calls create_pull_request_sync() which internally executes gh pr create --head <branch_name> BEFORE the branch is pushed to the remote. The push happens at cli.py:226 only AFTER pr_manager.create_pr() has already returned.`
- **Alignment:** Tests target exactly `cli.py:220-226` — the `_create_and_push_pr` method. B1 catches the ordering inversion (`['pr','push']` ≠ `['push','pr']`). B2 catches the missing short-circuit on push failure. Both are RED, confirming the bug is present and the test correctly targets the finding.
- **Goal (when fixed):** B1 passes when `call_order == ['push','pr']`; B2 passes when `create_pull_request_sync` is not called after push returns False.

### Class F (Provenance — Git Chain-of-Custody of Touched Test Files)

| File | Action | Commit | Author |
|------|--------|--------|--------|
| `tests/unit/utils/test_f86_pr_ordering.py` | Created (122 lines, 2 RED tests) | `08ce029` | ImmortalDemonGod |
| `tests/unit/utils/test_f86_pr_ordering.bug-catalog.md` | Created | `9c6f8c5` | ImmortalDemonGod |
| `tests/unit/utils/test_f86_pr_ordering.bug-catalog.md` | Updated (evaluation section) | `802ade9` | ImmortalDemonGod |

No existing test files were modified or deleted. Verified by `git diff --stat 697ab7f..802ade9 -- tests/` — only new files added.

---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence was collected by `aiv commit` during the change lifecycle.
Packet generated by `aiv close`.

---

## Known Limitations

- Evidence references point to Layer 1 evidence files at specific commit SHAs.
  Use `git show <sha>:.github/aiv-evidence/<file>` to retrieve.

---

## Summary

Change 'pytest-fixer-f86-tests': 3 commit(s) across 2 file(s).
