# Bug catalog — pef-p17-remove-unconditional-collect

- **Unconditional per-item stdout print during test collection**
  `src/branch_fixer/services/pytest/runner.py:61` (inside
  `PytestPlugin.pytest_collection_modifyitems`, `src/branch_fixer/services/pytest/runner.py:57-61`)
  — **Wrong:** the hook unconditionally calls `print(f"  - {item.nodeid}")` for every item in
  `items` on every collection pass, emitting unbounded `  - <nodeid>` lines to stdout regardless
  of caller, verbosity setting, or context.
  **Correct:** collecting tests via the plugin must produce **no** per-item stdout output at all
  (`  - <nodeid>` lines must not appear on stdout) — the hook must not print, so it cannot pollute
  CLI output or interfere with the caller's own output parsing (e.g.
  `PytestRunner.capture_test_output`, which parses captured session output elsewhere in this same
  file).
