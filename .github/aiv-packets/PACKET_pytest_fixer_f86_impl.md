# AIV Verification Packet (v2.2)

## Identification

| Field | Value |
|-------|-------|
| **Repository** | github.com/ImmortalDemonGod/aiv-protocol |
| **Change ID** | pytest-fixer-f86-impl |
| **Commits** | `b677cd7`, `bfb3175`, `28ebb13`, `5c42e8e`, `e39d356`, `0310482`, `ca5028a`, `dd08b9a`, `43dd153` |
| **Head SHA** | `43dd153` |
| **Base SHA** | `3a24eaf` |
| **Created** | 2026-06-21T09:19:36Z |

## Classification

```yaml
classification:
  risk_tier: R2
  sod_mode: S0
  critical_surfaces: []
  blast_radius: component
  classification_rationale: >
    R2: commit 5c42e8e changes uv.lock — upgrades requires-python from >=3.11 to
    >=3.13 and moves hypothesis from a direct dev-dependency to the 'dev' optional-extra.
    A Python interpreter version constraint change in the dependency manifest is an R2
    trigger per §5.1 (dependency-manifest changes that alter the runtime requirement).
    Additionally commit 43dd153 modifies an existing test file (test_workspace_validator.py)
    by adding a @pytest.mark.skipif decorator, which is a behavioral oracle change even
    though the production code path is unaffected. Neither change rises to R3 (no
    cryptographic surface, no auth boundary, no data-at-rest schema change) but both
    exceed the R1 threshold of 'new test files only / comment/doc edits'.
  classified_by: "ImmortalDemonGod"
  classified_at: "2026-06-21T09:19:36Z"
```

## Claims

1. _create_and_push_pr calls git push before gh pr create so the branch exists on remote when GitHub receives the PR request
2. push failure returns False immediately without calling create_pull_request_sync
3. Absence of push or PR call when service is None: _create_and_push_pr does NOT invoke push or create_pull_request_sync; returns False immediately
4. Four inherited tests in tests/unit/utils/test_cli.py were modified in commit bfb3175 because their old oracles encoded the F86 bug; justification filed at .aiv/oracle-corrections/pytest-fixer-f86-impl.md (commit e39d356)
5. _create_and_push_pr ordering test asserts push is called before create_pull_request_sync using assert_has_calls with any_order=False
6. push-fails test asserts create_pull_request_sync is NOT called when push returns False
7. all four _create_and_push_pr tests pass under the corrected push-first implementation (commit bfb3175)
8. Evidence classes A through F are documented for F86 with SHA-pinned canonical intent https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15
9. LIVE-FIRE-PUSH gate passed: git push to local bare remote succeeded with branch listed (commit b677cd7)
10. PUSH-FIRST gate passed: push at line 223 precedes create_pull_request_sync at line 228

---

## Evidence References

| # | Evidence File | Commit SHA | Classes |
|---|---------------|------------|---------|
| 1 | EVIDENCE_BRANCH_FIXER_UTILS_CLI.md | `b677cd7` | A, B, E |
| 2 | EVIDENCE_TESTS_UNIT_UTILS_TEST_CLI.md | `bfb3175` | A, B, E |
| 3 | EVIDENCE_.GITHUB_AIV_PACKETS_F86_PUSH_BEFORE_PR.MD.md | `28ebb13` | A, B, E |



### Class A (Behavioral / Direct Execution Evidence)

**Claim 7:** RETURN-CONTRACT gate — 4 tests pass

https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/commit/bfb3175

`.venv/bin/python -m pytest tests/unit/utils/test_cli.py -k "create_and_push_pr" -v`

```
tests/unit/utils/test_cli.py::TestCLI::test__create_and_push_pr_pr_and_push_success PASSED
tests/unit/utils/test_cli.py::TestCLI::test__create_and_push_pr_push_fails_returns_false PASSED
tests/unit/utils/test_cli.py::TestCLI::test__create_and_push_pr_pr_creation_returns_false_considered_success PASSED
tests/unit/utils/test_cli.py::TestCLI::test__create_and_push_pr_pr_creation_raises_propagates PASSED
4 passed, 51 deselected in 0.13s
```

**Claim 4:** ANTI-REGRESSION — full unit suite

https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/commit/43dd153

`.venv/bin/python -m pytest tests/unit/ --tb=short`

Result: `631 passed, 1 skipped in 3.85s` — zero net-new failures. The prior `--ignore` workaround for hypothesis-dependent files is removed; commit `43dd153` adds `skipif(os.getuid()==0)` to `test_validate_workspace_dir_not_accessible` (root bypasses `chmod 0o000`), and `uv sync --extra dev` installs `hypothesis` so both previously-excluded files now collect and pass.

**Claim 9:** LIVE-FIRE-PUSH gate

https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/commit/b677cd7

Local bare-repo git push (`git init --bare /tmp/test-remote-f86 && git remote add test-remote /tmp/test-remote-f86 && git push test-remote HEAD && git -C /tmp/test-remote-f86 branch`). Output: branch `fix/pytest-fixer-f86` listed after push. All commands exit 0. Teardown clean.

### Class B (Referential Evidence)

**Claim 1:** [`src/branch_fixer/utils/cli.py#L223`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7/src/branch_fixer/utils/cli.py#L223) — push is called here (commit `b677cd7`)

**Claim 8:** [`/.github/aiv-packets/f86-push-before-pr.md#L1`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/28ebb13/.github/aiv-packets/f86-push-before-pr.md#L1) — evidence file path at commit `28ebb13` with A-F coverage and SHA 697ab7f canonical intent (commit `28ebb13`)

**Claim 10:** [`src/branch_fixer/utils/cli.py#L228`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7/src/branch_fixer/utils/cli.py#L228) — create_pull_request_sync called here, after push (commit `b677cd7`)

**Scope Inventory** (SHA-pinned)

- [`src/branch_fixer/utils/cli.py#L219-L233`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7/src/branch_fixer/utils/cli.py#L219-L233) — post-fix `_create_and_push_pr` body (commit `b677cd7`)
- [`tests/unit/utils/test_cli.py#L203-L233`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/bfb3175/tests/unit/utils/test_cli.py#L203-L233) — updated test block (commit `bfb3175`)
- [`tests/unit/utils/test_cli.py#L211-L214`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/bfb3175/tests/unit/utils/test_cli.py#L211-L214) — ordering assertion with `assert_has_calls` `any_order=False` (commit `bfb3175`)
- [`tests/unit/utils/test_cli.py#L221`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/bfb3175/tests/unit/utils/test_cli.py#L221) — `assert_not_called()` for `create_pull_request_sync` on push failure (commit `bfb3175`)

### Class C (Negative Evidence — What Was Searched For and NOT Found)

- **Other callers of `_create_and_push_pr`:** `grep -rn "_create_and_push_pr" src/ tests/` — no test or production file outside `test_cli.py` and `cli.py` calls `_create_and_push_pr`. No integration test asserts the old PR-before-push ordering.
- **Bug-catalog Skipped set:** F84 (return-type `-> bool` vs `PRDetails`), F58 (mixed sync/async), F59 (`NotImplementedError` stubs) — none fixed here; documented with comment at `cli.py:227`; tracked as deferred.
- **Push logic inside `pr_manager.py` or `repository.py`:** None found; these methods are consumed unchanged.

### Class D (Static Analysis — Lint / Type / Build)

- **mypy** (`mypy src/branch_fixer --ignore-missing-imports`): `Success: no issues found in 43 source files` — exit 0, zero `error:` lines.
- **ruff:** Run by `aiv commit` on each file; any warnings are pre-existing (no new imports or syntax constructs added).
- **NO-BYPASS:** `git log origin/main..HEAD --format="%s %b %H" | grep -Ei "\-\-no\-verify\|--amend"` — empty output; all hooks ran normally.

### Class E (Intent Alignment)

- **Link:** https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15
- **Requirement verified:** audit/02-static-audit.md L15 records that `cli.py:220` calls `create_pull_request_sync()` — which runs `gh pr create --head <branch_name>` — before the branch is pushed to the remote. The push occurred at `cli.py:226` only after `create_pr()` returned. GitHub requires the branch to exist remotely before PR creation.
- **Alignment:** The reordered `_create_and_push_pr` calls `push(branch_name)` at line 223 (before `create_pull_request_sync` at line 228). Push failure returns `False` immediately — `create_pull_request_sync` is never invoked when the branch is absent from the remote. The audit's root-cause (wrong call order) is corrected at the root, verified by PUSH-FIRST gate (grep: push L223 < PR L228) and ORDERING-TEST gate (`assert_has_calls` with `any_order=False` at `test_cli.py:211-214`).

---

### Class F (Provenance — git chain-of-custody of touched test files)

**Test file modified:** `tests/unit/utils/test_cli.py`
**Commit SHA:** `bfb3175`
**Diff reference:** `git show bfb3175 -- tests/unit/utils/test_cli.py`

The test file existed before this change and carried four pre-existing `test__create_and_push_pr_*`
tests that covered `_create_and_push_pr`. Those tests were updated in commit `bfb3175` to
reflect the corrected push-first semantics — they were not deleted, replaced with stubs, or
removed from the collection. The git diff for `bfb3175` shows semantic updates only (changed
`return_value` setup, renamed one test, added `assert_has_calls` ordering assertion, added
`assert_not_called` for the push-fail case). All four tests remain in the file and pass.

**Oracle-corrections record:** The four inherited tests were modified because their original
oracles encoded the F86 bug (PR-before-push call sequence). The per-test justification is
recorded at `.aiv/oracle-corrections/pytest-fixer-f86-impl.md` (commit `e39d356`). In summary:
- `test__create_and_push_pr_pr_and_push_success`: lacked ordering constraint; passed against buggy code
- `test__create_and_push_pr_pr_success_push_fails` (renamed): name and setup encoded PR-before-push as correct
- `test__create_and_push_pr_pr_creation_returns_false_considered_success`: omitted `push.return_value` because push was never called in buggy path
- `test__create_and_push_pr_pr_creation_raises_propagates`: omitted `push.return_value` because PR raised before push in buggy sequence

All four justifications are anchored to F86's ordering invariant, independent of implementation.

**Anti-regression run (631 tests, 0 failures, 1 skipped):**
`.venv/bin/python -m pytest tests/unit/ --tb=short`
Result: `631 passed, 1 skipped in 3.85s` — no pre-existing tests broken.

**Regression fix (commit `43dd153`):** The prior attempt used `--ignore` on two hypothesis-dependent
test files. Commit `43dd153` resolves both root causes: (1) `uv sync --extra dev` installs
`hypothesis` (a dev optional-dependency in `pyproject.toml:33`) so both files now collect;
(2) `test_validate_workspace_dir_not_accessible` is decorated with
`@pytest.mark.skipif(os.getuid()==0, reason=...)` because root bypasses `os.access()` chmod
restrictions, making the PermissionError assertion unreachable when running as root in CI.
The skip is semantically correct: the test cannot exercise the permission guard in a root
environment. Neither `cli.py` nor `_create_and_push_pr` is affected.

---

### Class B (Referential Evidence)

**Scope Inventory** (SHA-pinned; all non-AIV files in this packet's 9 commits plus branch-level inventory)

- [`src/branch_fixer/utils/cli.py#L219-L228`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/src/branch_fixer/utils/cli.py#L219-L228) — post-fix `_create_and_push_pr` body (commit `b677cd7`)
- [`src/branch_fixer/utils/cli.py#L231-L232`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/b677cd7fc47f969dc0f6425c582700da5e1d9d32/src/branch_fixer/utils/cli.py#L231-L232) — push/PR call sites (commit `b677cd7`)
- [`tests/unit/utils/test_cli.py#L203-L233`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/bfb317502943c02762faa05f7630b77d07c315fa/tests/unit/utils/test_cli.py#L203-L233) — updated test block (commit `bfb3175`)
- [`tests/unit/utils/test_cli.py#L210-L214`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/bfb317502943c02762faa05f7630b77d07c315fa/tests/unit/utils/test_cli.py#L210-L214) — `assert_has_calls` ordering assertion (commit `bfb3175`)
- [`tests/unit/utils/test_cli.py#L221`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/bfb317502943c02762faa05f7630b77d07c315fa/tests/unit/utils/test_cli.py#L221) — `assert_not_called()` for push-fail guard (commit `bfb3175`)
- [`uv.lock`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/5c42e8e8c4fd1d5a767432a16274de249616919a/uv.lock) — requires-python upgraded >=3.11→>=3.13; hypothesis moved to dev-extra (commit `5c42e8e`)
- [`tests/unit/utils/test_workspace_validator.py`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/43dd153c9ed0f824537e3083a14507dec20ec3b1/tests/unit/utils/test_workspace_validator.py) — `@pytest.mark.skipif(os.getuid()==0, ...)` added to root-bypass permission test (commit `43dd153`)
- `.gitignore` — AIV scaffolding dirs (`.aiv/launch-briefs/`, `.aiv/plans/`, `.venv`) excluded; changed in commit `88edcf3` (`chore(pipeline): launch-brief artifacts`), which precedes the tests packet's first commit and is outside this packet's 9-commit range — inventoried here for completeness since `git diff origin/main..HEAD` includes it
- [`.github/aiv-packets/f86-push-before-pr.md#L1-L362`](https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/28ebb13/.github/aiv-packets/f86-push-before-pr.md#L1-L362) — full A-F evidence file (commit `28ebb13`)

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

Change 'pytest-fixer-f86-impl': 9 commit(s) across 4 non-AIV file(s) (src/branch_fixer/utils/cli.py, tests/unit/utils/test_cli.py, uv.lock, tests/unit/utils/test_workspace_validator.py). Branch also includes .gitignore modified in the pre-tests launch-brief commit `88edcf3` (outside this packet's commit range). Includes regression fix commit `43dd153` (skipif for root-bypass permission test; hypothesis dev-extra install). Risk tier upgraded to R2 due to uv.lock requires-python constraint change (>=3.11→>=3.13) and oracle-change in test_workspace_validator.py.
