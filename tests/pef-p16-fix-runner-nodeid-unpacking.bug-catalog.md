# Bug catalog — pef-p16-fix-runner-nodeid-unpacking

- **Symptom:** `PytestRunner.format_test_failures()` crashes with `ValueError` instead of returning a report line when a failed test's `nodeid` contains no `::` separator (e.g. a collection-level or top-level nodeid like `"no_colon_id"`).
  **Location:** `src/branch_fixer/services/pytest/runner.py:218`
  **Wrong:** `file_path, test_name = test_id.split("::", 1)` — `str.split("::", 1)` on a string with no `"::"` returns a 1-element list, and unpacking it into two variables raises `ValueError: not enough values to unpack (expected 2, got 1)`, aborting the whole method (and therefore `capture_test_output()`) instead of producing a failure line.
  **Correct:** the method should handle a colon-less nodeid gracefully — e.g. treat the entire nodeid as the test name (or file path) — and still emit a `FAILED ...` line for it, without raising.

- **Symptom:** A test skipped via `@pytest.mark.skip` (skip decided at the `setup` phase — pytest never runs the `call` phase for it) is counted into **neither** `SessionResult.skipped` **nor** `SessionResult.passed`; it silently disappears from all three counters.
  **Location:** `src/branch_fixer/services/pytest/runner.py:376-408` (`_handle_outcome_logic`) combined with `src/branch_fixer/services/pytest/runner.py:166-178` (`_count_individual_result`)
  **Wrong:** verified live via `PytestRunner.run_test()` against a real `@pytest.mark.skip` test: `result.setup_outcome == "skipped"`, `result.call_outcome is None` (no call report is emitted), `result.teardown_outcome == "passed"`. `_handle_outcome_logic`'s `result.passed` formula requires `setup_outcome == "passed"`, so `result.passed` is (correctly) `False` — but `result.skipped` is never assigned `True` anywhere in `_handle_outcome_logic` (it stays at its dataclass default of `False`), so `_count_individual_result`'s `if _is_clean_pass / elif failed / elif result.skipped` chain matches none of the three branches and the test is dropped from `session.passed`, `session.failed`, and `session.skipped` alike.
  **Correct:** a `@pytest.mark.skip` test should set `result.skipped = True` so `_count_individual_result` increments `session.skipped`.

- **Symptom (related manifestation, same root cause):** a test that calls `pytest.skip(...)` from inside its body (skip decided at the `call` phase) is miscounted into `SessionResult.passed` instead of `SessionResult.skipped`.
  **Location:** same as above.
  **Wrong:** verified live: for this variant `result.setup_outcome == "passed"`, `result.call_outcome == "skipped"`, `result.teardown_outcome == "passed"`. `_handle_outcome_logic`'s condition `call_outcome == "passed" or call_outcome == "skipped"` treats a skipped call as satisfying `result.passed`, so `result.passed` evaluates `True` and `_is_clean_pass` routes it into `session.passed += 1` (observed: `session.passed == 1`, `session.skipped == 0`).
  **Correct:** a call-phase skip should not satisfy `result.passed`, and should instead set `result.skipped = True` so it is counted in `session.skipped`.
