# Bug catalog — PEF-P31 (finding F25)

Source: `tests/unit/utils/test_run_cli.py` injects fake `types.ModuleType` objects directly into
`sys.modules` at 4 sites, each inside a test that already receives `monkeypatch` as a fixture
argument, with no restoration (`monkeypatch.setitem` or `try/finally`). This pollutes the
process-wide `sys.modules` table for the remainder of the pytest session.

- **Bug 1 — `tests/unit/utils/test_run_cli.py:179`, key `branch_fixer.orchestration.orchestrator`.**
  Symptom: `test_fix_all_tests_passed_saves_session_and_returns_0` sets
  `sys.modules["branch_fixer.orchestration.orchestrator"] = orchestrator_mod` (a fake module with a
  stub `FixSession`/`FixSessionState`) and never removes or restores the entry.
  Wrong: after this test finishes, `sys.modules["branch_fixer.orchestration.orchestrator"]` still
  holds the fake module object — any later-collected test that imports or exercises
  `branch_fixer.orchestration.orchestrator` (e.g. via `src/branch_fixer/utils/run_cli.py:92`'s lazy
  `from branch_fixer.orchestration.orchestrator import FixSession, FixSessionState`) transparently
  receives the fake `FixSession`/`FixSessionState` instead of the real ones.
  Correct: once the test completes (and its teardown runs), `sys.modules["branch_fixer.orchestration.orchestrator"]`
  must be exactly what it was before the test ran (absent if it was absent, the real module if it was
  already loaded).

- **Bug 2 — `tests/unit/utils/test_run_cli.py:217`, key `branch_fixer.services.pytest.error_processor`.**
  Symptom: `test_fix_failed_but_no_parsable_errors_returns_1` sets
  `sys.modules["branch_fixer.services.pytest.error_processor"] = err_proc_mod` (a fake module whose
  `process_pytest_results` always returns `[]`) with no cleanup.
  Wrong: the fake `process_pytest_results` (always `[]`) leaks into `sys.modules` for the rest of the
  session — a later test that imports `branch_fixer.services.pytest.error_processor` and expects the
  real parsing logic would silently get the stub instead.
  Correct: after this test's teardown, `sys.modules["branch_fixer.services.pytest.error_processor"]`
  must match its pre-test state exactly.

- **Bug 3 — `tests/unit/utils/test_run_cli.py:247`, key `branch_fixer.services.pytest.error_processor`
  (parametrized ×2 via `test_fix_fast_run_success_and_failure`).**
  Symptom: same raw `sys.modules[...] = err_proc_mod` assignment, repeated with no restoration, once
  per parametrization.
  Wrong: each parametrized run re-overwrites the shared key and leaves it overwritten; two
  back-to-back leaks compound the pollution window for downstream tests.
  Correct: each parametrized invocation must restore the key to its own pre-test value at its own
  teardown, independent of the other parametrization.

- **Bug 4 — `tests/unit/utils/test_run_cli.py:274`, key `branch_fixer.services.pytest.error_processor`
  (parametrized ×2 via `test_fix_delegate_to_process_errors`).**
  Symptom: same raw `sys.modules[...] = err_proc_mod` assignment as Bug 2/3, again with no cleanup.
  Wrong: this is the 4th and final unrestored injection of the same key in the file — by the time the
  full file has run, `sys.modules["branch_fixer.services.pytest.error_processor"]` is left holding
  whichever fake object was assigned last.
  Correct: this site's own fake object must not outlive its test; the key must return to its pre-test
  state at teardown.

## Aggregate, file-level symptom (what the RED test in this commit actually catches)

Running `pytest tests/unit/utils/test_run_cli.py -q` currently exits 0 (all 13 tests pass) but, as a
side effect, leaves both `branch_fixer.orchestration.orchestrator` and
`branch_fixer.services.pytest.error_processor` permanently present in `sys.modules` as the fake
objects injected at lines 179/217/247/274 — even though neither key was present in `sys.modules`
before the run. Any subsequently executed test in the same pytest session that imports either module
would transparently receive the leaked fake instead of the real one. Wrong behavior: `sys.modules`
snapshot taken before vs. after the file's test run differs at both keys. Correct behavior: the
snapshot must be identical before and after.
