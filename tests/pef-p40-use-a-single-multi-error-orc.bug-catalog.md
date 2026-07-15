# Bug catalog — pef-p40-use-a-single-multi-error-orc (F16, F82)

- **New orchestrator session created per error instead of once per run.**
  `src/branch_fixer/utils/cli.py:210` — `_generate_and_apply_fix(self, error)` calls
  `self.orchestrator.start_session([error])` with a single-element list on *every*
  invocation. `_process_all_errors` (`src/branch_fixer/utils/cli.py:521-536`) calls
  `_generate_and_apply_fix` once per error inside its `for i, error in enumerate(errors, 1)`
  loop.
  - Wrong: a run over N errors creates N distinct `FixSession` objects (N calls to
    `orchestrator.start_session`), each overwriting `self.orchestrator._session` —
    every prior session's state, retry history, and `completed_errors` list is
    discarded before the next error is processed.
  - Correct: a run over N errors should call `orchestrator.start_session(errors)`
    exactly once with the full error list, then drive per-error fixing (e.g. via
    `orchestrator.fix_error` / `orchestrator.run_session`) against that single
    session so state tracking and resume capability work as designed.

- **Multi-error session semantics (state tracking, resume) are destroyed by the
  per-error session churn above.** Because no session ever holds more than one
  error, `FixSession.errors`, `FixSession.completed_errors`, and
  `FixSession.retry_count` never reflect the true shape of a multi-error run, and
  `StateManager.validate_session_state`
  (`src/branch_fixer/storage/state_manager.py:186-201`) is only ever exercised
  against single-error sessions in practice, even though it is written to validate
  session-wide invariants (e.g. COMPLETED requires all errors fixed).
