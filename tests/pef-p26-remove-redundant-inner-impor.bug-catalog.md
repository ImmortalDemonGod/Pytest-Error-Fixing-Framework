# Bug catalog — pef-p26 (F17 + F42)

- **Redundant function-local `import re`** — `src/branch_fixer/services/ai/manager.py:217`
  (`AIManager._clean_stack_trace`). Wrong: the function re-imports `re` on every call even though
  `re` is already imported at module level (`manager.py:3`) and that binding is already used
  elsewhere in the same module (e.g. `re.search`/`re.split` in `_parse_response`). Correct: the
  module should contain exactly **one** `import re` statement (module-level, line 3) and **zero**
  function-local `import re` statements anywhere in the file — the module-level binding is
  sufficient for `_clean_stack_trace`'s own `re.split` call at line 219.

- **`PRDetails.created_at` / `PRDetails.updated_at` default to naive datetimes** —
  `src/branch_fixer/services/git/models.py:87-88`. Wrong: both fields use
  `field(default_factory=datetime.now)`, which produces a timezone-**naive** `datetime` (no
  `tzinfo`). Subtracting a timezone-aware `datetime` (e.g. `datetime.now(timezone.utc)`, or a
  UTC timestamp parsed from the GitHub API / TinyDB) from a naive `PRDetails.created_at` raises
  `TypeError: can't subtract offset-naive and offset-aware datetimes`. Correct: both fields
  should default to a timezone-**aware** UTC datetime (`p.created_at.tzinfo is not None`), so
  that `datetime.now(timezone.utc) - p.created_at` succeeds without raising.
