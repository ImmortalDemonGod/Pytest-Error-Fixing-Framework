# Bug catalog — pef-p25-remove-misleading-empty-orig (Finding F26)

- **BUG-1: `CodeChanges` declares a permanently-unpopulated `original_code` field, implying a diff it never carries.**
  `src/branch_fixer/core/models.py:112-115` — `CodeChanges` is a `@dataclass` with both
  `original_code: str` and `modified_code: str`. Wrong: a reader sees two fields and assumes the class
  carries a before/after diff. Correct: the only construction site,
  `AIManager._parse_response` (`src/branch_fixer/services/ai/manager.py:338`), always passes
  `original_code=""` — there is no code path that ever sets it to real content — so `CodeChanges`
  should declare only the field it actually carries, `modified_code`.

- **BUG-2: no production code path reads `CodeChanges.original_code` back out, so the field has zero behavioral purpose.**
  `src/branch_fixer/services/code/change_applier.py` (the sole consumer of a `CodeChanges` instance)
  never accesses `.original_code`; it independently re-derives its own pre-fix source via
  `test_file.read_text()` under the local name `original_source`. Wrong: keeping a same-named,
  unread field beside `modified_code` invites a future caller to wire `.original_code` in as if it
  were meaningful diff context, silently coupling to a value that is always `""`. Correct: with the
  field removed, `dataclasses.fields(CodeChanges)` yields exactly `{"modified_code"}`, so there is no
  unread field left to misuse.

- **BUG-3 (regression risk this catalog guards against): existing tests assert the empty string as if it were correct, cementing the misleading shape.**
  `tests/unit/ai/test_ai_manager.py` — `test_original_code_is_empty_string` (around L317-320) asserts
  `result.original_code == ""`, treating the always-empty value as expected behavior rather than
  flagging it as dead weight. Wrong: a passing test that pins `original_code == ""` makes the
  misleading field look intentional and blocks future removal from ever going green without a test
  update. Correct: once `original_code` is removed from `CodeChanges`, the only valid regression pin
  is a structural one — the dataclass's field set is exactly `{"modified_code"}` — not a
  value-equality check against an empty string.
