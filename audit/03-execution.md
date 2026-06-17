# 03 — Execution / Dynamic Surface

_Tests ran: **true**. Passed 883, failed 1, skipped 0, errors 25, coverage 93%. Independent verification: coverage_confirmed=**true**._

> **⚠️ Re-execution addendum (proof-of-attempt pass) — see [`03-execution-addendum.md`](03-execution-addendum.md).** The "un-executed accounting" below was re-opened under a strict standard (install deps, stub only the boundary, drive real logic, capture I/O). Un-executed **code** regions dropped **14 → 2** (both with proof-of-attempt). The 25 git-test errors (commit-signing) and 11 deselected integration tests now pass; the AI manager, end-to-end fix (flipped a real test False→True), PR creation, and git branch logic were all driven directly with their network/auth boundaries stubbed.

## Summary

Environment set up with Python 3.13.12 venv; all deps installed via uv. Test suite ran: 883 passed, 1 failed, 25 errors, 11 deselected. 25 errors in tests/unit/git/test_repository.py are sandbox-environment artifacts (git commit signing enforced globally via /tmp/code-sign; signing server returns HTTP 400). 1 failure in test_workspace_validator.py is also environment-caused (chmod 0o000 does not restrict root). Integration tests deselected by pytest.ini. Branch coverage 93% across 2184 statements. All 4 CLI entrypoints launched cleanly (exit 0). Key Stage-2 findings confirmed by direct code inspection: async/sync mismatch (F83) means recovery checkpointing silently no-ops; PR creation before push (F86) would cause gh pr create to fail on unborn remote branches; success_count never incremented (F15) means fix-rate reporting is always 0; double FixServiceError wrapping (F38/F88); multiple NotImplementedError stubs (F7, F8, F59, F68) block production use of their features. 35 of 88 findings confirmed by reading source; 6 refined with more precise evidence; remainder untested due to scope or credentials.

## Environment setup (discovered from the repo)

- ✓ Discover Python versions (`python3 --version && python3.13 --version`) — python3 = 3.11.15 (system); python3.13 = 3.13.12 available. Project requires >=3.13 per pyproject.toml.
- ✓ Create Python 3.13 venv (`python3.13 -m venv .venv`) — .venv/bin/python == Python 3.13.12
- ✓ Upgrade pip inside venv (`.venv/bin/python -m pip install --upgrade pip`) — pip upgraded to 26.1.2
- ✓ Install uv inside venv (`.venv/bin/python -m pip install uv`) — uv 0.11.21 installed
- ✓ Install project + dev deps via uv (editable) (`.venv/bin/python -m uv pip install -e '.[dev]'`) — All deps resolved; litellm, pytest-cov, hypothesis, ruff, mypy, etc. installed
- ✓ Install hypothesis[cli] and black for integration tests (`.venv/bin/python -m pip install 'hypothesis[cli]' black`) — black 26.5.1, pytokens 0.4.1 installed

## Test result

883 passed, 1 failed, 11 deselected (integration marker excluded by pytest.ini addopts), 25 errors. 25 errors are ALL in tests/unit/git/test_repository.py — the shared git_repo fixture calls 'git commit -m init' which fails with exit code 128 because the sandbox enforces GPG commit signing via /tmp/code-sign, and the signing server returns HTTP 400. This is a sandbox environment constraint, not a code bug. 1 failure: tests/unit/utils/test_workspace_validator.py::test_validate_workspace_dir_not_accessible — chmod 0o000 on a tmp dir does not restrict access when running as root; test expects PermissionError that is never raised. Overall coverage 93% across 2184 statements with 478 branches.

## Entry points exercised

| Command | Exit | Observation |
| --- | --- | --- |
| `.venv/bin/python -m branch_fixer.main --help` | 0 | CLI loads cleanly. Shows two subcommands: fix and generate. No import errors. |
| `.venv/bin/python -m branch_fixer.main --version` | 0 | Outputs: 'pytest-fixer, version 0.1.0'. Version matches pyproject.toml. |
| `.venv/bin/python -m branch_fixer.main fix --help` | 0 | Shows --api-key (required, maps to OPENROUTER_API_KEY env), --max-retries, --initial-temp, --temp-increment, --non-interactive, --fast-run, --test-path, --test-function, --cleanup-only, --dev-force-success. Confirms F20  |
| `.venv/bin/python -m branch_fixer.main generate --help` | 0 | Shows --source-path (required), --output-dir (default: generated_tests), --strategy (default: hypothesis). CLI registered correctly. |
| `.venv/bin/python scripts/hypot_test_gen.py --help` | 1 | No --help flag; script parses argv[1] as file path. Prints usage: 'python test_generator.py <path_to_python_file>'. snoop.install() executed at import time creating snoop_debug.log in cwd (confirms F36). |

## Stage-2 findings — execution delta

| Finding | Status | Evidence |
| --- | --- | --- |
| F1 | confirmed | runner.py:218 reads 'file_path, test_name = test_id.split("::", 1)'. No guard for missing '::'; a test_id without '::' causes ValueError: not enough values to unpack. |
| F2 | confirmed | runner.py:383-415 _handle_outcome_logic: result.passed is set True when call_outcome=='skipped' (line 391), but result.skipped is never set True anywhere in the method. TestResult.skipped stays False for @pytest.mark.ski |
| F3 | confirmed | runner.py:61 has active 'print(f"  - {item.nodeid}")' statement (line 59 comment references a commented-out print; line 61 is NOT commented). Observed in test runs: this fires for every collected item. |
| F4 | untested | audits/QUALITY_AUDIT.md not read; could not verify doc drift claim against actual verify_fix behavior. |
| F5 | confirmed | grep -rn 'from branch_fixer.core.exceptions import' src/ returns no results. core/exceptions.py defines FixError, CoordinationError, WorkflowError, ComponentError, InteractionError — none imported anywhere in production  |
| F6 | confirmed | dispatcher.py:5 defines 'class WorkflowError(Exception): pass' independently. core/exceptions.py:14 defines 'class WorkflowError(FixError): pass'. No inheritance link. Dispatcher's WorkflowError is a separate class. |
| F7 | confirmed | branch_manager.py:169 is 'raise NotImplementedError()' with no condition. Any call to get_branch_metadata() raises unconditionally. |
| F8 | confirmed | branch_manager.py:225 is 'raise NotImplementedError()' with no condition. Any call to is_branch_merged() raises unconditionally. |
| F9 | untested | Did not read services/pytest/models.py to verify the _pytest.main import; coverage shows models.py at 100% coverage so tests do run it successfully with the current pytest version. |
| F10 | untested | Did not verify the two test files for UnifiedErrorParser; not required for execution audit. |
| F11 | untested | Did not read test_pr_manager.py:139-148 in detail. |
| F12 | untested | Did not read test_logging_config.py:166-182 in detail. |
| F13 | confirmed | scripts/analyze_code.sh:119 contains literal: export CS_ACCESS_TOKEN="<REDACTED-CodeScene-token-see-scripts/analyze_code.sh:119>". Read directly from file. |
| F14 | confirmed | scripts/analyze_code.sh installs CodeScene CLI via curl pipe to sh. Pattern confirmed by reading the script; not executed (destructive-skip). |
| F15 | confirmed | cli.py:519 initializes success_count=0. Lines 521-539 loop over errors but never increment success_count. Comment at line 538 says 'you can increment success_count here' but it is not done. Returns (total_processed, 0) a |
| F16 | confirmed | cli.py:210-211: _generate_and_apply_fix calls self.orchestrator.start_session([error]) then self.orchestrator.fix_error(error) on each call. Called from _process_non_interactive_error for every error individually, so a n |
| F17 | confirmed | manager.py:217 has 'import re' inside _clean_stack_trace body. manager.py:3 already has 'import re' at module level. Redundant but harmless (Python caches module imports). |
| F18 | untested | Did not read parser.py:53 in detail to verify _SKIP_METHODS frozenset content. |
| F19 | untested | Did not read docs/developer-guide/02-contribution-guide.md. |
| F20 | confirmed | fix --help shows '--api-key TEXT ... OPENROUTER_API_KEY env var'. Confirmed OPENROUTER_API_KEY is the real env var (also in CLAUDE.md). README.md check not performed directly but CLAUDE.md states README says OPENAI_API_K |
| F21 | untested | Did not read tests/unit/core/test_verify_fix_workflow.py header. |
| F22 | confirmed | ci.yml:19 uses python-version: '3.13'. PRD claim that CI specifies 3.10 is wrong — the PRD is outdated. Finding as stated (PRD doc drift) is valid. |
| F23 | confirmed | cli.py:325: dev_force_success=config.dev_force_success is passed to FixService. Read at cli.py:317-327. |
| F24 | untested | Integration tests deselected by pytest.ini addopts; test_generator_e2e.py:171-182 not executed. |
| F25 | untested | Did not read tests/unit/utils/test_run_cli.py:179 in detail. |
| F26 | untested | Did not read core/models.py:112-115 CodeChanges in detail. |
| F27 | untested | Did not read scripts/analyze_code.sh:290 coverage run section; not executed. |
| F28 | confirmed | ci.yml:57: 'continue-on-error: true' on the security job. pip-audit findings are non-blocking. Read directly from .github/workflows/ci.yml. |
| F29 | confirmed | cli.py:347: interactive=not config.dev_force_success. When dev_force_success=True, interactive=False. This repurposes a debug flag as an interactivity toggle. |
| F30 | untested | Did not read docs/aiv-packet-pr9.yaml. |
| F31 | untested | Did not read .windsurfrules. |
| F32 | untested | Did not read .github/workflows/deploy.yml. |
| F33 | confirmed | hypot_test_gen.py:247: subprocess.run(full_cmd, shell=True, ...) where full_cmd includes user-provided 'command' string. shell=True confirmed from reading. |
| F34 | confirmed | hypot_test_gen.py:239: full_cmd = f'hypothesis write {command}' uses bare 'hypothesis' binary name. CLAUDE.md mandates using Path(sys.executable).parent / 'hypothesis'. The venv-local hypothesis binary is not used here. |
| F35 | confirmed | hypot_test_gen.py:381: 'if attempt < 3' is hardcoded. try_generate_test at line 312 accepts max_retries=3 as default, so they coincidentally match, but handle_failed_attempt would misreport for any other max_retries valu |
| F36 | confirmed | hypot_test_gen.py:25: snoop.install(out=Path('snoop_debug.log')) executes at module import time. Verified by running the script — snoop_debug.log was created in cwd on import. |
| F37 | confirmed | logging_config.py:31-37: snoop_logger.addHandler(snoop_handler) is called without checking snoop_logger.handlers. With force=True on basicConfig (line 23), root logger handlers are replaced but snoop logger accumulates a |
| F38 | confirmed | fix_service.py:140-143: inner except catches any exception and raises FixServiceError. fix_service.py:165-167: outer except re-catches that FixServiceError and wraps it in a new FixServiceError with root_cause extraction |
| F39 | confirmed | recovery.py:210-212: 'for fpath in rp.modified_files: pass'. Loop body is pure pass. Docstring says it restores files but implementation is a no-op placeholder. |
| F40 | confirmed | recovery.py:244,250,258,263 all use print() for diagnostic output instead of the logging module used everywhere else in the codebase. |
| F41 | untested | Did not read recovery.py:11-14 TYPE_CHECKING block in full detail. |
| F42 | confirmed | pr_manager.py:109: created_at=datetime.now() produces a naive datetime. The PRDetails dataclass field at models.py:87-88 uses field(default_factory=datetime.now). No timezone info attached. |
| F43 | confirmed | main.py:12 calls setup_logging() before cli(). run_cli.py:94 calls setup_logging() again inside the fix() Click command. With force=True on basicConfig, root handlers are replaced; snoop FileHandler accumulates (see F37) |
| F44 | untested | Did not read docs/design-and-research/01-strategic-analysis.md:49. |
| F45 | untested | Did not read docs/design-and-research/01-strategic-analysis.md:131. |
| F46 | confirmed | Taskfile.yml:29: 'python3 -m venv {{.PYTHON_VENV}}' uses bare python3. On this system python3 resolves to 3.11.15, not 3.13. Using bare python3 in 'task setup' would create a 3.11 venv, violating pyproject.toml requires- |
| F47 | untested | Did not read docs/reference/hypothesis-guide.md:162. |
| F48 | untested | Did not read scripts/runner_debug.py:23 to verify hardcoded path. |
| F49 | confirmed | pr_manager.py:136-138: update_pr checks 'if pr_id not in self.prs: raise PRUpdateError'. Then returns self.prs[pr_id] unchanged. status, metadata, reason params are declared but not used in the body. |
| F50 | confirmed | orchestrator.py:428-429: current_temperature = self.initial_temp + self.temp_increment * self._session.retry_count. FixSession.retry_count is defined as 'retry_count: int = 0' (line 55 area). get_progress() correctly acc |
| F51 | confirmed | orchestrator.py:248-254: when _handle_error_fix returns False, method immediately saves session and returns False (line 254). The failed_tests/passed_tests update at lines 257-262 is bypassed. session.failed_tests stays  |
| F52 | confirmed | failure_parser.py:9: PATTERNS = [r'([\w\/\._-]+):(\d+):\s+([\w\.]+Error)']. The third capture group requires the exception class name to contain 'Error'. AssertionError, KeyboardInterrupt, StopIteration, NotImplementedEr |
| F53 | confirmed | settings.py:6: SECRET_KEY = os.environ.get('BRANCH_FIXER_SECRET_KEY', ''). Empty string default. Read directly. |
| F54 | untested | Did not read docs/developer-guide/04-execution-flow.md:18. |
| F55 | untested | Did not read docs/developer-guide/04-execution-flow.md:118. |
| F56 | untested | Did not read docs/developer-guide/04-execution-flow.md:148-156. |
| F57 | untested | Did not read scripts/runner_debug.py:1 header. |
| F58 | confirmed | pr_manager.py:41: create_pr is 'def create_pr(...)' (sync). pr_manager.py:114: update_pr is 'async def update_pr(...)'. pr_manager.py:140: validate_pr is 'async def'. pr_manager.py:155: get_pr_history is 'async def'. pr_ |
| F59 | confirmed | pr_manager.py:167: 'raise NotImplementedError()' in get_pr_history. pr_manager.py:186: 'raise NotImplementedError()' in close_pr. Both confirmed by reading. |
| F60 | confirmed | pr_manager.py:66: 'pr_id = len(self.prs) + 1'. If PR with id 1 is deleted, next creation also produces id 1, causing collision. |
| F61 | confirmed | pr_manager.py:41-111: create_pr declares modified_files: List[Path] as required param (line 45). Searching body: modified_files is never read or used inside create_pr. The gh pr create command at lines 71-86 does not pas |
| F62 | confirmed | orchestrator.py:344-356: fix_service = FixService(...) is constructed inside the retry loop in fix_error(). For max_retries=3, up to 3 separate FixService instances are created with fresh AI manager, test runner, change  |
| F63 | confirmed | workspace.py:20: REQUIRED_DEPENDENCIES includes 'snoop'. check_dependencies() at line 104 uses importlib.import_module per dep; raises ImportError if snoop not installed. Since snoop is in pyproject.toml dependencies, it |
| F64 | untested | Did not read docs/design-and-research/02-swe-bench-strategy.md. |
| F65 | untested | Did not read tests/test_math_operations.py. |
| F66 | confirmed | repository.py:87-88: checks '(root / ".git").exists()' on the exact root path before calling Repo(..., search_parent_directories=True). If cwd is a subdirectory of a git repo, the .git check fails and raises NotAGitRepos |
| F67 | refined | repository.py:323: run_command(['push', 'origin', push_branch]) raises GitError on non-zero exit (via _check_command_error at line 150). The except Exception at line 333 catches it and returns False. Therefore lines 328- |
| F68 | confirmed | repository.py:590: self.pull() raises NotImplementedError (line 352: 'raise NotImplementedError("pull method is not implemented yet.")'). sync_with_remote at line 593 catches GitError only, not NotImplementedError. The N |
| F69 | refined | repository.py:612: 'return result.returncode == 0' is executed only when run_command() does NOT raise (i.e., returncode==0), so this always returns True when reached. No try-except in merge_branch, so GitError propagates |
| F70 | confirmed | coordinator.py:19-31: coordinate_fix_attempt body is '# Implement coordination logic here\n        pass'. Method is async, returns None always. |
| F71 | confirmed | coordinator.py:46-47: '# Implement failure handling logic here\n        return False'. handle_failure always returns False regardless of context. |
| F72 | confirmed | test_runner.py:470: 'assert "Duration: 1.23s" or "Duration: 1.2"' — Python evaluates right-hand side as the string "Duration: 1.23s" (truthy), so assert always passes. The assertion never actually checks the report outpu |
| F73 | confirmed | test_orchestrator.py:583 creates exception via SimpleNamespace.__class__("CheckpointError")("fail"). SimpleNamespace.__class__ is type; type("CheckpointError") with one arg returns type of that arg = str; str("fail") = " |
| F74 | untested | Did not read CONTRIBUTING.md:39. |
| F75 | confirmed | pyproject.toml:5: description = "Add your description here". Confirmed by reading the file. Placeholder never filled. |
| F76 | untested | Did not read scripts/setup_project.sh. |
| F77 | untested | Did not read docs/developer-guide/prompts/Code-Refactoring-Instructions.md. |
| F78 | confirmed | repository.py:314-335: push() docstring says 'Raises: GitError: If the push operation fails' but implementation wraps all exceptions in 'except Exception: logger.error(); return False'. GitError is never raised from push |
| F79 | untested | Did not read tests/integration/pytest/conftest.py. |
| F80 | untested | Did not read storage/state_manager.py:9 TYPE_CHECKING block. |
| F81 | untested | Did not read tests/test_generator/test_strategy_fabric.py:231. |
| F82 | untested | Did not read storage/state_manager.py:142 validate_session_state in detail. |
| F83 | confirmed | recovery.py:135,174,225: create_checkpoint, restore_checkpoint, handle_failure are all 'async def'. orchestrator.py:393 calls 'self.recovery_manager.handle_failure(error, self._session, context)' without await — returns  |
| F84 | confirmed | pr_manager.py:41-48: create_pr() is annotated '-> PRDetails' and returns a PRDetails instance. repository.py:544-571: create_pull_request_sync() is annotated '-> bool' but calls self.pr_manager.create_pr() and returns th |
| F85 | confirmed | orchestrator.py:351: 'dev_force_success=False, # Placeholder for logic'. This hardcodes False regardless of any config or CLI flag passed to the orchestrator. |
| F86 | confirmed | cli.py:219-226: create_pull_request_sync (which internally calls 'gh pr create --head branch_name' at pr_manager.py:71-82) is called at line 220 BEFORE push(branch_name) at line 226. The branch may not exist on the remot |
| F87 | untested | Did not read error_processor.py:49-54 and change_applier.py:127-128 in combination. |
| F88 | confirmed | fix_service.py:140-143: inner except catches any Exception and raises FixServiceError(str(e)). fix_service.py:165-167: outer except catches that FixServiceError and re-raises as FixServiceError(str(root_cause)) where roo |

## Un-executed accounting (every region carries a reason)

- `src/branch_fixer/services/ai/manager.py: generate_fix(), _analyze_error(), _call_ai() — all AI API call paths` — **requires-credentials**
- `src/branch_fixer/main.py + run_cli.py: task run:fix and run:fix-test full execution (fix command with real OPENROUTER_API_KEY)` — **requires-credentials**
- `scripts/analyze_code.sh:95-99 CodeScene CLI install via curl | sh` — **destructive-skip**
- `scripts/analyze_code.sh: full CodeScene analysis (requires CodeScene API token and license)` — **external-service**
- `task docs:deploy — mkdocs gh-deploy` — **external-service**
- `CI jobs: lint, typecheck, security, test, integration, build-and-deploy` — **external-service**
- `tests/integration/test_generator_e2e.py (11 deselected by pytest.ini '-m not integration')` — **other**
- `tests/unit/git/test_repository.py (25 errors — git_repo fixture requires git commit which fails due to sandbox GPG signing enforcement)` — **other**
- `src/branch_fixer/services/git/repository.py: sync_with_remote, pull, commit — NotImplementedError stubs` — **dead**
- `src/branch_fixer/orchestration/coordinator.py: coordinate_fix_attempt, handle_failure — pass/return False stubs` — **dead**
- `src/branch_fixer/orchestration/dispatcher.py: dispatch_fix_workflow, handle_component_error — pass stubs` — **dead**
- `src/branch_fixer/services/git/branch_manager.py: get_branch_metadata, is_branch_merged — NotImplementedError stubs` — **dead**
- `src/branch_fixer/services/git/pr_manager.py: get_pr_history, close_pr — NotImplementedError stubs` — **dead**
- `scripts/runner_debug.py — hardcoded absolute macOS path /Volumes/Totallynotaharddrive/...; not runnable in this Linux environment` — **other**

## Independent verification

coverage_confirmed: **true** — Re-read the saved artifacts under audit/.work/ and reproduced key claims independently. (a) test_run.log and test_run2.log both end with the identical pytest summary line: '1 failed, 883 passed, 11 deselected, 25 errors' — exactly matching the report's test_result (passed=883, failed=1, skipped=0, errors=25). Both logs' TOTAL coverage line reads '2184 statements, 478 branches, 93%', matching coverage_pct=93. The saved coverage.xml independently corroborates: lines-valid=2184, branches-valid=478, line-rate=0.94, branch-rate=0.8975 — the pytest-cov combined statement+branch TOTAL of 93% is consistent with these (the 0.94 XML line-rate is pure line coverage; pytest-cov's 93% folds in branch coverage). (b) Un-executed reasons verified as legitimate: counted exactly 25 'ERROR tests/unit/git/test_repository.py' lines in the log; their root cause in the traceback is 'subprocess.CalledProcessError: Command [git commit -m init] returned non-zero exit status 128'. I reproduced this directly in a throwaway repo — git commit fails because commit.gpgsign=true and the sandbox signing server (/tmp/code-sign -> /opt/env-runner/environment-manager) returns HTTP status 400. This is a genuine environment constraint, not an avoidable test gap or a code bug, exactly as the report claims. Credential-gated AI paths, external-service CI/CodeScene/mkdocs, integration-marker deselection (11), and NotImplementedError/pass dead stubs are all legitimate, non-avoidable un-executed reasons. (c) Spot-checked 3 entry points myself: '.venv/bin/python -m branch_fixer.main --version' -> 'pytest-fixer, version 0.1.0' rc=0; '--help' rc=0; 'generate --help' rc=0 — all matching the reported exit_code 0 observations. No material discrepancies between the report's self-reported numbers and the real artifacts.

**Discrepancies the verifier found:**
- Minor (non-material): coverage.xml records a pure line-rate of 0.94 (94%) while the report and pytest-cov TOTAL state 93%. This is not a contradiction — the 93% is pytest-cov's combined statement+branch metric (branch-rate 0.8975 drags the combined figure below the pure 94% line rate). Worth noting only because a reader comparing the XML line-rate alone to the headline number could perceive a 1-point mismatch. (audit/.work/coverage.xml:line line-rate="0.94" vs audit/.work/test_run2.log TOTAL '93%' and 03-exec-raw.json:46)
