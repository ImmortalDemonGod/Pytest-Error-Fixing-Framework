# Bug catalog — pef-p03-harden-hypot-test-gen-subpro (F33–F36)

- **Shell command injection via `shell=True`** — `scripts/hypot_test_gen.py:239,247`
  (`TestGenerator.run_hypothesis_write`). `full_cmd = f"hypothesis write {command}"` is passed to
  `subprocess.run(full_cmd, shell=True, ...)`. `command` embeds `entity.module_path`, which is
  derived from a caller-supplied filesystem path via `construct_module_path` (`scripts/hypot_test_gen.py:405-415`).
  A path containing shell metacharacters (`$(...)`, backticks, `;`, `&&`) is interpreted by `/bin/sh`
  and executes arbitrary commands. Wrong: `$(touch pwned)` in the derived command actually runs
  `touch pwned`. Correct: the command is invoked as an argv list with no shell interpretation, so
  metacharacters are passed through literally as inert text and never executed.

- **`max_retries` parameter is ignored by the failure handler** — `scripts/hypot_test_gen.py:377-386`
  (`TestGenerator.handle_failed_attempt`). `try_generate_test(..., max_retries=N)` loops
  `attempt in range(1, N + 1)` but `handle_failed_attempt` hardcodes `if attempt < 3:` instead of
  comparing against the caller's `max_retries`. Wrong: with `max_retries=5`, attempts 3 and 4 already
  hit the `else` branch and log "All attempts failed" (the terminal-failure message) three times
  (attempts 3, 4, 5) while only attempts 1–2 get the retry-and-sleep treatment. Correct: retry-wait
  (with sleep) fires on attempts `1..max_retries-1`, and the terminal "all attempts failed" message
  fires exactly once, only on the final attempt (`attempt == max_retries`).

- **`hypothesis` invoked via bare `PATH` lookup instead of the venv-local binary** —
  `scripts/hypot_test_gen.py:239` (`TestGenerator.run_hypothesis_write`). `full_cmd` starts with the
  literal string `"hypothesis"`, resolved by the shell against `$PATH`. Wrong: this can silently
  invoke a different `hypothesis` executable than the one installed in the active virtualenv (or none
  at all if `PATH` doesn't include the venv's `bin/`), unlike the DDD `HypothesisStrategy._hypothesis_bin()`
  (`src/dev/test_generator/generate/strategies/hypothesis.py:609-612`), which resolves
  `Path(sys.executable).parent / "hypothesis"`. Correct: the subprocess is invoked against the
  absolute, venv-pinned `hypothesis` binary path, never a bare `PATH`-resolved name.

- **Module-level `snoop.install()` side effect at import time** — `scripts/hypot_test_gen.py:25`.
  `snoop.install(out=Path("snoop_debug.log"))` runs unconditionally as soon as
  `scripts.hypot_test_gen` is imported (not gated behind `if __name__ == "__main__"` or lazy
  initialization), globally patching builtins (`snoop`, `pp`, `spy`) as a side effect of import alone.
  This is captured as a regression guard: importing the module must not eagerly create
  `snoop_debug.log` on disk as an import-time side effect (currently true only because `snoop`'s
  `FileWriter` opens lazily on first write — the `install()` call itself remains an unwanted
  module-import side effect that should be removed/guarded as part of hardening this file).
