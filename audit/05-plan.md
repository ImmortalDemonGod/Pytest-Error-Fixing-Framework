# 05 — Execution-Ready Plan

_44 ordered, dependency-sorted change items. Each links to a Stage-2 finding or Stage-4 goal signal, is localized to a path, and carries a verification signal. Validated by an independent reviewer — no ambiguous items remain._

**Sequencing:** Ordering is dependency-sorted into bands. Band 1 (P01-P04, order 1-4): security fixes — independent, fast, highest-severity-per-effort (F13 hardcoded token is the single security/high), no deps. Band 2 (P05-P11, order 5-11): primary-goal fix-delivery correctness — the cluster that makes the tool actually safe and autonomous. P05 fixes the broken PR-before-push path (F86/F84); P06 stops transient API failures from aborting the whole session and is a prerequisite for honest success accounting (P08) and orchestrator session-count fixes (P27); P07 stops collection errors burning the retry budget; P09 (recovery async/sync) must land before P10 (real file restore) because P10's restore runs through the now-synchronous recovery API; P11 removes the dev_force_success bypass that otherwise lets the pipeline fake success. Band 3 (P12-P15): git/repository correctness (branch isolation + push/pull/merge semantics) — independent of each other. Band 4 (P16-P19): pytest runner/parser correctness — P16/P18 feed the later fault-localization work. Band 5 (P20-P21): logging idempotency and dependency hygiene. Band 6 (P22-P27): dead-code deletion and design cleanup; P23's deletion is justified by grep evidence that SessionCoordinator is referenced only in docs/audits, never imported by src/ or tests/. Band 7 (P28-P33): test-suite integrity — P28 depends on P20+P24 because it asserts the behavior those items introduce; the rest harden weak/always-true assertions and CI. Band 8 (P34-P40): documentation drift and remaining design no-ops (P40 also fixes real session-lifecycle bugs F16/F82, grouped here because they are low-blast-radius). Band 9 (P41-P44): goal-2 (SWE-bench/APR) research-driven enhancements, intentionally last because they build on the now-correct pipeline: P41 (traceback fault localization) is the highest-ROI and gates P43 (multi-candidate sampling) and P44 (BM25 retrieval); P42 (structured failure injection) builds on the guarded retry loop from P06. Items within a band that share no depends_on edge may be parallelized; the CLAUDE.md '1 file per commit' rule means multi-file items (P03, P05, P09, P24, P32, P37, P39, P40) must be split into per-file commits during execution.

| # | ID | Change | Location | Links | Effort | Depends |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | P01 | Remove hardcoded CodeScene API token | `scripts/analyze_code.sh:119` | F13 | S | — |
| 2 | P02 | Verify CodeScene CLI installer before executing | `scripts/analyze_code.sh:95-99` | F14 | S | — |
| 3 | P03 | Harden hypot_test_gen subprocess + retry + import-time snoop | `scripts/hypot_test_gen.py:25,239,247,381` | F33,F34,F35,F36 | M | — |
| 4 | P04 | Stop silently defaulting SECRET_KEY to empty string | `src/branch_fixer/config/settings.py:6` | F53 | S | — |
| 5 | P05 | Push branch before creating PR; return real bool from create_pull_request_sync | `src/branch_fixer/utils/cli.py:220-226 + src/branch_fixer/services/git/repository.py:544-568 + src/branch_fixer/services/git/pr_manager.py:71-112` | F86,F84 | M | — |
| 6 | P06 | Guard transient API failures inside the retry loop | `src/branch_fixer/orchestration/orchestrator.py:357 + src/branch_fixer/orchestration/fix_service.py:140-167` | F88,F38 | M | — |
| 7 | P07 | Short-circuit pytest collection errors out of the fix pipeline | `src/branch_fixer/services/pytest/error_processor.py:49-54 + src/branch_fixer/orchestration/fix_service.py (attempt_fix entry)` | F87 | M | — |
| 8 | P08 | Track real fix success and return correct exit code | `src/branch_fixer/utils/cli.py:519,538-539,552` | F15 | M | P06 |
| 9 | P09 | Resolve async/sync mismatch in RecoveryManager callers | `src/branch_fixer/storage/recovery.py:135,174,225 + src/branch_fixer/orchestration/orchestrator.py:393,516` | F83 | M | — |
| 10 | P10 | Make restore_checkpoint actually restore files and log via logging | `src/branch_fixer/storage/recovery.py:200-263` | F39,F40 | M | P09 |
| 11 | P11 | Remove dev_force_success bypass and decouple interactive flag | `src/branch_fixer/utils/cli.py:325,344-348 + src/branch_fixer/orchestration/orchestrator.py:351` | F23,F85,F29 | M | — |
| 12 | P12 | Implement branch_manager metadata and merged-check methods | `src/branch_fixer/services/git/branch_manager.py:169,225` | F7,F8 | M | — |
| 13 | P13 | Let _find_git_root resolve repo root from a subdirectory | `src/branch_fixer/services/git/repository.py:87-91` | F66 | S | — |
| 14 | P14 | Implement pull() so sync_with_remote returns a bool | `src/branch_fixer/services/git/repository.py:352,590-593` | F68 | M | — |
| 15 | P15 | Align push/merge return semantics with docstrings | `src/branch_fixer/services/git/repository.py:314,325-335,612` | F67,F69,F78 | M | — |
| 16 | P16 | Fix runner nodeid unpacking and skipped-test accounting | `src/branch_fixer/services/pytest/runner.py:218,388-415,173-183` | F1,F2 | M | — |
| 17 | P17 | Remove unconditional collection debug print in runner | `src/branch_fixer/services/pytest/runner.py:59-80` | F3 | S | — |
| 18 | P18 | Broaden failure_parser regex to non-Error exception names | `src/branch_fixer/services/pytest/parsers/failure_parser.py:9` | F52 | S | — |
| 19 | P19 | Avoid importing ExitCode from pytest private module | `src/branch_fixer/services/pytest/models.py:7` | F9 | S | — |
| 20 | P20 | Make setup_logging idempotent and call it once | `src/branch_fixer/config/logging_config.py:30-37 + src/branch_fixer/utils/run_cli.py:94` | F37,F43 | S | — |
| 21 | P21 | Remove snoop from hard runtime dependencies | `src/branch_fixer/utils/workspace.py:20` | F63 | S | — |
| 22 | P22 | Delete dead exception taxonomy and stub dispatcher | `src/branch_fixer/core/exceptions.py:2-29 + src/branch_fixer/orchestration/dispatcher.py:5-41` | F5,F6 | S | — |
| 23 | P23 | Delete dead SessionCoordinator class | `src/branch_fixer/orchestration/coordinator.py` | F70,F71 | S | — |
| 24 | P24 | Implement update_pr mutation; fix pr_id collisions and modified_files; document deferred PR methods | `src/branch_fixer/services/git/pr_manager.py:43-44,66,114-186` | F49,F58,F59,F60,F61 | M | — |
| 25 | P25 | Remove misleading empty original_code from CodeChanges | `src/branch_fixer/core/models.py:112-115 + src/branch_fixer/services/ai/manager.py:317` | F26 | S | — |
| 26 | P26 | Remove redundant inner import and use tz-aware PR timestamps | `src/branch_fixer/services/ai/manager.py:217 + src/branch_fixer/services/git/models.py:87-88` | F17,F42 | S | — |
| 27 | P27 | Fix orchestrator per-error temperature, session counts, and FixService reuse | `src/branch_fixer/orchestration/orchestrator.py:248-273,344-356,428-430` | F50,F51,F62 | M | P06 |
| 28 | P28 | Rewrite codified-bug tests to assert corrected behavior | `tests/unit/git/test_pr_manager.py:139-148 + tests/unit/config/test_logging_config.py:166-182` | F11,F12 | S | P20,P24 |
| 29 | P29 | Fix always-true and broken-raise test assertions | `tests/unit/services/pytest/test_runner.py:470 + tests/unit/orchestration/test_orchestrator.py:583,589` | F72,F73 | S | — |
| 30 | P30 | Strengthen weak e2e and fabric-strategy assertions | `tests/integration/test_generator_e2e.py:171-182 + tests/test_generator/test_strategy_fabric.py:231,244` | F24,F81 | S | — |
| 31 | P31 | Restore sys.modules after monkeypatched import in test | `tests/unit/utils/test_run_cli.py:179` | F25 | S | — |
| 32 | P32 | Remove non-coverage test, split misorganized conftest, drop duplicate parser tests | `tests/test_math_operations.py:3-8 + tests/integration/pytest/conftest.py:12-30 + tests/unit/pytest/parsers/test_unified_error_parser.py` | F65,F79,F10 | M | — |
| 33 | P33 | Run pytest in CI and make security audit gating explicit | `.github/workflows/deploy.yml + .github/workflows/ci.yml:56-57` | F32,F28 | S | — |
| 34 | P34 | Correct API-key env var in user/dev docs | `README.md:52 + docs/developer-guide/04-execution-flow.md:18` | F20,F54 | S | — |
| 35 | P35 | Fix contributor test-command drift to venv python | `docs/developer-guide/02-contribution-guide.md:54 + CONTRIBUTING.md:39` | F19,F74 | S | — |
| 36 | P36 | Correct stale design/execution-flow doc references | `docs/design-and-research/01-strategic-analysis.md:49,131 + docs/developer-guide/04-execution-flow.md:118,148-156 + audits/QUALITY_AUDIT.md:46` | F44,F45,F55,F56,F4 | S | — |
| 37 | P37 | Fix stale path comments, src.-prefixed imports, and placeholder artifacts | `tests/unit/core/test_verify_fix_workflow.py:1 + src/branch_fixer/storage/recovery.py:11-14 + src/branch_fixer/storage/state_manager.py:9-10 + scripts/runner_debug.py:1 + pyproject.toml:5 + scripts/setup_project.sh:7 + docs/developer-guide/prompts/Code-Refactoring-Instructions.md:23 + .taskmaster/docs/prd.txt:348-350` | F21,F41,F57,F75,F76,F77,F22,F80 | M | — |
| 38 | P38 | Fix reversed() doc example, venv Python version, and coverage runner | `docs/reference/hypothesis-guide.md:162 + Taskfile.yml:29 + scripts/analyze_code.sh:290-295` | F47,F46,F27 | S | — |
| 39 | P39 | Clean up inert skip-set, dev-local path, dedup rules, and doc-hygiene artifacts | `src/dev/test_generator/analyze/parser.py:53,152 + scripts/runner_debug.py:23 + .windsurfrules:524 + docs/design-and-research/02-swe-bench-strategy.md:1-185 + docs/aiv-packet-pr9.yaml:35-36,356-358` | F18,F48,F31,F64,F30 | M | — |
| 40 | P40 | Use a single multi-error orchestrator session and implement validate_session_state | `src/branch_fixer/utils/cli.py:210-211 + src/branch_fixer/storage/state_manager.py:142-156` | F16,F82 | M | — |
| 41 | P41 | Add traceback-based fault localization to the AI prompt | `src/branch_fixer/services/ai/manager.py (prompt build) + src/branch_fixer/services/pytest/parsers/failure_parser.py / error_processor.py` | GOAL:Reach SWE-bench-level autonomous source-code program repair (Pass@1) | research: Agentless/AutoCoderRover/fault-localization-context | L | P16,P18 |
| 42 | P42 | Inject exact failing assertion + buggy lines into the capped retry conversation | `src/branch_fixer/services/ai/manager.py (self._messages thread) + orchestrator.fix_error retry loop` | GOAL:Safe autonomous pytest-failure repair tool | research: ChatRepair conversational repair (<=5 rounds) | M | P06 |
| 43 | P43 | Multi-candidate patch sampling with test-based selection | `src/branch_fixer/orchestration/orchestrator.py (fix_error loop) + src/branch_fixer/orchestration/fix_service.py` | GOAL:Reach SWE-bench-level autonomous source-code program repair (Pass@1) | research: Agentless sampling / SWT-Bench ensemble | L | P06,P41 |
| 44 | P44 | Add BM25 retrieval pre-filter before the LLM call | `new module under src/branch_fixer/services/ai/ (retrieval) + src/branch_fixer/services/ai/manager.py context build` | GOAL:Reach SWE-bench-level autonomous source-code program repair (Pass@1) | research: SWE-Fixer BM25 coarse-to-fine retrieval | L | P41 |

## Item detail

### 1. Remove hardcoded CodeScene API token (`P01`)

- **Location:** `scripts/analyze_code.sh:119`
- **Links to:** F13
- **Change:** Delete the `export CS_ACCESS_TOKEN="<REDACTED-CodeScene-token>"` unconditional fallback. Require CS_ACCESS_TOKEN to come from the environment; if unset, print an explicit error and exit non-zero rather than embedding a credential. Rotate/revoke the leaked token out-of-band.
- **Verification signal:** Grep for the literal token string across the repo returns zero hits; running analyze_code.sh with CS_ACCESS_TOKEN unset exits non-zero with a clear message instead of using a baked-in token.
- **Depends on:** none · **Effort:** S


### 2. Verify CodeScene CLI installer before executing (`P02`)

- **Location:** `scripts/analyze_code.sh:95-99`
- **Links to:** F14
- **Change:** Replace `curl -sSf <url> | sh` with: download the installer to a temp file, compare its sha256 against a pinned expected hash, and only execute on match; abort on mismatch.
- **Verification signal:** Mutating the downloaded installer byte causes the script to abort before execution; an unmodified installer with the pinned hash installs normally.
- **Depends on:** none · **Effort:** S


### 3. Harden hypot_test_gen subprocess + retry + import-time snoop (`P03`)

- **Location:** `scripts/hypot_test_gen.py:25,239,247,381`
- **Links to:** F33,F34,F35,F36
- **Change:** (a) Build the hypothesis invocation as an argv list and call subprocess.run without shell=True (F33). (b) Invoke the venv-local binary via Path(sys.executable).parent / "hypothesis" instead of bare `hypothesis` (F34). (c) Replace the hardcoded `if attempt < 3` retry guard with `if attempt < max_retries` (F35). (d) Move `snoop.install(out=Path('snoop_debug.log'))` out of module import scope into a guarded main()/CLI-flag path (F36).
- **Verification signal:** A source path containing spaces/`$()`/backticks no longer injects shell commands; with max_retries=5 the retry-wait fires on attempts 1-4 and the final-failure error only on attempt 5; importing the module does not create snoop_debug.log; subprocess uses the venv hypothesis binary.
- **Depends on:** none · **Effort:** M


### 4. Stop silently defaulting SECRET_KEY to empty string (`P04`)

- **Location:** `src/branch_fixer/config/settings.py:6`
- **Links to:** F53
- **Change:** When BRANCH_FIXER_SECRET_KEY is unset, log a clear warning (or raise in security-sensitive contexts) instead of silently defaulting to "". Do not allow an empty-string key to be used for any HMAC/token operation.
- **Verification signal:** Importing settings.py without the env var emits a warning/raises; no code path uses an empty-string secret key.
- **Depends on:** none · **Effort:** S


### 5. Push branch before creating PR; return real bool from create_pull_request_sync (`P05`)

- **Location:** `src/branch_fixer/utils/cli.py:220-226 + src/branch_fixer/services/git/repository.py:544-568 + src/branch_fixer/services/git/pr_manager.py:71-112`
- **Links to:** F86,F84
- **Change:** Reorder the CLI delivery path so the branch push (cli.py:226) executes BEFORE create_pull_request_sync (cli.py:220), since GitHub requires the remote branch to exist before `gh pr create`. Change create_pull_request_sync (repository.py:568) to return a real bool — True only when `gh pr create` exits 0 and the resulting PRDetails.url is non-None — instead of returning the always-truthy PRDetails object. Update the cli.py:220 boolean guard to consume that bool.
- **Verification signal:** End-to-end/manual run: a failed `gh pr create` now yields False and is logged as a failure (not 'Created pull request successfully'); on success the remote branch exists prior to PR creation and PRDetails.url is populated.
- **Depends on:** none · **Effort:** M


### 6. Guard transient API failures inside the retry loop (`P06`)

- **Location:** `src/branch_fixer/orchestration/orchestrator.py:357 + src/branch_fixer/orchestration/fix_service.py:140-167`
- **Links to:** F88,F38
- **Change:** Wrap the `fix_service.attempt_fix(...)` call in fix_error's `for` retry loop in a try/except FixServiceError that logs and continues to the next retry (with the temperature bump) rather than letting the exception escape the loop on attempt 1. Also collapse the double-wrap in fix_service.attempt_fix (inner except at 140-143 re-raised again at 165-167) so the original diagnostic message is preserved (F38).
- **Verification signal:** Unit test injecting a CompletionError on attempt 1 shows the loop proceeds through attempts 2..max_retries instead of aborting the session; the surfaced FixServiceError message retains the inner cause text.
- **Depends on:** none · **Effort:** M


### 7. Short-circuit pytest collection errors out of the fix pipeline (`P07`)

- **Location:** `src/branch_fixer/services/pytest/error_processor.py:49-54 + src/branch_fixer/orchestration/fix_service.py (attempt_fix entry)`
- **Links to:** F87
- **Change:** Detect the synthetic collection-error TestError (test_file == Path('unknown_collection_file.py') / test_function == 'pytest_collection') and short-circuit before generate_fix() is called, returning a non-retryable failure. This prevents burning max_retries AI calls that are guaranteed to fail at _backup_file with FileNotFoundError.
- **Verification signal:** A collection error produces zero AI/generate_fix calls and an immediate non-retryable skip; assert the AI manager is not invoked and the retry budget is not consumed.
- **Depends on:** none · **Effort:** M


### 8. Track real fix success and return correct exit code (`P08`)

- **Location:** `src/branch_fixer/utils/cli.py:519,538-539,552`
- **Links to:** F15
- **Change:** Increment success_count when _generate_and_apply_fix reports a successful, verified fix; have process_errors return 0 when at least one fix succeeded (per intended semantics) rather than always 1; correct the summary line so it reports the actual count instead of a constant 'Successfully fixed: 0'.
- **Verification signal:** A run that successfully fixes >=1 error returns exit code 0 and prints the true success count; a run that fixes none returns non-zero.
- **Depends on:** P06 · **Effort:** M


### 9. Resolve async/sync mismatch in RecoveryManager callers (`P09`)

- **Location:** `src/branch_fixer/storage/recovery.py:135,174,225 + src/branch_fixer/orchestration/orchestrator.py:393,516`
- **Links to:** F83
- **Change:** Make create_checkpoint/restore_checkpoint/handle_failure synchronous (remove `async`) to match the synchronous orchestrator callers and the synchronous test stubs in test_orchestrator.py:565-598. Update test_recovery.py:134-198 to drop @pytest.mark.asyncio/await. (Sync chosen over awaiting because both production callers are sync and recovery does no real I/O concurrency.)
- **Verification signal:** orchestrator._create_checkpoint_if_needed receives a RecoveryPoint so `checkpoint.id` works (no AttributeError); handle_error returns True only when real recovery ran, not because a coroutine object is truthy; recovery tests pass without asyncio markers.
- **Depends on:** none · **Effort:** M


### 10. Make restore_checkpoint actually restore files and log via logging (`P10`)

- **Location:** `src/branch_fixer/storage/recovery.py:200-263`
- **Links to:** F39,F40
- **Change:** Implement the restore loop body (currently `pass` at line 213) to restore each modified file from its backup. Replace the print() diagnostics at 241-263 with the standard logging module used elsewhere.
- **Verification signal:** Unit test: a file modified after a checkpoint is restored to its backup content by restore_checkpoint; recovery diagnostics appear via the logger, not stdout.
- **Depends on:** P09 · **Effort:** M


### 11. Remove dev_force_success bypass and decouple interactive flag (`P11`)

- **Location:** `src/branch_fixer/utils/cli.py:325,344-348 + src/branch_fixer/orchestration/orchestrator.py:351`
- **Links to:** F23,F85,F29
- **Change:** Remove the dev_force_success short-circuit so the pipeline always invokes the AI service: drop dev_force_success from the FixService construction (cli.py:325) and remove/neutralize the --dev-force-success flag; stop deriving interactive from dev_force_success (cli.py:347) by passing an explicit `interactive=config.interactive`; remove the hardcoded `dev_force_success=False` placeholder in orchestrator.fix_error (orchestrator.py:351).
- **Verification signal:** The fix pipeline always calls the AI manager (no silent success path); running in --non-interactive never triggers interactive prompts inside the orchestrator; --dev-force-success no longer appears in CLI help.
- **Depends on:** none · **Effort:** M


### 12. Implement branch_manager metadata and merged-check methods (`P12`)

- **Location:** `src/branch_fixer/services/git/branch_manager.py:169,225`
- **Links to:** F7,F8
- **Change:** Implement get_branch_metadata (populate BranchMetadata from GitPython refs/commit data) and is_branch_merged (decide via `git branch --merged`/merge-base against the target branch), replacing the unconditional NotImplementedError raises. These support the primary-goal branch-isolation guarantees.
- **Verification signal:** Unit tests: get_branch_metadata returns a populated BranchMetadata for a known branch; is_branch_merged returns True for a merged branch and False for an unmerged one, without raising.
- **Depends on:** none · **Effort:** M


### 13. Let _find_git_root resolve repo root from a subdirectory (`P13`)

- **Location:** `src/branch_fixer/services/git/repository.py:87-91`
- **Links to:** F66
- **Change:** Remove the premature `(root / '.git').exists()` check that raises NotAGitRepositoryError before GitPython runs; instead call Repo(root, search_parent_directories=True) and translate InvalidGitRepositoryError into NotAGitRepositoryError. This makes search_parent_directories=True effective.
- **Verification signal:** Calling with a subdirectory (e.g. cwd=src/) of a git repo resolves the repo root instead of raising NotAGitRepositoryError.
- **Depends on:** none · **Effort:** S


### 14. Implement pull() so sync_with_remote returns a bool (`P14`)

- **Location:** `src/branch_fixer/services/git/repository.py:352,590-593`
- **Links to:** F68
- **Change:** Implement pull() via run_command (`git pull`) instead of raising NotImplementedError so sync_with_remote() can return True/False. Keep the except GitError handler meaningful for non-zero results.
- **Verification signal:** sync_with_remote() returns a bool on success/failure and never propagates NotImplementedError; unit test covers the success and GitError paths.
- **Depends on:** none · **Effort:** M


### 15. Align push/merge return semantics with docstrings (`P15`)

- **Location:** `src/branch_fixer/services/git/repository.py:314,325-335,612`
- **Links to:** F67,F69,F78
- **Change:** Because run_command raises GitError on any non-zero returncode, make the failure contract consistent: have push() surface GitError per its docstring (remove the blanket `except Exception: return False` at 333-335 that silently swallows failures) and remove the now-dead `else` branch at 328; document that merge_branch (612) signals failure via GitError rather than a bool that is always True. Pick one contract (raise-on-failure) and apply it to push/merge consistently.
- **Verification signal:** A failing push raises GitError (matching the push docstring) instead of returning False/None; the dead else/log-error branch at 328-329 is gone; merge_branch failure is reachable and tested.
- **Depends on:** none · **Effort:** M


### 16. Fix runner nodeid unpacking and skipped-test accounting (`P16`)

- **Location:** `src/branch_fixer/services/pytest/runner.py:218,388-415,173-183`
- **Links to:** F1,F2
- **Change:** Guard `test_id.split('::', 1)` so a nodeid without '::' does not raise ValueError (e.g. handle the 1-element case). In _handle_outcome_logic, set result.skipped = True for skipped outcomes and exclude skipped from result.passed; ensure _count_individual_result increments session.skipped, including setup-phase skips where call_outcome stays None.
- **Verification signal:** format_test_failures handles a nodeid with no '::' without raising; a @pytest.mark.skip test is counted as skipped (session.skipped incremented) and not as passed.
- **Depends on:** none · **Effort:** M


### 17. Remove unconditional collection debug print in runner (`P17`)

- **Location:** `src/branch_fixer/services/pytest/runner.py:59-80`
- **Links to:** F3
- **Change:** Delete the unconditional `print(f'  - {item.nodeid}')` at line 61 (leftover debug instrumentation) and the surrounding stale commented-out prints at lines 59,66,72,80 so the collection hook emits no stray stdout.
- **Verification signal:** Collecting tests via the plugin produces no per-item stdout lines; downstream output parsing sees clean output (grep of runner.py shows no nodeid print in pytest_collection_modifyitems).
- **Depends on:** none · **Effort:** S


### 18. Broaden failure_parser regex to non-Error exception names (`P18`)

- **Location:** `src/branch_fixer/services/pytest/parsers/failure_parser.py:9`
- **Links to:** F52
- **Change:** Extend the exception-name capture group so it matches exception classes ending in 'Exception'/'Interrupt'/'Iteration' and arbitrary custom exception identifiers, not only names containing 'Error'. Use a broader identifier pattern for the exception type token.
- **Verification signal:** Parser unit test: failures raising StopIteration, KeyboardInterrupt, and a CustomException are captured instead of being silently dropped.
- **Depends on:** none · **Effort:** S


### 19. Avoid importing ExitCode from pytest private module (`P19`)

- **Location:** `src/branch_fixer/services/pytest/models.py:7`
- **Links to:** F9
- **Change:** Import ExitCode from the public `pytest` namespace (`from pytest import ExitCode`) if available, with a guarded fallback, instead of `from _pytest.main import ExitCode`.
- **Verification signal:** models.py imports successfully without referencing the `_pytest` private package; grep shows no `_pytest` import remaining.
- **Depends on:** none · **Effort:** S


### 20. Make setup_logging idempotent and call it once (`P20`)

- **Location:** `src/branch_fixer/config/logging_config.py:30-37 + src/branch_fixer/utils/run_cli.py:94`
- **Links to:** F37,F43
- **Change:** Before adding the snoop FileHandler, check whether an equivalent handler is already attached and skip if so (guard against accumulation). Remove the duplicate setup_logging() call so it runs once in the entrypoint (keep main.py:11, drop the call inside fix() at run_cli.py:94, or vice versa).
- **Verification signal:** Calling setup_logging() twice adds no duplicate snoop FileHandler (len before == len after); a full run shows exactly one snoop handler.
- **Depends on:** none · **Effort:** S


### 21. Remove snoop from hard runtime dependencies (`P21`)

- **Location:** `src/branch_fixer/utils/workspace.py:20`
- **Links to:** F63
- **Change:** Remove "snoop" from REQUIRED_DEPENDENCIES so check_dependencies() no longer raises ImportError when the debug-only snoop library is absent.
- **Verification signal:** On an environment without snoop installed, the tool starts and check_dependencies() passes (does not raise ImportError).
- **Depends on:** none · **Effort:** S


### 22. Delete dead exception taxonomy and stub dispatcher (`P22`)

- **Location:** `src/branch_fixer/core/exceptions.py:2-29 + src/branch_fixer/orchestration/dispatcher.py:5-41`
- **Links to:** F5,F6
- **Change:** After confirming no runtime imports, delete the unused FixError/CoordinationError/WorkflowError/ComponentError/InteractionError taxonomy and the pure-stub WorkflowDispatcher (including its duplicate WorkflowError definition) so there is a single, used exception namespace.
- **Verification signal:** Grep across src/ and tests/ for these symbol names returns no production references; the full test suite passes after deletion.
- **Depends on:** none · **Effort:** S


### 23. Delete dead SessionCoordinator class (`P23`)

- **Location:** `src/branch_fixer/orchestration/coordinator.py`
- **Links to:** F70,F71
- **Change:** Delete coordinator.py. Grep evidence shows SessionCoordinator/coordinate_fix_attempt are referenced only in docs and audit artifacts (docs/developer-guide/04-execution-flow.md, docs/design-and-research/01-strategic-analysis.md, audits/*) and never imported by any module under src/ or tests/ — the orchestrator performs coordination directly, so the no-op stubs (coordinate_fix_attempt=pass, handle_failure=return False) are unreachable dead code. Remove any package re-export if present and update the two doc references to drop the stale class.
- **Verification signal:** Grep across src/ and tests/ for SessionCoordinator/coordinate_fix_attempt/handle_failure(coordinator) returns zero hits; the full test suite passes after deletion.
- **Depends on:** none · **Effort:** S


### 24. Implement update_pr mutation; fix pr_id collisions and modified_files; document deferred PR methods (`P24`)

- **Location:** `src/branch_fixer/services/git/pr_manager.py:43-44,66,114-186`
- **Links to:** F49,F58,F59,F60,F61
- **Change:** (a) update_pr (114): mutate the stored PRDetails — set status, merge metadata, bump updated_at, append a PRChange record — instead of returning it unchanged (F49); update the existing test test_update_pr_returns_existing_pr (tests/unit/git/test_pr_manager.py:152) to assert the mutation. (b) create_pr (43-44,66): store the passed modified_files into PRDetails.modified_files (F61) and replace `pr_id = len(self.prs)+1` with a monotonic self._next_id counter to prevent id reuse after deletion (F60). (c) get_pr_history (155) and close_pr (169): keep them deferred but add an explicit `# Not yet implemented (Phase 4+)` docstring marker (matching the project's documented-deferral convention) and file GitHub issues; existing tests already assert NotImplementedError, so leave that behavior. (d) Document that create_pr is the synchronous fast-path and the management methods are async (F58) rather than churning the async tests.
- **Verification signal:** update_pr returns a PRDetails whose status/metadata reflect the arguments and whose history grew by one PRChange; create_pr stores modified_files into PRDetails.modified_files; deleting a PR then creating a new one yields a fresh non-colliding id; GitHub issues exist for get_pr_history/close_pr.
- **Depends on:** none · **Effort:** M


### 25. Remove misleading empty original_code from CodeChanges (`P25`)

- **Location:** `src/branch_fixer/core/models.py:112-115 + src/branch_fixer/services/ai/manager.py:317`
- **Links to:** F26
- **Change:** Since AIManager always constructs CodeChanges(original_code="", modified_code=...), drop the permanently-empty original_code field (or populate it with the real pre-fix file content if a diff is genuinely needed). Simplest: remove the unused field and update the single construction site.
- **Verification signal:** No code references CodeChanges.original_code as a diff source; manager.py constructs CodeChanges with modified_code only; tests pass.
- **Depends on:** none · **Effort:** S


### 26. Remove redundant inner import and use tz-aware PR timestamps (`P26`)

- **Location:** `src/branch_fixer/services/ai/manager.py:217 + src/branch_fixer/services/git/models.py:87-88`
- **Links to:** F17,F42
- **Change:** Delete the `import re` inside _clean_stack_trace (re is already imported at module level, manager.py:3). Change PRDetails.created_at/updated_at default_factory from datetime.now to a lambda returning datetime.now(timezone.utc) so timestamps are timezone-aware.
- **Verification signal:** manager.py has no function-local `import re`; PRDetails timestamps are tz-aware and comparing them to a tz-aware datetime does not raise TypeError.
- **Depends on:** none · **Effort:** S


### 27. Fix orchestrator per-error temperature, session counts, and FixService reuse (`P27`)

- **Location:** `src/branch_fixer/orchestration/orchestrator.py:248-273,344-356,428-430`
- **Links to:** F50,F51,F62
- **Change:** (F50) Compute get_progress current_temperature from a per-error retry counter, not the global session retry_count. (F51) In run_session, compute failed_tests/passed_tests counts before the early `return False` so the persisted session is not recorded as 0/0 on partial failure. (F62) Construct FixService once per error (or per session) instead of rebuilding it on every retry inside fix_error.
- **Verification signal:** get_progress reports the temperature actually in use for the current error; a session that leaves errors unfixed persists correct failed/passed counts; FixService is instantiated once per error (assert constructor call count).
- **Depends on:** P06 · **Effort:** M


### 28. Rewrite codified-bug tests to assert corrected behavior (`P28`)

- **Location:** `tests/unit/git/test_pr_manager.py:139-148 + tests/unit/config/test_logging_config.py:166-182`
- **Links to:** F11,F12
- **Change:** After P24 and P20, update test_create_pr_accepts_modified_files_and_metadata_without_using_them to assert modified_files DO appear in PRDetails.modified_files (and rename it), and update test_repeated_calls_add_snoop_handler_but_basicconfig_is_noop_for_root to assert the snoop handler count does NOT grow on repeated setup_logging() calls.
- **Verification signal:** Both tests now assert the fixed behavior (modified_files propagated; handler count stable) and pass against the P24/P20 changes.
- **Depends on:** P20, P24 · **Effort:** S


### 29. Fix always-true and broken-raise test assertions (`P29`)

- **Location:** `tests/unit/services/pytest/test_runner.py:470 + tests/unit/orchestration/test_orchestrator.py:583,589`
- **Links to:** F72,F73
- **Change:** (F72) Replace `assert "Duration: 1.23s" or "Duration: 1.2"` with `assert "Duration: 1.23s" in report` (or the intended substring check). (F73) Replace the fallback `raise SimpleNamespace.__class__("CheckpointError")("fail")` (which raises a str) with raising a real BaseException-derived CheckpointError so the checkpoint-error-handling path is actually exercised.
- **Verification signal:** The runner test fails if the duration string is absent from the report; the orchestrator fallback raises a proper exception (not TypeError: exceptions must derive from BaseException) and the intended error-handling branch runs.
- **Depends on:** none · **Effort:** S


### 30. Strengthen weak e2e and fabric-strategy assertions (`P30`)

- **Location:** `tests/integration/test_generator_e2e.py:171-182 + tests/test_generator/test_strategy_fabric.py:231,244`
- **Links to:** F24,F81
- **Change:** (F24) In test_pytest_runs_generated_tests_without_import_error, additionally assert result.returncode == 0 (or that tests passed), not merely the absence of ImportError/ModuleNotFoundError strings. (F81) In test_analysis_uses_analysis_system_prompt, assert the system message equals/contains the imported ANALYSIS_SYSTEM_PROMPT constant rather than the generic words 'analyze'/'plan'.
- **Verification signal:** The e2e test fails if generated tests error with a non-import failure; the fabric test fails if the analysis prompt drifts from ANALYSIS_SYSTEM_PROMPT.
- **Depends on:** none · **Effort:** S


### 31. Restore sys.modules after monkeypatched import in test (`P31`)

- **Location:** `tests/unit/utils/test_run_cli.py:179`
- **Links to:** F25
- **Change:** Replace the bare `sys.modules[...] = types.ModuleType(...)` injection with monkeypatch.setitem (or a try/finally) so the original module is restored after the test, eliminating cross-test sys.modules pollution.
- **Verification signal:** Running this test followed by other tests that import branch_fixer.orchestration.orchestrator shows no import pollution; sys.modules entry is unchanged after the test completes.
- **Depends on:** none · **Effort:** S


### 32. Remove non-coverage test, split misorganized conftest, drop duplicate parser tests (`P32`)

- **Location:** `tests/test_math_operations.py:3-8 + tests/integration/pytest/conftest.py:12-30 + tests/unit/pytest/parsers/test_unified_error_parser.py`
- **Links to:** F65,F79,F10
- **Change:** (F65) Delete tests/test_math_operations.py (defines and tests a local add(); exercises no src/ code). (F79) Split the unit-git fixtures (clean_repo, branch_manager) out of the integration conftest into tests/unit/git/conftest.py and fix the undeclared test_suite_dir dependency for the integration `runner` fixture. (F10) Remove the smaller duplicate tests/unit/pytest/parsers/test_unified_error_parser.py, keeping the comprehensive tests/unit/services/pytest/test_unified_error_parser.py.
- **Verification signal:** Suite passes; only one UnifiedErrorParser test module remains; integration conftest fixtures resolve (no undeclared test_suite_dir) and unit-git fixtures live under tests/unit/git/.
- **Depends on:** none · **Effort:** M


### 33. Run pytest in CI and make security audit gating explicit (`P33`)

- **Location:** `.github/workflows/deploy.yml + .github/workflows/ci.yml:56-57`
- **Links to:** F32,F28
- **Change:** (F32) Add a step that runs the pytest suite before the docs build/deploy in deploy.yml so regressions cannot ship silently. (F28) Either make the pip-audit security job blocking, or keep continue-on-error but reference a tracking GitHub issue/timeline in the comment so non-blocking is an explicit, tracked decision.
- **Verification signal:** deploy.yml workflow contains a pytest invocation gating the deploy; the ci.yml security job either fails the build on CVEs or links a tracking issue.
- **Depends on:** none · **Effort:** S


### 34. Correct API-key env var in user/dev docs (`P34`)

- **Location:** `README.md:52 + docs/developer-guide/04-execution-flow.md:18`
- **Links to:** F20,F54
- **Change:** Replace OPENAI_API_KEY with OPENROUTER_API_KEY in the README .env setup snippet and in the execution-flow click.option envvar example, matching manager.py and CLAUDE.md.
- **Verification signal:** Grep of README.md and execution-flow.md shows OPENROUTER_API_KEY and no OPENAI_API_KEY in the env-setup instructions.
- **Depends on:** none · **Effort:** S


### 35. Fix contributor test-command drift to venv python (`P35`)

- **Location:** `docs/developer-guide/02-contribution-guide.md:54 + CONTRIBUTING.md:39`
- **Links to:** F19,F74
- **Change:** Replace the bare `pytest` instruction with `.venv/bin/python -m pytest` in both contributor docs, per CLAUDE.md's mandate.
- **Verification signal:** Grep of both files shows `.venv/bin/python -m pytest` and no bare-`pytest` run instruction.
- **Depends on:** none · **Effort:** S


### 36. Correct stale design/execution-flow doc references (`P36`)

- **Location:** `docs/design-and-research/01-strategic-analysis.md:49,131 + docs/developer-guide/04-execution-flow.md:118,148-156 + audits/QUALITY_AUDIT.md:46`
- **Links to:** F44,F45,F55,F56,F4
- **Change:** Remove the manager_design_draft.py reference (F44) and fill the '[Current Date]' placeholders (F45) in the strategic analysis; drop the deleted `marvin` backend mention (F55) and correct run_command from async (`asyncio.create_subprocess_exec`) to the actual synchronous implementation (F56) in execution-flow; mark the stale runner.py 'Environment' row in QUALITY_AUDIT.md as resolved (verify_fix already uses sys.executable -m pytest) (F4).
- **Verification signal:** Grep across docs returns no 'manager_design_draft', no '[Current Date]', no 'marvin' backend, and no `async def run_command`; QUALITY_AUDIT.md row 46 is marked resolved.
- **Depends on:** none · **Effort:** S


### 37. Fix stale path comments, src.-prefixed imports, and placeholder artifacts (`P37`)

- **Location:** `tests/unit/core/test_verify_fix_workflow.py:1 + src/branch_fixer/storage/recovery.py:11-14 + src/branch_fixer/storage/state_manager.py:9-10 + scripts/runner_debug.py:1 + pyproject.toml:5 + scripts/setup_project.sh:7 + docs/developer-guide/prompts/Code-Refactoring-Instructions.md:23 + .taskmaster/docs/prd.txt:348-350`
- **Links to:** F21,F41,F57,F75,F76,F77,F22,F80
- **Change:** Correct the wrong module-path header comments (F21, F57). Drop the `src.` prefix from the TYPE_CHECKING imports in recovery.py (F41) and state_manager.py (F80) so they resolve as `branch_fixer.*`. Fill the pyproject.toml description placeholder (F75). Fix or remove scripts/setup_project.sh's wrong skeleton layout and resolve the gitignore-tracking inconsistency (F76). Strip the stray committed LLM-prompt line from Code-Refactoring-Instructions.md (F77). Update PRD Critical Finding #1 which falsely claims CI uses python 3.10 — CI already uses 3.13 (F22).
- **Verification signal:** Header comments match actual file paths; grep for `src.branch_fixer` in recovery.py/state_manager.py imports returns nothing; pyproject description is meaningful; setup_project.sh either matches src/ layout or is removed; the stray prompt line is gone; PRD no longer claims python 3.10.
- **Depends on:** none · **Effort:** M


### 38. Fix reversed() doc example, venv Python version, and coverage runner (`P38`)

- **Location:** `docs/reference/hypothesis-guide.md:162 + Taskfile.yml:29 + scripts/analyze_code.sh:290-295`
- **Links to:** F47,F46,F27
- **Change:** (F47) Fix the `reversed(reversed(xs)) == xs` example so it cannot raise TypeError (e.g. `list(reversed(list(reversed(xs)))) == xs`). (F46) Pin the venv creation to Python 3.13 (e.g. `python3.13 -m venv`) in Taskfile.yml so the wrong interpreter is not selected. (F27) Use `uv run coverage` for the coverage run/report/xml calls to resolve to the project venv like the rest of the script.
- **Verification signal:** The documented roundtrip assertion executes without TypeError; `task setup` creates a Python 3.13 venv; coverage commands resolve to the venv interpreter.
- **Depends on:** none · **Effort:** S


### 39. Clean up inert skip-set, dev-local path, dedup rules, and doc-hygiene artifacts (`P39`)

- **Location:** `src/dev/test_generator/analyze/parser.py:53,152 + scripts/runner_debug.py:23 + .windsurfrules:524 + docs/design-and-research/02-swe-bench-strategy.md:1-185 + docs/aiv-packet-pr9.yaml:35-36,356-358`
- **Links to:** F18,F48,F31,F64,F30
- **Change:** (F18) Remove the inert "property" entry from _SKIP_METHODS, or actually skip @property methods by inspecting node.decorator_list rather than node.name. (F48) Replace the hardcoded macOS volume path in runner_debug.py with a path derived from the repo root, or delete the script. (F31) Deduplicate the triplicated DEV_WORKFLOW/WINDSURF_RULES/SELF_IMPROVE sections in .windsurfrules. (F64) Add a disclaimer or remove the raw AI-transcript swe-bench-strategy.md from the published mkdocs nav. (F30) Record the single-AI author==verifier separation-of-duties limitation explicitly in the AIV packet/process.
- **Verification signal:** Property-decorated methods are correctly skipped (or the dead entry is gone); runner_debug.py runs on any checkout or is removed; .windsurfrules has single copies of each section; the AI-transcript doc carries a disclaimer or is removed from nav.
- **Depends on:** none · **Effort:** M


### 40. Use a single multi-error orchestrator session and implement validate_session_state (`P40`)

- **Location:** `src/branch_fixer/utils/cli.py:210-211 + src/branch_fixer/storage/state_manager.py:142-156`
- **Links to:** F16,F82
- **Change:** (F16) Stop calling orchestrator.start_session([error]) once per error inside _process_all_errors; create a single session for the whole error set so multi-error state tracking and resume semantics are preserved. (F82) Implement validate_session_state for all FixSessionState values (initializing/running/paused/error/failed), not just `completed`, replacing the example-only no-op.
- **Verification signal:** A run over N errors uses one session id (assert start_session called once); validate_session_state returns meaningful results for each state and is covered by tests.
- **Depends on:** none · **Effort:** M


### 41. Add traceback-based fault localization to the AI prompt (`P41`)

- **Location:** `src/branch_fixer/services/ai/manager.py (prompt build) + src/branch_fixer/services/pytest/parsers/failure_parser.py / error_processor.py`
- **Links to:** GOAL:Reach SWE-bench-level autonomous source-code program repair (Pass@1) | research: Agentless/AutoCoderRover/fault-localization-context
- **Change:** Parse the failing pytest traceback to identify the responsible source file(s) and pass that file context into the AIManager prompt, augmenting/replacing the current error_message regex. File-level localization is the highest-ROI APR improvement per the fault-localization-context research; keep it file-level (avoid noisy line-level injection).
- **Verification signal:** For a curated set of seeded bugs, the prompt includes the correct responsible source file in a measurable majority of cases; an A/B harness shows fix success on the sample is no worse and ideally improved versus the regex-only baseline.
- **Depends on:** P16, P18 · **Effort:** L


### 42. Inject exact failing assertion + buggy lines into the capped retry conversation (`P42`)

- **Location:** `src/branch_fixer/services/ai/manager.py (self._messages thread) + orchestrator.fix_error retry loop`
- **Links to:** GOAL:Safe autonomous pytest-failure repair tool | research: ChatRepair conversational repair (<=5 rounds)
- **Change:** On each retry, append the exact failing assertion message and the buggy source lines from the latest verify_fix run into the persistent _messages thread (structured failure injection), and cap the loop at ~5 rounds, matching the empirical diminishing-returns bound.
- **Verification signal:** Inspecting the conversation thread on a retry shows the precise assertion text and buggy lines were injected; the loop terminates at the configured cap (~5); a small-sample harness shows retry quality improves over plain error-text appending.
- **Depends on:** P06 · **Effort:** M


### 43. Multi-candidate patch sampling with test-based selection (`P43`)

- **Location:** `src/branch_fixer/orchestration/orchestrator.py (fix_error loop) + src/branch_fixer/orchestration/fix_service.py`
- **Links to:** GOAL:Reach SWE-bench-level autonomous source-code program repair (Pass@1) | research: Agentless sampling / SWT-Bench ensemble
- **Change:** Replace the single-candidate temperature-bumping retry with sampling N candidate patches per round and selecting the one that makes verify_fix pass (test-based selection), keeping each candidate's apply/verify isolated via the existing backup/subprocess machinery.
- **Verification signal:** The fix loop generates multiple candidates per round and selects by verify_fix exit code; on a benchmark sample, Pass@1 improves versus the single-candidate baseline at a recorded cost-per-fix.
- **Depends on:** P06, P41 · **Effort:** L


### 44. Add BM25 retrieval pre-filter before the LLM call (`P44`)

- **Location:** `new module under src/branch_fixer/services/ai/ (retrieval) + src/branch_fixer/services/ai/manager.py context build`
- **Links to:** GOAL:Reach SWE-bench-level autonomous source-code program repair (Pass@1) | research: SWE-Fixer BM25 coarse-to-fine retrieval
- **Change:** Add a cheap BM25 (or embedding-based) ranking of repository files against the error message to select the most relevant files for the AIManager context, reducing whole-file context injection cost and improving localization. Gate this behind the traceback localization (P41) as the primary signal, with BM25 as a fallback/augmentation.
- **Verification signal:** The retrieval step returns a ranked file list for a given error; measured prompt token volume drops versus whole-file injection while fix success on a sample is maintained or improved.
- **Depends on:** P41 · **Effort:** L

