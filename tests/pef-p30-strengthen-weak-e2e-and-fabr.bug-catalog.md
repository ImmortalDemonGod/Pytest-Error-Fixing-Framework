# Bug catalog — pef-p30-strengthen-weak-e2e-and-fabr (F24, F81)

- **F24 — outcome-blindness in `test_pytest_runs_generated_tests_without_import_error`**
  `tests/integration/test_generator_e2e.py:171-182`. The test runs generated tests through a real
  `pytest` subprocess but only asserts that the strings `"ImportError"` / `"ModuleNotFoundError"` are
  absent from stdout/stderr (lines 179-181). It never inspects `result.returncode`.
  Wrong: a generated test that fails with `AssertionError` (or any non-import error), or a subprocess
  run that collects zero tests (`rc=5`), passes this test silently.
  Correct: the test must additionally assert `result.returncode == 0`, so any non-clean exit — an
  assertion failure, a collection error, or a vacuous zero-tests run — turns the test red.

- **F81 — drift-blindness in `test_analysis_uses_analysis_system_prompt`**
  `tests/test_generator/test_strategy_fabric.py:228-244`. The test imports `ANALYSIS_SYSTEM_PROMPT`
  from `src/dev/test_generator/generate/prompts.py` at line 230 but its assertion (line 244) only
  checks the generic substrings `"analyze"` / `"plan"` in the lowercased captured system message —
  it never references the imported constant.
  Wrong: `fabric.py:99` could stop passing `ANALYSIS_SYSTEM_PROMPT` verbatim and switch to any other
  prompt text that merely contains the word "analyze" or "plan", and this test would keep passing.
  Correct: the assertion must bind to the actual constant — `phase1_system == ANALYSIS_SYSTEM_PROMPT`
  — so any drift in Phase 1's system prompt away from the real constant turns the test red.
