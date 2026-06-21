# Oracle Corrections — change-id: `pytest-fixer-f86-impl`

**Finding:** F86 — `_create_and_push_pr` calls `create_pull_request_sync` before `push`, causing
GitHub to reject PR creation because the head branch does not yet exist on the remote.

**Canonical intent:**
https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15

**Principle:** The correctness invariant for `_create_and_push_pr` is:
> `push(branch_name)` MUST be called — and MUST succeed — before `create_pull_request_sync`
> is invoked. If push fails, PR creation MUST NOT be attempted.

Each justification below is anchored to **F86's ordering invariant**, not to the implementation
that was written to fix it.

---

## Test 1: `test__create_and_push_pr_pr_and_push_success`

**Status:** Modified — ordering assertion added; mock-setup order swapped.

### What the old oracle asserted
```python
mock_service.git_repo.create_pull_request_sync.return_value = True
mock_service.git_repo.push.return_value = True
res = cli._create_and_push_pr("fix-branch", sample_error)
assert res is True
mock_service.git_repo.create_pull_request_sync.assert_called_with("fix-branch", sample_error)
mock_service.git_repo.push.assert_called_with("fix-branch")
```

### Why the old oracle was wrong (independent of any implementation)

**The bug F86 is an ordering bug.** The defect is that `create_pull_request_sync` is called
before `push`. The old test verified that **both** methods were called, but it imposed **no
ordering constraint**: the two `assert_called_with` assertions are order-independent — they pass
regardless of which function was called first.

This means the old test **passed against the buggy code** (PR-before-push) and would also pass
against the correct code (push-before-PR). A test that cannot distinguish between correct and
incorrect call sequences is **a wrong oracle for an ordering defect.**

The correct oracle must use `assert_has_calls([call.push(...), call.create_pull_request_sync(...)],
any_order=False)` to assert the invariant: push is called before PR creation. Without that
constraint, the test encodes no meaningful claim about the property F86 says must hold.

---

## Test 2: `test__create_and_push_pr_pr_success_push_fails` (REMOVED / renamed to `test__create_and_push_pr_push_fails_returns_false`)

**Status:** Removed from origin/main; replaced by `test__create_and_push_pr_push_fails_returns_false`.

### What the old oracle asserted
```python
mock_service.git_repo.create_pull_request_sync.return_value = True  # PR set up as succeeding
mock_service.git_repo.push.return_value = False
res = cli._create_and_push_pr("fix-branch", sample_error)
assert res is False
```

### Why the old oracle was wrong (independent of any implementation)

The old test name itself names the bug: **"PR success, push fails."** That title describes a
scenario where PR creation is invoked first (succeeds), and push is attempted second (fails).
That call sequence IS the defect — `create_pull_request_sync` called before `push`.

The old oracle:
1. Set up `create_pull_request_sync.return_value = True`, establishing the expectation that PR
   creation was the first call that could succeed or fail.
2. Set up `push.return_value = False`, establishing push as the secondary call.
3. Asserted the result was `False` — consistent with the old buggy code path: PR succeeds →
   push fails → return False.

This test was **testing the bug as correct behaviour.** The scenario it exercised — PR invoked
before push, PR succeeds, push fails, returns False — is precisely the F86 defect sequence.

The correct oracle for "push fails" is: push is called first, fails, PR is **NOT called at all**
(assert `create_pull_request_sync.assert_not_called()`), returns False. The old test did not
express this; it expressed the opposite. It was wrong by design, not by omission.

---

## Test 3: `test__create_and_push_pr_pr_creation_returns_false_considered_success`

**Status:** Modified — `mock_service.git_repo.push.return_value = True` added.

### What the old oracle asserted
```python
cli.service = mock_service
mock_service.git_repo.create_pull_request_sync.return_value = False
res = cli._create_and_push_pr("fix-branch", sample_error)
assert res is True
```
No `push.return_value` was set.

### Why the old oracle was wrong (independent of any implementation)

In the old buggy code path for this scenario:
```
if self.service and self.service.git_repo.create_pull_request_sync(...):  # PR called first
    ...
else:
    return True   # PR returned falsy → return True; push is NEVER called
```

The old test **deliberately omitted `push.return_value`** because in the buggy implementation,
`push` was never called when `create_pull_request_sync` returned False. The omission encoded
the assumption: **push does not matter here because it is never invoked.**

That assumption IS the F86 bug. The correct invariant says push MUST be called first. A test
that is valid only if push is not called — and that passes only because the method skips push
entirely — is an oracle that encodes the buggy control flow.

The old test also did not assert that `push.assert_not_called()`, which means it neither
documented that push was irrelevant nor protected against a future correct implementation
calling push. It was wrong because it implicitly tested the broken call sequence (PR-first,
PR-fails, push-skipped) as the expected behaviour for this scenario.

The correct oracle sets `push.return_value = True` explicitly, asserting the precondition:
push is called first and succeeds; then PR is attempted and returns False (non-fatal); result
is True. This is the correct sequence the invariant requires.

---

## Test 4: `test__create_and_push_pr_pr_creation_raises_propagates`

**Status:** Modified — `mock_service.git_repo.push.return_value = True` added.

### What the old oracle asserted
```python
def raise_err(*args, **kwargs):
    raise RuntimeError("pr failed")
mock_service.git_repo.create_pull_request_sync.side_effect = raise_err
cli.service = mock_service
with pytest.raises(RuntimeError):
    cli._create_and_push_pr("fix-branch", sample_error)
```
No `push.return_value` was set.

### Why the old oracle was wrong (independent of any implementation)

In the old buggy code path for this scenario:
```
if self.service and self.service.git_repo.create_pull_request_sync(...):  # PR called first → raises
```
PR was the first call, and it raised immediately. `push` was never reached. The old test
**deliberately omitted `push.return_value`** because in the buggy implementation, push was
not reached when PR raised — push was simply irrelevant.

Omitting `push.return_value` encoded the assumption that push is never called before PR raises.
That assumption is the F86 bug. The correct invariant is: push MUST be called first. Only after
push succeeds should `create_pull_request_sync` be attempted (and allowed to raise).

The old oracle's implicit premise — "push setup is unnecessary because PR raises before push
is ever called" — is a direct encoding of the wrong call sequence. The test was wrong because
it designed around the buggy order, not the correct one.

The correct oracle adds `push.return_value = True` to explicitly state: push is called first
and succeeds; then PR is called (raises); the exception propagates. This is the correct
precondition that the invariant requires for the raises-propagates scenario.

---

## Summary table

| Test (origin/main name) | Old oracle flaw | Anchored to F86? |
|-------------------------|----------------|------------------|
| `test__create_and_push_pr_pr_and_push_success` | No ordering constraint — passes against buggy PR-before-push sequence | Yes — ordering bug requires ordering assertion |
| `test__create_and_push_pr_pr_success_push_fails` | Name and setup encode bug: PR is first call, push is second | Yes — test validated the bug as correct behaviour |
| `test__create_and_push_pr_pr_creation_returns_false_considered_success` | Omits push setup because buggy code never reached push in this path | Yes — omission encodes PR-first, push-skipped assumption |
| `test__create_and_push_pr_pr_creation_raises_propagates` | Omits push setup because buggy code never reached push before PR raised | Yes — omission encodes PR-first, push-never-reached assumption |

All four old oracles encoded the F86 defect — either directly (tests 1 and 2) or by implicit
omission (tests 3 and 4). All corrections are justified by the finding's ordering invariant,
not by implementation convenience.
