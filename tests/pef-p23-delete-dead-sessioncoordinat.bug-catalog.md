# Bug catalog — F70/F71 (`SessionCoordinator` dead-code stubs)

- **Symptom:** `SessionCoordinator.coordinate_fix_attempt` is a permanent async no-op.
  **Location:** `src/branch_fixer/orchestration/coordinator.py:19-31`.
  **Wrong:** body is a bare `pass` behind the comment `# Implement coordination logic here`; the
  coroutine always returns `None` regardless of `session`/`error`/`attempt`, silently discarding
  any coordination work a caller might expect to happen.
  **Correct:** the class has zero production callers and zero test coverage anywhere in `src/` or
  `tests/` (verified: `grep -rnE "SessionCoordinator|coordinate_fix_attempt" src/ tests/` hits only
  `coordinator.py` itself). There is no real caller relying on this behavior to preserve, so the
  correct end state is that `coordinate_fix_attempt` — and `SessionCoordinator` itself — do not
  exist in the codebase at all, not that the stub gets a real implementation.

- **Symptom:** `SessionCoordinator.handle_failure` hardcodes `return False` unconditionally.
  **Location:** `src/branch_fixer/orchestration/coordinator.py:33-47`.
  **Wrong:** the method always reports recovery failure regardless of the `error`/`context`
  arguments, behind the comment `# Implement failure handling logic here`; any caller checking the
  return value for recovery success would always see `False`.
  **Correct:** same as above — zero production callers, zero test coverage. The correct end state
  is deletion of `handle_failure` along with the rest of the dead `SessionCoordinator` class, not a
  "fixed" implementation that returns `True` under some condition.
