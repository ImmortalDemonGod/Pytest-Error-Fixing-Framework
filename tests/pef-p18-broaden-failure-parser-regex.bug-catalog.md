# Bug Catalog — pef-p18-broaden-failure-parser-regex

- **Symptom**: `StopIteration` failures are silently dropped from parser output.
  **Location**: `src/branch_fixer/services/pytest/parsers/failure_parser.py:9`
  **Wrong**: `PATTERNS[0]` = `r"([\w\/\._-]+):(\d+):\s+([\w\.]+Error)"` requires the exception type token to end in the literal substring `Error`, so a pytest failure line like `tests/test_x.py:10: StopIteration` never matches — `process_failure_line` (and therefore `parse_test_failures`) returns `None` / omits the failure entirely, instead of an `ErrorInfo` with `error_type="StopIteration"`.
  **Correct**: The pattern should also match exception class names ending in `Exception` (and other stdlib terminal exception names like `StopIteration`, `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`), so these failures are captured, not dropped.

- **Symptom**: `KeyboardInterrupt` failures are silently dropped from parser output.
  **Location**: `src/branch_fixer/services/pytest/parsers/failure_parser.py:9`
  **Wrong**: Same regex defect as above — `KeyboardInterrupt` does not end in `Error`, so `re.search(PATTERNS[0], line)` fails to match a line such as `tests/test_x.py:12: KeyboardInterrupt`, and the failure is dropped instead of being reported.
  **Correct**: A pytest failure line naming `KeyboardInterrupt` as the exception type should produce an `ErrorInfo` with `error_type="KeyboardInterrupt"`, `test_file` and `line_number` populated from the matched groups.

- **Symptom**: User-defined exception classes named `*Exception` (e.g. `CustomException`) are silently dropped from parser output.
  **Location**: `src/branch_fixer/services/pytest/parsers/failure_parser.py:9`
  **Wrong**: The `[\w\.]+Error` suffix requirement in `PATTERNS[0]` rejects any custom exception class whose name does not literally end in `Error`, e.g. `tests/test_x.py:15: CustomException` never matches, so the failure is lost rather than surfaced for fixing.
  **Correct**: A pytest failure line naming `CustomException` (or any `*Exception`-suffixed class) as the exception type should produce an `ErrorInfo` with `error_type="CustomException"` and the correct `test_file`/`line_number`.
