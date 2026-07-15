# Bug catalog — pef-p29-fix-always-true-and-broken-r (F72, F73)

- **Vacuous assertion (F72)** — `tests/unit/services/pytest/test_runner.py:470`, inside
  `TestPytestRunner.test_format_report_basic`. `assert "Duration: 1.23s" or "Duration: 1.2"`
  is parsed as `assert ("Duration: 1.23s" or "Duration: 1.2")`. Python's `or` short-circuits on
  the first truthy operand, so this reduces to `assert "Duration: 1.23s"` — a non-empty string
  literal, which is unconditionally `True` regardless of the value of `report`. The variable
  `report` (the actual value under test, returned by `PytestRunner.format_report(sess)`) never
  appears in the boolean expression, so the assertion cannot fail no matter what
  `format_report` returns.
  - **Wrong:** `assert "Duration: 1.23s" or "Duration: 1.2"` — always passes, checks nothing.
  - **Correct:** `assert "Duration: 1.23s" in report` — actually verifies that
    `PytestRunner.format_report` rendered the `Duration:` line with the expected `.2f`-formatted
    value.
  - **Verified:** `src/branch_fixer/services/pytest/runner.py:497` already formats
    `f"Duration: {session.duration:.2f}s"` correctly for `duration=1.23` (produces
    `"Duration: 1.23s"`). There is no production defect here — this is a pure test-quality gap
    (a broken assertion that would silently pass even if `format_report` were rewritten to omit
    the duration line entirely).

- **Dead/broken exception fallback (F73)** — `tests/unit/orchestration/test_orchestrator.py:583`,
  inside `TestFixOrchestrator.test_create_checkpoint_handles_checkpoint_error`, local class `RM`:
  `raise SimpleNamespace.__class__("CheckpointError")("fail")`. `SimpleNamespace.__class__` is
  the metaclass `type`. Calling `type("CheckpointError")` with a single argument does **not**
  construct a new exception class — it returns `type(x)`, i.e. the *type of* the argument, which
  for a string literal is `str`. So the expression reduces to `raise str("fail")`, i.e.
  `raise "fail"`, which Python rejects with `TypeError: exceptions must derive from
  BaseException` instead of raising the intended checkpoint-failure exception.
  - **Wrong:** `raise SimpleNamespace.__class__("CheckpointError")("fail")` inside `RM` — raises
    `TypeError`, not an exception the orchestrator's `except CheckpointError` clause can catch.
  - **Correct:** raise an actual `CheckpointError` instance (e.g.
    `raise branch_fixer.storage.recovery.CheckpointError("fail")`), so
    `FixOrchestrator._create_checkpoint_if_needed` (`src/branch_fixer/orchestration/orchestrator.py:520`)
    exercises its intended `except CheckpointError as e:` branch.
  - **Verified:** `RM` is never instantiated. The test wraps construction in
    `try: from branch_fixer.storage.recovery import CheckpointError as CE; class RM2: ...; rm =
    RM2() except Exception: rm = RM()`. The import of `CheckpointError` always succeeds (it is a
    real class defined at `src/branch_fixer/storage/recovery.py`), so the `try` branch always
    wins and `rm = RM2()` (which raises a real `CE("boom")`) is what actually runs. `RM`'s broken
    `raise` is dead code — it never executes in the current test suite, and
    `FixOrchestrator._create_checkpoint_if_needed` already correctly catches `CheckpointError`
    and logs a warning without propagating (`src/branch_fixer/orchestration/orchestrator.py:520-521`).
    There is no production defect here either — this is a leftover broken fallback class in the
    test file that the real code path never reaches.

## Note on test-layer strategy

Both F72 and F73 are defects in *test source code* (a vacuous assertion, a dead/broken exception
construction), not in production code — `format_report` and `_create_checkpoint_if_needed` already
behave correctly. Because there is no production bug to exercise, a new test that calls the
production symbols with correct expectations would pass today and would therefore not be RED.
Instead, `tests/test_pef-p29-fix-always-true-and-broken-r.py` pins each defect by parsing the exact
buggy function's AST source out of the *current* test files and asserting the corrected pattern is
present (F72) / the broken pattern is absent (F73). Both assertions are false against the current
(buggy) test files, so the test is genuinely RED, and each assertion will independently flip to
green once test_runner.py:470 and test_orchestrator.py:583 are corrected by the implement-fix stage.
