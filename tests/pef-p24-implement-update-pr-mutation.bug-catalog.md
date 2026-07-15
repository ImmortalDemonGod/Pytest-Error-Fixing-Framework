# Bug catalog: pef-p24-implement-update-pr-mutation

Target file: `src/branch_fixer/services/git/pr_manager.py`. All findings below are rooted in
`PRManager` and were verified by direct read against base SHA `697ab7f3414459edd480bb72a342446d040b3134`
(see `audit/02-static-audit.md#L36`, `.aiv/plans/pef-p24-implement-update-pr-mutation-plan.md` §2/§6).

- **F49 — `update_pr` is a state-mutation stub.** `pr_manager.py:114-138`. Symptom: calling
  `update_pr(pr_id, status=PRStatus.MERGED, metadata={"k": "v"}, reason="done")` on an existing PR
  silently discards `status`, `metadata`, and `reason` — the method only checks `pr_id in self.prs`
  (line 136) and returns `self.prs[pr_id]` unchanged (line 138). Wrong: the returned `PRDetails.status`
  stays whatever `create_pr` set it to (`PRStatus.OPEN`) and `.change_history` stays `[]` forever, no
  matter how many times `update_pr` is called. Correct: `.status` reflects the passed `status`,
  `.metadata` has the passed `metadata` merged in (not replaced), and `.change_history` grows by
  exactly one `PRChange` entry per call.

- **F58 — Mixed sync/async calling convention across one class.** `pr_manager.py:41` (`create_pr`,
  `def`) vs. `pr_manager.py:114,140,155,169` (`update_pr`, `validate_pr`, `get_pr_history`, `close_pr`,
  all `async def`). Symptom: no caller can treat `PRManager`'s five public methods uniformly — four
  require `await`, one forbids it. Wrong: the class exposes two incompatible calling conventions with
  no documented rule for which methods need which. Correct: all five methods share one calling
  convention (plain `def`, matching the sole production caller `repository.py:568`, which calls
  `create_pr` synchronously and never awaits any of the other four).

- **F59 — `get_pr_history` and `close_pr` are unconditional stubs.** `pr_manager.py:167` and
  `pr_manager.py:186`. Symptom: both methods have full docstrings and type signatures implying real
  behavior (`get_pr_history` "Get complete change history for PR", `close_pr` "Close PR with specified
  status") but each body is a single `raise NotImplementedError()` with no conditional logic at all.
  Wrong: every call to either method raises, regardless of whether the PR exists or the arguments are
  valid — the documented `Raises: KeyError` / `Raises: PRUpdateError` / `Raises: ValueError` contracts
  are never reachable. Correct: `get_pr_history` returns the live `change_history` list for an existing
  PR and raises `KeyError` for a missing one; `close_pr` mutates `.status` to the given
  `PRStatus.MERGED`/`PRStatus.CLOSED` value, appends one `PRChange`, and returns `True`, raising
  `ValueError` for any other status and `PRUpdateError` for a missing PR.

- **F60 — Non-monotonic id generation collides after deletion.** `pr_manager.py:66`
  (`pr_id = len(self.prs) + 1`). Symptom: id assignment is derived from the *current size* of
  `self.prs`, not from a count of ids ever issued. Wrong: creating PR 1 and PR 2, deleting PR 2's entry
  from `self.prs`, then creating a new PR reuses id 2 (`len(self.prs) == 1` after the deletion, so
  `1 + 1 == 2`) — the same id that was just freed, causing two logically distinct PRs to share an id
  across the manager's lifetime. Correct: id assignment uses a strictly monotonic counter
  (e.g. `self._next_id`) that is never decremented and never re-derived from `len(self.prs)`, so a
  freed id is never reissued.

- **F61 — `create_pr` drops the `modified_files` and `metadata` constructor arguments.**
  `pr_manager.py:43-44` (parameters bound) and `pr_manager.py:102-111` (the `PRDetails(...)` call site).
  Symptom: `modified_files` and `metadata` are accepted as required/optional parameters but neither is
  ever passed into the `PRDetails(...)` constructor call — only `id`, `title`, `description`,
  `branch_name`, `status`, `created_at`, `url` are set. Wrong: `PRDetails.modified_files` is always the
  dataclass default `[]` and `PRDetails.metadata` is always `{}`, regardless of what the caller passed
  in, even though `PRDetails` already has both fields shaped exactly to receive them
  (`models.py:89-90`). Correct: the constructed/stored `PRDetails.modified_files` equals the passed
  `modified_files` argument's contents, and `.metadata` equals the passed `metadata` argument (or `{}`
  when `metadata=None`).
