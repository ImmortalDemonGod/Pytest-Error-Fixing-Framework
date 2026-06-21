# Oracle Corrections — change `pytest-fixer-f15-impl`

**Finding:** F15 (critical)
**Canonical intent anchor (SHA-pinned):**
`https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L11`

---

## Scope of this document

F15 requires modifying six test methods that existed on `origin/main`. The oracle guard requires
written justification — anchored to the finding, independent of implementation — for every test
that was changed or removed. This document supplies that justification.

Criterion for "old oracle was wrong": the old test was asserting behaviour that **implements the
defect**, not the correct behaviour. A test that passes ONLY when the bug is present is incorrect
(it is a bug-encoding test), and correcting it is required for the fix to be testable at all.

---

## Per-test justification

### 1. `test_handle_manual_fix_choice_fixed_returns_true`

**Location (origin/main):** `tests/unit/utils/test_cli.py:365–368`

**Old oracle:**
```python
res = cli._handle_manual_fix_choice(sample_error)
assert res is True
```

**Why the old oracle was wrong:**

F15 identifies that `_handle_manual_fix_choice` returns a bare `bool` and discards the distinction
between a successful fix and a skipped fix (both "fixed" and "skip" branches returned `True`). The
finding (audit L11) records that callers downstream — specifically `_process_all_errors` — can
never distinguish between "the error was fixed" and "the error was skipped" because the handler
collapses both outcomes to the same `True` scalar.

Asserting `res is True` (a bare scalar) encodes this defect directly: it verifies that the handler
discards the fix-outcome signal. The correct behaviour — required by the finding — is for the
method to return a pair `(continue: bool, fixed: bool)` so that callers can propagate the
`fixed` component into `success_count`. An assertion on a bare `True` can only pass when the
fix-outcome channel is absent (= the bug is present). The old oracle is therefore wrong because
it cannot distinguish `(True, True)` from `True` from `(True, False)` — it would accept any of
these as equivalent, making the test unable to detect a regression back to the buggy behaviour
or a misimplementation that loses the "fixed" bit.

**Correct oracle:** `assert res == (True, True)` — verifies `continue=True` AND `fixed=True`.

---

### 2. `test_handle_manual_fix_choice_quit_returns_false`

**Location (origin/main):** `tests/unit/utils/test_cli.py:370–373`

**Old oracle:**
```python
res = cli._handle_manual_fix_choice(sample_error)
assert res is False
```

**Why the old oracle was wrong:**

Same defect as #1, "quit" branch. The finding records that the "quit" return of
`run_manual_fix_workflow` is collapsed to a bare `False`, losing the signal that no fix was
attempted (as opposed to a fix that was attempted and failed). Asserting `res is False` encodes
the defect by accepting a bare scalar that makes callers unable to distinguish
`(False, False)` from `False`. A caller that unpacks a `Tuple[bool, bool]` requires a tuple
return; asserting a scalar proves nothing about whether `_process_all_errors` can correctly
handle the "quit" signal as a stop condition combined with a "not fixed" outcome.

**Correct oracle:** `assert res == (False, False)` — verifies `continue=False` AND `fixed=False`.

---

### 3. `test_handle_ai_fix_choice_success_and_failure`

**Location (origin/main):** `tests/unit/utils/test_cli.py:375–381`

**Old oracle:**
```python
with patch.object(CLI, "run_fix_workflow", return_value=True):
    res = cli._handle_ai_fix_choice(sample_error)
    assert res is True          # success branch → True
with patch.object(CLI, "run_fix_workflow", return_value=False):
    res = cli._handle_ai_fix_choice(sample_error)
    assert res is True          # failure branch → also True  ← encodes the bug
```

**Why the old oracle was wrong:**

F15 explicitly records (audit L11 / plan §1 V3): "`_handle_ai_fix_choice` always returns `True`
regardless of `run_fix_workflow` result." The old test asserts this literally: both the success
case AND the failure case are asserted to return `True`. This means the test is asserting that
fix failures are silently swallowed — which is the defect itself. The test cannot catch a
regression where a failure is incorrectly reported as success (or vice versa) because both are
expected to produce the same return value.

Additionally, both branches return a bare scalar, encoding the defect that fix-outcome data
cannot flow up to `success_count` via `_process_all_errors`.

**Correct oracles:**
- Success branch: `assert res == (True, True)` — `continue=True`, `fixed=True`
- Failure branch: `assert res == (True, False)` — `continue=True`, `fixed=False`

These two must differ; otherwise the test proves nothing about outcome propagation.

---

### 4. `test__process_interactive_error_calls_correct_handler`

**Location (origin/main):** `tests/unit/utils/test_cli.py:412–429`

**Old oracle (three sub-cases):**
```python
# 'q' sub-case:
assert res is False

# 'n' sub-case:
assert res is True

# 'z' (unknown/AI) sub-case:
patch.object(CLI, "_handle_ai_fix_choice", return_value=True)
assert res is True
```

**Why the old oracle was wrong:**

F15 records that `_process_interactive_error` returns a bare scalar from `_handle_ai_fix_choice`
and from dict-dispatch, giving callers (specifically `_process_all_errors`) no way to extract the
`fixed` component. Asserting scalar returns (`is False`, `is True`) encodes the defect in three
places:

1. **'q' → `is False`**: the "quit" path should carry `(False, False)` so that the loop can both
   stop *and* know no fix was recorded. Asserting `is False` cannot detect if `fixed=True` were
   mistakenly set.
2. **'n' → `is True`**: the "skip" path should carry `(True, False)` — continue but not fixed.
   Asserting `is True` cannot distinguish `(True, True)` (correctly fixed) from `(True, False)`
   (correctly skipped), making the test useless for detecting the skip-vs-fix conflation bug.
3. **'z' mock `return_value=True`, `assert is True`**: the AI-fix path's mock returns a bare
   `True`, not a `(True, bool)` tuple; and the assertion accepts any truthy value. This proves
   nothing about whether the tuple is passed through or collapsed.

**Correct oracles:**
- 'q': `assert res == (False, False)`; mock `_handle_quit_choice` return unchanged (still `bool`)
- 'n': `assert res == (True, False)`; mock `_handle_skip_choice` return unchanged (still `bool`)
- 'z': mock `_handle_ai_fix_choice` `return_value=(True, True)`; `assert res == (True, True)`

---

### 5. `test__process_all_errors_noninteractive_iterates_all` (removed; replaced by two tests)

**Location (origin/main):** `tests/unit/utils/test_cli.py:439–445`

**Old oracle:**
```python
with patch.object(CLI, "_process_non_interactive_error", return_value=None) as pn:
    total_processed, success_count = cli._process_all_errors(errors, interactive=False)
    assert total_processed == 3
    assert success_count == 0       # ← encodes the bug
```

**Why the old oracle was wrong:**

This test is the most direct encoding of the F15 defect. It mocks `_process_non_interactive_error`
returning `None` (the pre-fix, no-`return` behaviour recorded in audit L11 / plan §1 V2) and
asserts `success_count == 0` — exactly the broken behaviour F15 identifies.

The defect is: `_process_non_interactive_error` has no `return` statement and implicitly returns
`None`; `_process_all_errors` never checks its return value and never increments `success_count`.
This test was written to match that broken state. It would FAIL on a correct implementation
(which captures `True`/`False` from `_process_non_interactive_error` and increments on success),
proving it encodes the bug rather than the specification.

The test was replaced with two tests:
- `test__process_all_errors_noninteractive_success`: mock returns `True`; asserts `success_count == 3`.
- `test__process_all_errors_noninteractive_failure`: mock returns `False`; asserts `success_count == 0`.

These two together cover both paths and make the counter's behaviour verifiable in both directions.

---

### 6. `test__process_all_errors_interactive_breaks_on_quit`

**Location (origin/main):** `tests/unit/utils/test_cli.py:447–454`

**Old oracle:**
```python
with patch.object(CLI, "_process_interactive_error", return_value=False) as pi:
    total_processed, success_count = cli._process_all_errors(errors, interactive=True)
    assert total_processed == 0
    assert success_count == 0
    pi.assert_called_once()
```

**Why the old oracle was wrong:**

After F15's fix, `_process_interactive_error` returns `Tuple[bool, bool]`, not a bare scalar.
`_process_all_errors` unpacks the tuple: `should_continue, fixed = self._process_interactive_error(error)`.

If the mock still returns a bare `False`, Python's unpacking fails at runtime with a `TypeError`
(cannot unpack a non-sequence `bool` into two variables). The old mock value `return_value=False`
is therefore **incompatible with the corrected calling convention** — it does not encode the buggy
behaviour per se (the assertion on `success_count == 0` and `total_processed == 0` remains
correct for the "quit on first error" scenario); rather, the mock setup uses the old scalar type
that the corrected code can no longer accept.

**Correct oracle:** `return_value=(False, False)` — the tuple that `_process_all_errors` unpacks.
The assertions on `total_processed == 0`, `success_count == 0`, and `pi.assert_called_once()`
are unchanged and remain correct.

---

## Summary table

| Test | Old oracle type | Defect encoded | Oracle direction of change |
|------|-----------------|----------------|---------------------------|
| `test_handle_manual_fix_choice_fixed_returns_true` | Scalar `True` | Discards `fixed` bit | `(True, True)` |
| `test_handle_manual_fix_choice_quit_returns_false` | Scalar `False` | Discards `fixed` bit | `(False, False)` |
| `test_handle_ai_fix_choice_success_and_failure` | Scalar `True` for BOTH branches | Fix outcome swallowed | `(True, True)` / `(True, False)` |
| `test__process_interactive_error_calls_correct_handler` | Scalars (`True`/`False`) + scalar mock | Tuple return not tested | Tuple assertions + tuple mock |
| `test__process_all_errors_noninteractive_iterates_all` (removed) | `return_value=None`, `success_count == 0` | Directly asserts the bug | Replaced by two tests covering True/False paths |
| `test__process_all_errors_interactive_breaks_on_quit` | `return_value=False` (scalar) | Incompatible mock type post-fix | `return_value=(False, False)` |
