# Bug catalog — pef-p10-make-restore-checkpoint-actu (F39, F40)

- **F39 — `restore_checkpoint` never restores file content (no-op restore).**
  `src/branch_fixer/storage/recovery.py:232-234` (`for fpath in rp.modified_files: pass`). Wrong:
  after a checkpoint is created and a tracked file is subsequently modified, calling
  `restore_checkpoint(checkpoint_id)` leaves the file's on-disk bytes unchanged (still the
  post-modification content) while returning `True` (falsely reporting success). Correct: the
  file's bytes must be restored to exactly what they were at checkpoint-creation time (byte-
  identical), because `create_checkpoint` (`recovery.py:157-194`) never snapshots file content
  anywhere, so there is nothing for `restore_checkpoint` to read back from — both halves of the
  round trip are missing.

- **F40 — `handle_failure` reports recovery diagnostics via `print()` instead of the module logger.**
  `src/branch_fixer/storage/recovery.py:266,272,280,282,285` (5 call sites inside `handle_failure`,
  e.g. `print(logger_string)`, `print("No recovery points to restore.")`,
  `print(f"Attempting to restore last checkpoint {latest_rp.id}")`,
  `print(f"Restore result: {restored}")`, `print(f"Restore failed: {e}")`). Wrong: all recovery
  diagnostics go to raw stdout, bypassing the `logging` module used everywhere else in this
  codebase (`orchestrator.py`, `fix_service.py` both define `logger = logging.getLogger(__name__)`),
  so recovery diagnostics are invisible to any log-level filtering, log aggregation, or `caplog`-
  based test assertions. Correct: each site should emit through a module-level
  `logger = logging.getLogger(__name__)` at the appropriate level (info/warning/error), and stdout
  should remain empty for these calls.
