# AIV Evidence File (v1.0)

**File:** `tests/unit/utils/test_f86_pr_ordering.py`
**Commit:** `9c6f8c5`
**Generated:** 2026-06-21T08:59:58Z
**Protocol:** AIV v2.0 + Addendum 2.7 (Zero-Touch Mandate)

---

## Classification (required)

```yaml
classification:
  risk_tier: R1
  sod_mode: S0
  critical_surfaces: []
  blast_radius: "tests/unit/utils/test_f86_pr_ordering.py"
  classification_rationale: "R1: new test file only, no production code changed; tests intentionally fail (RED stage) and document ordering invariant"
  classified_by: "ImmortalDemonGod"
  classified_at: "2026-06-21T08:59:58Z"
```

## Claim(s)

1. _create_and_push_pr calls create_pull_request_sync before push — actual order is ['pr','push'] not ['push','pr']
2. _create_and_push_pr invokes create_pull_request_sync even when push returns False — ghost PR attempted on unpushed branch
3. No existing tests were modified or deleted during this change.

---

## Evidence

### Class E (Intent Alignment)

- **Link:** [https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15)
- **Requirements Verified:** F86 requires RED tests that fail because gh pr create fires before push at cli.py:220-226

### Class B (Referential Evidence)

**Scope Inventory** (SHA: [`9c6f8c5`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/tree/9c6f8c5a4683bee1b6fab539aea41b4654179120))

- [`tests/unit/utils/test_f86_pr_ordering.py#L1-L122`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/9c6f8c5a4683bee1b6fab539aea41b4654179120/tests/unit/utils/test_f86_pr_ordering.py#L1-L122)

### Class A (Execution Evidence)

**Per-symbol test coverage (AST analysis):**

- **`sample_error`** (L1-L122): FAIL -- WARNING: No tests import or call `sample_error`
- **`cli_with_mock_service`** (unknown): FAIL -- WARNING: No tests import or call `cli_with_mock_service`
- **`TestPushBeforePRCreation`** (unknown): FAIL -- WARNING: No tests import or call `TestPushBeforePRCreation`
- **`TestPushFailurePreventsGhPRCreate`** (unknown): FAIL -- WARNING: No tests import or call `TestPushFailurePreventsGhPRCreate`
- **`TestPushBeforePRCreation.test_push_called_before_create_pull_request_sync_guards_against_branch_not_on_remote`** (unknown): FAIL -- WARNING: No tests import or call `test_push_called_before_create_pull_request_sync_guards_against_branch_not_on_remote`
- **`TestPushFailurePreventsGhPRCreate.test_create_pull_request_sync_not_called_when_push_fails_guards_against_ghost_pr`** (unknown): FAIL -- WARNING: No tests import or call `test_create_pull_request_sync_not_called_when_push_fails_guards_against_ghost_pr`

**Coverage summary:** 0/6 symbols verified by tests.

### Code Quality (Linting & Types)

- **ruff:** 0 error(s)
- **mypy:** 

## Claim Verification Matrix

| # | Claim | Type | Evidence | Verdict |
|---|-------|------|----------|---------|
| 1 | _create_and_push_pr calls create_pull_request_sync before pu... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 2 | _create_and_push_pr invokes create_pull_request_sync even wh... | unresolved | No automatic binding available | REVIEW MANUAL REVIEW |
| 3 | No existing tests were modified or deleted during this chang... | structural | Class C not collected | REVIEW MANUAL REVIEW |

**Verdict summary:** 0 verified, 0 unverified, 3 manual review.
---

## Verification Methodology

**Zero-Touch Mandate:** Verifier inspects artifacts only.
Evidence collected by `aiv commit` running: git diff (scope inventory), AST symbol-to-test binding (0/6 symbols verified).
Ruff/mypy results are in Code Quality (not Class A) because they prove syntax/types, not behavior.

---

## Summary

Two RED unit tests pin push-before-PR ordering and push-failure-short-circuit invariants for cli._create_and_push_pr
