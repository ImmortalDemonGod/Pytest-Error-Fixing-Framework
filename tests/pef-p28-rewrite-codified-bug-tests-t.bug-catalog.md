# Bug catalog — pef-p28-rewrite-codified-bug-tests-t (F11, F12)

- **F11 — `PRManager.create_pr` drops `modified_files` and `metadata` on the floor.**
  `src/branch_fixer/services/git/pr_manager.py:102-110` builds the returned `PRDetails` without
  passing `modified_files=modified_files` or `metadata=metadata`, even though both are accepted
  parameters of `create_pr` (`src/branch_fixer/services/git/pr_manager.py:41-47`) and `PRDetails`
  has typed fields for both (`src/branch_fixer/services/git/models.py:391-392`).
  - Wrong (current): `details.modified_files == []` and `details.metadata == {}` no matter what
    the caller passed in — the arguments are silently discarded.
  - Correct (expected): `details.modified_files` equals the `modified_files` list the caller
    passed, and `details.metadata` equals the `metadata` dict the caller passed.
  - Codified as "correct" by the existing test
    `tests/unit/git/test_pr_manager.py:139-148`
    (`test_create_pr_accepts_modified_files_and_metadata_without_using_them`), which passes
    non-trivial `modified_files`/`metadata` and then only asserts `details.id == 1` and storage —
    never asserting the values actually reached `PRDetails`, per its own name.

- **F12 — `setup_logging()` leaks a new `snoop` FileHandler on every call.**
  `src/branch_fixer/config/logging_config.py:30-37` unconditionally constructs a new
  `logging.FileHandler` and calls `snoop_logger.addHandler(snoop_handler)` with no check for an
  existing handler, so every call to `setup_logging()` appends one more handler to the `"snoop"`
  logger (file-descriptor leak on repeated invocations, e.g. repeated fix attempts in one process).
  - Wrong (current): calling `setup_logging()` twice results in
    `len(logging.getLogger("snoop").handlers)` growing by 1 each call (unbounded growth).
  - Correct (expected): the snoop handler count stays stable across repeated `setup_logging()`
    calls (idempotent setup, mirroring `logging.basicConfig`'s no-op-when-already-configured
    behavior for the root logger).
  - Codified as "correct" by the existing test
    `tests/unit/config/test_logging_config.py:166-182`
    (`test_repeated_calls_add_snoop_handler_but_basicconfig_is_noop_for_root`), which explicitly
    asserts `len(snoop_handlers_after) == len(snoop_handlers_before) + 1` — codifying the leak as
    intended behavior.
