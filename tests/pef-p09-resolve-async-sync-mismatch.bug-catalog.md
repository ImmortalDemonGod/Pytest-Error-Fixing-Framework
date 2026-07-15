# Bug catalog — pef-p09-resolve-async-sync-mismatch (Finding F83)

- **`create_checkpoint` returns a coroutine, not a `RecoveryPoint`, at its real call site.**
  `src/branch_fixer/storage/recovery.py:135` declares `async def create_checkpoint(...)`. The
  only production caller, `FixOrchestrator._create_checkpoint_if_needed` at
  `src/branch_fixer/orchestration/orchestrator.py:815`, calls it without `await`:
  `checkpoint = self.recovery_manager.create_checkpoint(session, metadata)`. Wrong: `checkpoint`
  is an un-awaited coroutine object. Correct: `checkpoint` must be a `RecoveryPoint` instance so
  the very next line, `checkpoint.id` (`orchestrator.py:817`), can succeed.

- **The `AttributeError` from the coroutine mismatch is not caught by the intended handler.**
  `_create_checkpoint_if_needed` wraps the call in `try: ... except CheckpointError as e:`
  (`orchestrator.py:813-820`). Wrong: `checkpoint.id` raises `AttributeError` (coroutine objects
  have no `.id`), which is a different exception type than `CheckpointError`, so it propagates
  unhandled instead of being logged as a warning. Correct: with a synchronous return value, no
  exception is raised on `.id` access, and the `except CheckpointError` branch remains reachable
  only for genuine checkpoint failures.

- **`handle_failure` returns a coroutine, not a `bool`, at its real call site.**
  `src/branch_fixer/storage/recovery.py:225` declares `async def handle_failure(...)`. The only
  production caller, `FixOrchestrator.handle_error` at `src/branch_fixer/orchestration/orchestrator.py:692`,
  calls it without `await`: `recovered = self.recovery_manager.handle_failure(error, self._session, context)`.
  Wrong: `recovered` is an un-awaited coroutine object, which is always truthy. Correct:
  `recovered` must be the actual `bool` result of the recovery attempt.

- **`handle_error` always reports recovery success, even when no recovery occurred.**
  `orchestrator.py:695-697`: `if recovered: return True`. Wrong: because a coroutine object is
  always truthy, this branch is taken on *every* call regardless of whether recovery actually
  succeeded, ran, or was even attempted — `handle_error` unconditionally returns `True` and never
  falls through to `self._session.state = FixSessionState.ERROR` (`orchestrator.py:702`). Correct:
  `handle_error` should return `True` only when `handle_failure` genuinely performed a recovery and
  it succeeded, and should return `False` (setting `state = ERROR`) otherwise.

- **`restore_checkpoint` is also `async def` with no awaiting synchronous caller, part of the same
  API-shape mismatch.** `src/branch_fixer/storage/recovery.py:174`. It's currently reached only
  internally via `await self.restore_checkpoint(...)` from `handle_failure` (itself async), so it
  doesn't independently crash a sync caller today — but it must move in lockstep with
  `create_checkpoint`/`handle_failure` to keep `RecoveryManager`'s public API internally consistent
  (all three methods called synchronously from `FixOrchestrator`, none awaited anywhere in
  production code).

- **Test suite mismatch masks the defect.** `tests/unit/storage/test_recovery.py:134-460` marks
  every `RecoveryManager.create_checkpoint` / `restore_checkpoint` / `handle_failure` test with
  `@pytest.mark.asyncio` and `await`s the calls, so it only ever exercises the async-correct calling
  convention. `tests/unit/orchestration/test_orchestrator.py:565-598` mocks `recovery_manager` with
  synchronous `Mock()` stubs (whose return values are plain values, not coroutines), so the
  orchestrator's un-awaited calls never surface the coroutine mismatch in that suite either. Neither
  test file exercises the real async-method-called-synchronously path that production code takes.

**Caught by:** `tests/test_pef_p09_resolve_async_sync_mismatch.py::test_checkpointerror_pins_the_finding_defect`
