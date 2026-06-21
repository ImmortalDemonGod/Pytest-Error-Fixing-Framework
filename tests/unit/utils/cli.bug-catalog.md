# Bug Catalog: `src/branch_fixer/utils/cli.py`

**Produced by:** design-tests skill, finding F15
**Date:** 2026-06-21
**Canonical audit source:** https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L11
**Test file:** `tests/unit/utils/test_cli_f15.py`

---

## Public Interface Summary

`CLI` is the top-level orchestrator for the pytest-fixer CLI.  Key surface relevant to this finding:

- `process_errors(errors, interactive) -> int` — main entry point; returns 0 on full success, 1 on any failure or partial run.  Delegates to `_process_all_errors`.
- `_process_all_errors(errors, interactive) -> Tuple[int, int]` — loops over errors, calls `_process_non_interactive_error` or `_process_interactive_error`, returns `(total_processed, success_count)`.
- `_process_non_interactive_error(error)` — calls `self.run_fix_workflow(error, interactive=False)` for its side effects; return type is implicitly `None`.
- `run_fix_workflow(error, interactive) -> bool` — returns `True` on fix success, `False` on failure.

**Load-bearing comment (line 538):**
> `# If you track actual success/fail logic, you can increment success_count here.`
>
> This is an explicit acknowledgement that the increment was never implemented.

**IO boundaries:** subprocess via `run_fix_workflow`, git ops, click output.

**Branching points in `_process_all_errors`:**
1. `self._exit_requested` early-exit.
2. `interactive` branch → `_process_interactive_error` vs `_process_non_interactive_error`.
3. `_process_interactive_error` returns `bool` for "continue/quit" semantics — NOT success semantics.

**Existing tests that document (and accept) broken behavior:**
- `tests/unit/utils/test_cli.py::TestCLI::test__process_all_errors_noninteractive_iterates_all` — asserts `success_count == 0` while patching `_process_non_interactive_error` entirely; passes only because the mock hides the real call chain.

---

## Bug Catalog

### Bug B1 (PRIMARY — F15): `_process_non_interactive_error` discards fix outcome; `success_count` never incremented

**Failure mode:** `_process_all_errors` always returns `success_count == 0` regardless of how many fixes succeed, because `_process_non_interactive_error` calls `run_fix_workflow` for its echo side-effect only and returns `None`; `_process_all_errors` never reads that result.

**Blast radius:** `process_errors` returns exit-code 1 on every run with ≥ 1 error processed (since `0 == total_processed` is False when `total_processed > 0`), even when every fix succeeded.  Callers that check the exit code to decide whether to push/open PRs will always see "failure."

**Why plausible:** The placeholder comment at line 538 (`If you track actual success/fail logic, you can increment success_count here`) marks the gap exactly.  The `_process_non_interactive_error` return type is implicitly `None` — the architecture never threaded the result back.

**Test type:** Captured bug / Contract pin (non-interactive path)

**Catalog tests:**
- `test__process_all_errors_success_count_is_one_when_single_non_interactive_fix_succeeds` → **RED**
- `test__process_all_errors_success_count_tracks_partial_successes_non_interactive` → **RED**
- `test_process_errors_returns_exit_code_0_when_all_non_interactive_fixes_succeed` → **RED** (integration layer)

---

### Bug B2: `success_count` in `process_errors` (line 479) is dead-code initialisation

**Failure mode:** `process_errors` initialises `success_count = 0` at line 479, then unconditionally overwrites it with the value returned by `_process_all_errors` at line 489.  The initial assignment is never read before it is replaced.

**Blast radius:** None — pure dead code.  Misleads readers into thinking `success_count` is intentionally tracked at this layer.

**Why plausible:** Copy-paste of the inner function's local variables at the outer scope when the helper was extracted.

**Test type:** N/A — cosmetic, deferred.

**Deferred.** Zero blast radius; cosmetic cleanup, not a correctness issue.

---

### Bug B3 (SAME CLASS, interactive path): interactive fix success is also untracked

**Failure mode:** In interactive mode, `_process_interactive_error` returns `True/False` for "continue/quit" semantics, not for "this fix succeeded."  Even when the user triggers an AI fix that succeeds (`_handle_ai_fix_choice` → `run_fix_workflow` → `True`), that success is never surfaced back to `_process_all_errors`.  So `success_count` remains 0 for interactive runs too.

**Blast radius:** Same as B1 — exit code is always 1 for interactive runs where fixes succeeded.

**Why plausible:** The interactive handler chain was designed around "should we break the loop?" not "did the fix succeed?".  The two semantics were conflated.

**Test type:** Captured bug / Contract pin (interactive path)

**Catalog test:**
- `test__process_all_errors_success_count_is_one_when_interactive_fix_succeeds` → **RED**

**Note:** Fixing B1 and B3 requires threading fix-outcome through two different call chains (non-interactive: `_process_non_interactive_error` return; interactive: `_handle_ai_fix_choice` and `_handle_manual_fix_choice` propagation).  B1 (non-interactive) is the simpler and higher-blast-radius path, so tests focus there first.

---

## Skipped / Explicitly Not Tested

| Item | Reason |
|---|---|
| `success_count` dead-code init at line 479 (B2) | Zero blast radius; cosmetic cleanup. |
| Interactive handler chain propagation (B3 full fix) | Architectural complexity; the interactive fix-success propagation requires restructuring the handler return semantics.  B1 captures the invariant; B3 is deferred. |
| `_exit_requested` early-exit affecting success_count | The `total_processed < total_errors` guard (line 504) already returns 1 in this case, so the success_count bug is irrelevant on that path. |
| `process_errors` with `errors=[]` | Returns 0 correctly (0==0 guard passes); no bug. |
| Signal handler behaviour | Already tested in existing `test_cli.py`. |

---

## Self-Critique

**B1 tests: what bug do they catch?**
`success_count` stays 0 regardless of `run_fix_workflow` outcome — the tests catch the missing increment.

**Would they pass for wrong-but-stable output?**
No.  The tests assert `success_count == 1` (or 2) which is only reachable if the increment actually runs.  Asserting `== 0` would be wrong-but-stable; we assert the correct non-zero value.

**Would they fail under a behaviour-preserving refactor?**
No — they assert on the return value of `_process_all_errors` (observable output), not on internal call counts.

---

## Post-Run Evaluation (to be filled after tests run)

- **Bugs caught (test failed first run):** TBD — expected B1 to be caught
- **Bugs characterised (test passed first run):** TBD
- **Bugs discovered during writing:** B2 (dead-code initialisation), B3 (interactive path untracked)
