# Bug catalog — pef-p14-implement-pull-so-sync-with (Finding F68)

- **`sync_with_remote()` propagates `NotImplementedError` instead of returning a bool.**
  `src/branch_fixer/services/git/repository.py:590` calls `self.pull()`, and `pull()` at
  `repository.py:352` unconditionally executes `raise NotImplementedError("pull method is not
  implemented yet.")`. Wrong: every call to `sync_with_remote()` crashes the caller with an
  uncaught `NotImplementedError` — the method can never return `True` or `False`. Correct:
  `sync_with_remote()` must handle the unimplemented `pull()`/`push()` case and return `False`
  (or otherwise resolve to a `bool`), never letting `NotImplementedError` escape.

- **The `except GitError` clause is a no-op for the actual defect.**
  `repository.py:593` (`except GitError: return False`) only catches `GitError`. `NotImplementedError`
  is not a subclass of `GitError` (it's a builtin `RuntimeError` subclass), so it passes straight
  through the `try`/`except` in `sync_with_remote()` (`repository.py:589-594`) untouched. Wrong:
  the exception handling silently assumes `pull()`/`push()` only ever raise `GitError`. Correct:
  the handler (or the underlying `pull()`/`push()` implementations) must account for
  `NotImplementedError` so `sync_with_remote()` always resolves to a `bool`.

- **Existing unit test enshrines the bug as expected behavior.**
  `tests/unit/services/git/test_repository.py::TestSyncAndMerge::test_sync_with_remote_success_and_giterror`
  (around lines 573-576) asserts `pytest.raises(NotImplementedError)` when `pull()` raises
  `NotImplementedError` — i.e. it currently treats the crash as the *correct* outcome. Wrong: this
  test locks in the defect described above. Correct: once fixed, that assertion must instead
  assert `sync_with_remote()` returns `False` for this case.
