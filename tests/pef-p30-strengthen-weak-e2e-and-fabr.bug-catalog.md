# Bug catalog — pef-p30-strengthen-weak-e2e-and-fabr

| # | Location | Defect | Evidence (harness-executed) | Caught by |
|---|----------|--------|------------------------------|-----------|
| 1 | tests/integration/test_generator_e2e.py:171-182 | `test_pytest_runs_generated_tests_without_import_error` (lines 171-182) only asserts the absence of `ImportError` and `ModuleNotFoundError` strings in subprocess output. It does not assert that `result.returncode == 0` or that any tests actually passed. Generated tests that fail with AssertionError or any non-import error would not be detected by this test. | The e2e test fails if generated tests error with a non-import failure; the fabric test fails if the analysis prompt drifts from ANALYSIS_SYSTEM_PROMPT. | `tests/test_pef_p30_strengthen_weak_e2e_and_fabr.py` |

- **Expected (per the finding goal):** The e2e test fails if generated tests error with a non-import failure; the fabric test fails if the analysis prompt drifts from ANALYSIS_SYSTEM_PROMPT.
- Every row above is recorded ground truth (finding fields + harness-executed command outputs); no value is estimated.
