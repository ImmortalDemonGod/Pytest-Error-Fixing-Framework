# Oracle correction: pef-p20-make-setup-logging-idempoten

## Changed pre-existing test

- `tests/unit/config/test_logging_config.py::test_repeated_calls_add_snoop_handler_but_basicconfig_is_noop_for_root`

## Why this pre-existing test was wrong for this finding

Finding F37 (audit/02-static-audit.md#L31) documents that `setup_logging()`
appends a new `FileHandler` to the `snoop` logger on every call, so calling
it twice (as the normal run path does — `main.py:11` and `run_cli.py:94`)
leaves two duplicate handlers attached and duplicates every log line.

`test_repeated_calls_add_snoop_handler_but_basicconfig_is_noop_for_root`
asserted `len(snoop_handlers_after) == len(snoop_handlers_before) + 1`
after two calls to `setup_logging()` — i.e. it encoded the buggy duplicate-
handler behavior itself as the expected, correct outcome. It is not an
independent oracle of desired behavior; it is a regression pin for the bug
described in the finding.

The finding's own acceptance command (`GOAL` in F37) is:

```
.venv/bin/python -c "import logging; from branch_fixer.config.logging_config import setup_logging; \
setup_logging(); a=len(logging.getLogger('snoop').handlers); setup_logging(); \
b=len(logging.getLogger('snoop').handlers); assert a==b, (a,b)"
```

which directly contradicts the old assertion (`b == a + 1`). Keeping the old
assertion would make it impossible to ever land a correct fix for F37/F43.

## What changed

`src/branch_fixer/config/logging_config.py::setup_logging` now clears any
pre-existing handlers on the `snoop` logger before attaching a new one, so
repeated calls are idempotent (no duplicate `FileHandler`).

The test was updated in place (same test name, same structure) to assert
`len(snoop_handlers_after) == len(snoop_handlers_before)` — i.e. the second
`setup_logging()` call must not add a new snoop handler — matching the
finding's GOAL and the intent at
https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L31.

No other assertion in this test file was touched; the `root_handlers`
assertion (basicConfig is a no-op on repeated calls) is unchanged.
