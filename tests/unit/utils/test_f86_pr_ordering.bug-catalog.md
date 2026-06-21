# Bug Catalog — F86: PR Created Before Branch Push

**Target code:** `src/branch_fixer/utils/cli.py:213-235` (`_create_and_push_pr`)  
**Secondary location:** `src/branch_fixer/services/git/pr_manager.py:71-88` (`PRManager.create_pr`)  
**Canonical intent (Class E):**
https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15  
**Test file:** `tests/unit/utils/test_f86_pr_ordering.py`

---

## 1. Code Summary

### Public interface
`CLI._create_and_push_pr(branch_name: str, error: TestError) -> bool`  
Called by `run_fix_workflow` after a fix is generated and applied.  
Contract: push the fix branch to remote, then create a GitHub PR.  
Returns `True` on success (branch pushed + PR created or PR-opt-out), `False` on push failure.

### Load-bearing comments
- Line 224: `# 4) Try pushing to remote` — step comment implies PR creation is step 3, push is step 4.  
  This numbering hard-codes the wrong order in the documentation.

### IO boundaries
- `create_pull_request_sync` → `PRManager.create_pr` → `subprocess.run(["gh", "pr", "create", …])` — network call to GitHub API.
- `push(branch_name)` → `git push origin <branch>` — network call to remote git.

### Branching points
```
_create_and_push_pr(branch_name, error):
  if service AND create_pull_request_sync(branch_name, error):  # <- BUG: gh pr create fires here
      if push(branch_name):        # <- push happens AFTER
          return True
      else:
          return False
  else:
      return True   # PR "failed" but fix is treated as success
```

### Type / magic-string contracts
`PRManager.create_pr` returns a `PRDetails` object (always truthy) even when `gh pr create`
exits non-zero — failures are logged as warnings and swallowed. So
`create_pull_request_sync` always returns truthy, making the `if` branch always true
and masking the gh failure from callers.

### Existing tests (`test_cli.py:204-232`)
Existing tests mock both `create_pull_request_sync` and `push` independently but do NOT
assert the call order between them. They cover the boolean-return logic, not sequencing.

---

## 2. Bug Catalog

### B1 — PRIMARY: `gh pr create` fires before branch exists on remote (ordering bug)

**The failure mode:** `_create_and_push_pr` calls `create_pull_request_sync` (which runs
`gh pr create --head <branch_name>`) at line 220 **before** calling `push(branch_name)` at
line 226. GitHub's API rejects the request because the head branch does not yet exist on
the remote.

**Blast radius:** Every non-interactive automated fix cycle (`--non-interactive`) completes
locally (branch created, fix applied, tests pass) but the GitHub PR is never actually opened.
The CI/review/merge workflow never triggers. The fix sits on a local branch with no visibility.

**Why it's plausible:** The method is named `_create_and_push_pr` — "create" before "push"
mirrors the method name literally. The step comment in the body (`# 4) Try pushing to remote`)
also numbers push as a later step.

**Test type:** Captured-bug / order assertion (unit, call-order mock).

**Self-critique:**
- Catches the specific catalog bug? Yes — asserting `call_order == ['push', 'pr']` fails
  with current code where the actual order is `['pr', 'push']`.
- Passes for wrong-but-stable output? No — order is the observable contract.
- Fails under behavior-preserving refactor? No — we assert order of collaborator calls,
  not internal implementation.

---

### B2 — SECONDARY: push failure does not prevent PR creation

**The failure mode:** Because `create_pull_request_sync` is called **first**, if `push`
subsequently fails (network error, no upstream, authentication), the `gh pr create` call
has already been attempted. In the (correctly fixed) implementation, a push failure
must short-circuit and prevent `gh pr create` from running at all.

**Blast radius:** A dangling PR on GitHub pointing to a branch that was never successfully
pushed — the PR diff is empty or nonexistent; any CI that checks out the branch fails.

**Why it's plausible:** The two-step protocol (push + create PR) needs an explicit
short-circuit on push failure. Without ordering, each step is attempted independently.

**Test type:** Negative-path / call-guard assertion (unit).

**Self-critique:**
- Catches the specific bug? Yes — asserting `create_pull_request_sync.assert_not_called()`
  when `push` returns False fails with current code (which calls `create_pull_request_sync`
  before consulting `push` at all).
- Passes for wrong-but-stable output? No.
- Fails under non-behavior refactor? No — asserts on observable collaborator calls.

---

### B3 — `PRManager.create_pr` silently swallows `gh` non-zero exit

**The failure mode:** `pr_manager.py:71-88` catches `gh pr create` failures as warnings
and still returns a truthy `PRDetails` object. Callers cannot distinguish "PR created
on GitHub" from "gh unavailable or rejected".

**Blast radius:** The log says "Created pull request successfully" (cli.py:223) even when
GitHub returned an error.

**Why it's plausible:** The original design treated `gh` as optional (no-gh = just log).
The same pattern was extended to cover all `gh` failures.

**Test type:** Contract-pin (unit, `PRManager.create_pr` return-value contract).

**Self-critique:**
- Catches B3? Yes — test checks that `create_pr` url field is `None` (failure) and the
  return value reflects the gh exit code, but the current code always returns a truthy
  object regardless.
- However, fixing B3 alone without fixing B1 and B2 does not restore correct PR-creation
  behavior — B1 is the root cause. B3 is a secondary enabler.

---

## 3. Skipped / Deferred

| Bug class | Why skipped |
|---|---|
| Integration: actual `gh pr create` against real GitHub remote | Requires authenticated GitHub CLI and remote repo — out of scope for unit stage; deferred to integration suite |
| B3 (silent gh swallow) test | Architectural-correctness but not primary-deliverable-dependency for this ticket; the ordering fix (B1+B2) is the primary deliverable. B3 test deferred as follow-up issue. |
| Push partial failure (some refs fail) | `push()` returns bool — partial failure is out of scope until `push()` returns richer status |
| Interactive mode PR ordering | Interactive mode prompts user before calling `_create_and_push_pr` — same code path, so B1/B2 tests cover it implicitly |

---

## 4. Evaluation (post-run)

| Category | Count | Notes |
|---|---|---|
| Bugs caught (test RED first run) | 2 | B1: order `['pr','push']` ≠ `['push','pr']`; B2: `create_pull_request_sync` called despite `push→False` |
| Bugs characterized (test GREEN first run) | 0 | No tests passed — all two tests are RED |
| Bugs discovered during writing | 0 | Catalog was accurate; no additional bugs surfaced |

**Manual verification command:**
```
.venv/bin/python -m pytest tests/unit/utils/test_f86_pr_ordering.py -v
```
**Result:** 2 failed / 0 passed — both tests are RED as required for the design-tests stage.

**B3 evaluation:** `PRManager.create_pr` silently swallows `gh` failures — deferred as follow-up;
root cause (B1 ordering) is the primary deliverable for F86.
