# Bug catalog — pef-p32-remove-non-coverage-test-spl (F65, F79, F10)

- **Zero-coverage test file** — `tests/test_math_operations.py:3-8`. The file defines its
  own local `add(a, b)` function and then tests that local copy. It imports nothing from
  `src/branch_fixer` and exercises no production code. Wrong: this file is treated as part
  of the suite's coverage signal. Correct: the file should not exist — the suite's coverage
  numbers should reflect only tests that import real `src/` symbols.

- **Misplaced/duplicated git fixtures reference a non-existent `GitRepository` method** —
  `tests/integration/pytest/conftest.py:12-30`. Lines 1-10 correctly define the
  integration-scope `runner`/`test_suite_dir` fixtures. Lines 12-30 additionally define
  `clean_repo`/`branch_manager` fixtures that duplicate (and diverge from) the ones that
  already live in `tests/unit/git/conftest.py`. The duplicate `clean_repo` builds
  `Mock(spec=GitRepository)` and sets `repo.create_branch.return_value = True`
  (line ~24 of the duplicated block). `GitRepository` (see
  `src/branch_fixer/services/git/repository.py:443`) has no `create_branch` method — only
  `create_fix_branch`. Because the mock is built with `spec=GitRepository`, setting the
  non-existent attribute raises `AttributeError: Mock object has no attribute
  'create_branch'` the moment any test actually exercises this fixture. Wrong: constructing
  the duplicated `clean_repo` fixture in `tests/integration/pytest/conftest.py` raises
  `AttributeError`. Correct: `tests/integration/pytest/conftest.py` should not define
  `clean_repo`/`branch_manager` at all — those fixtures belong solely in
  `tests/unit/git/conftest.py`, which already uses `create_autospec(GitRepository,
  instance=True)` and the real `create_fix_branch` method name.

- **Duplicate test coverage for `UnifiedErrorParser`** —
  `tests/unit/pytest/parsers/test_unified_error_parser.py:1` and
  `tests/unit/services/pytest/test_unified_error_parser.py:1` both cover the same
  production class (`branch_fixer.services.pytest.parsers.unified_error_parser.UnifiedErrorParser`).
  The latter is a superset (138 tests across 5 classes: `TestUnifiedErrorParser`,
  `Test_parse_pytest_output_function`, `TestConvertErrorInfoToTestError`,
  `TestCollectionParser`, `TestFailureParser`, `TestErrorInfo`). Wrong: two independent test
  modules exist for the same class, doubling maintenance cost with no coverage benefit.
  Correct: only the comprehensive module,
  `tests/unit/services/pytest/test_unified_error_parser.py`, should remain.
