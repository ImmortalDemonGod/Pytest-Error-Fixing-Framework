# Bug catalog — F87: collection errors are not short-circuited before AI-fix + retry budget

- **Symptom:** a `CollectionError`-typed `TestError` is fed through the *exact same* AI-fix
  retry pipeline as an ordinary, file-addressable test failure, even though a collection error
  (a module that failed to *import*) can never be repaired by editing the fabricated sentinel
  path `Path("unknown_collection_file.py")`.
  - **Where:** `src/branch_fixer/orchestration/orchestrator.py:322-372`
    (`FixOrchestrator.fix_error()`).
  - **Wrong:** `fix_error()` has no check of `error.error_details.error_type` anywhere in its
    body — it unconditionally enters `for attempt_index in range(self.max_retries):` and
    constructs a `FixService` + calls `fix_service.attempt_fix(error, temperature=current_temp)`
    for every `TestError`, regardless of error class.
  - **Correct:** before the retry loop, `fix_error()` must recognize
    `error.error_details.error_type == "CollectionError"` and return `False` immediately,
    without entering the loop at all.

- **Symptom:** every collection error burns a real `AIManager.generate_fix()` call (and its
  associated API cost/latency) that is *guaranteed* to be wasted, because the downstream
  `ChangeApplier._backup_file()` call will always raise `FileNotFoundError` for the
  non-existent sentinel path.
  - **Where:** `src/branch_fixer/orchestration/fix_service.py:128`
    (`FixService.attempt_fix()`, `changes = self.ai_manager.generate_fix(error, attempt.temperature)`),
    reached from `orchestrator.py:357` (`fix_service.attempt_fix(error, temperature=current_temp)`)
    once per loop iteration.
  - **Wrong:** `ai_manager.generate_fix()` is called unconditionally for `CollectionError`
    `TestError`s, exactly as for any other error class.
  - **Correct:** for a `CollectionError`-typed `TestError`, `ai_manager.generate_fix()` must be
    called **zero** times — the orchestrator must skip the error before `FixService` (and
    therefore the AI manager) is ever invoked.

- **Symptom:** the full `max_retries` (default 3) retry budget is consumed on every collection
  error, 100% of the time, because each of the 3 guaranteed-failing attempts increments
  `session.retry_count` and bumps the temperature before giving up.
  - **Where:** `src/branch_fixer/orchestration/orchestrator.py:364-365`
    (`current_temp += self.temp_increment; self._session.retry_count += 1`, inside the
    `for attempt_index in range(self.max_retries)` loop of `fix_error()`).
  - **Wrong:** `session.retry_count` increments once per failed attempt for a `CollectionError`
    error (ending at `3` after the loop exhausts), identical to how a genuinely fixable-but-hard
    error would be retried.
  - **Correct:** `session.retry_count` must stay unchanged (remain at its pre-call value, `0`
    in a session with no prior attempts) for a `CollectionError`-typed `TestError`, since no
    retry loop should ever run for it.
