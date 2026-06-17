# 03 — Execution Addendum: Proof-of-Attempt Re-Execution Pass

_Re-opens Stage 3's un-executed accounting under a strict standard: every region previously
marked un-executed / skipped / reasoned-away was **re-attempted** by installing deps and
stubbing only the **boundary** (network / auth / SDK) while driving the **real logic**, with
captured I/O. A region may remain un-executed only with a failed command + attempted stub
attached. Done in an ephemeral sandbox (full perms, internet) where nothing persists._

**Environment:** Python 3.13.12 venv (survived Stage 3); all deps + Hypothesis CLI present.
**Harnesses (committed):** `audit/.work/exec/{h1_ai_and_stubs,h2_e2e_and_pr,h2b_pr,h3_git}.py`.
Raw logs in `audit/.work/exec/*.log` (gitignored; key I/O excerpted below).

## Regions that FLIPPED un-executed → executed

| Region (prior class) | Boundary stubbed / method | Captured result (real logic ran) |
|---|---|---|
| **AI manager** `generate_fix`/`_analyze_error`/`_parse_response`/`_clean_stack_trace` (requires-credentials) | dummy key `sk-DUMMY…`; stub `manager.completion` | `generate_fix` → parsed `CodeChanges(modified_code="def test_add():\n    assert 2 + 2 == 4")`. `completion` called at **temp 0.1 (analyze) → 0.4 (fix) → 0.6 (retry-with-feedback)**, thread grew 3→5. Real analyze/prompt/parse/thread logic executed. (Bonus finding: returned `original_code` is empty.) |
| **End-to-end fix pipeline** (requires-credentials CLI) | stub AI fix → **real** `ChangeApplier` → **real** `verify_fix` subprocess | `verify_fix` BEFORE=`False` → `apply_changes_with_backup` success=`True` (backup written to `.backups/`) → `verify_fix` AFTER=`True`. **Real test flipped False→True.** AST assert-guard **rejected** an assertion-deleting fix (success=`False`, backup restored). |
| **PR creation** `pr_manager.create_pr` (requires-credentials/external) | stub `shutil.which('gh')` + `subprocess.run` | → `PRDetails(id=1, status=PRStatus.OPEN, branch=fix-demo-abc123)`; built `gh pr create --title … --head fix-demo-abc123`. Confirms **F86** (no push before create) and **F61** (`modified_files` never reaches the `gh` argv). |
| **Git branch create/cleanup** `branch_manager` (external-service) | real git in a temp repo | `create_fix_branch`→`True`, `branch_exists`→`True`, `cleanup_fix_branch`→`True`. |
| **25 git tests** `tests/unit/git/test_repository.py` (sandbox commit-signing) | `git config --global commit.gpgsign false` | **rc=0, 26 passed** (previously 25 errors). |
| **Integration tests** `test_generator_e2e.py` (deselected) | `pytest -m integration` | **rc=0, 11 passed.** |
| **CI: ruff check / ruff format / mypy** (external-service) | run locally | rc=0 each — clean / 72 files formatted / 43 files no issues. |
| **CI: pip-audit** (external-service) | run locally | rc=0 — no vulns (only the local editable pkg is not on PyPI). |
| **CI: docstr-coverage** (external-service) | install + run | rc=0 — **82.1% ≥ 80**, grade "Very good". |
| **CI: mkdocs build** (build-and-deploy external-service) | run locally | rc=0 — built in 0.51s. |
| **Feature 2 test generation** `generate` CLI + `hypot_test_gen.py` (untested) | run for real | `generate` rc=0 → produced `test_ErrorInfo_default.py` (1 generated / 9 skipped); script rc=0. |
| **`repository.{clone,commit,pull,sync_with_remote}`**, **`branch_manager.{get_branch_metadata,is_branch_merged}`**, **`pr_manager.{get_pr_history,close_pr}`** (dead) | called directly | All raise `NotImplementedError` — **reachable live stubs**, not unreachable dead code. (`sync_with_remote` raises via `pull` → confirms F68; `close_pr` requires `(pr_id, status)` then raises.) |
| **`coordinator.*`, `dispatcher.*`** (dead) | called directly (async) | `coordinate_fix_attempt`→`None`, `handle_failure`→`False`, `dispatch_fix_workflow`→`None`, `handle_component_error`→`None` — confirms F70/F71/F6 silent no-ops. |
| **`scripts/runner_debug.py`** (“not runnable on Linux”) | run | **rc=0** — executed and returned a `SessionResult`; the prior "hardcoded macOS path" reason is contradicted. |

## Regions still un-executed — WITH proof-of-attempt (2)

1. **CodeScene CLI install + analysis** (`scripts/analyze_code.sh:90-119`).
   - Attempt: `curl -sSf https://downloads.codescene.io/enterprise/cli/install-codescene-cli.sh | sh`
   - Captured failure: `curl: (22) The requested URL returned error: 403`. The enterprise install endpoint is **access-controlled**, so `cs` cannot be installed without enterprise credentials; analysis additionally needs a license token.
   - Class: **hard blocker** — access-gated commercial external service. (`F13` token / `F14` curl-pipe-to-sh remain valid static findings regardless.)

2. **Real outward `git push` / `mkdocs gh-deploy`** (CLI `fix --non-interactive` `_create_and_push_pr` at `cli.py:226`; `task docs:deploy`).
   - All **local** logic executed: PR-build (above), branch create (above), `mkdocs build` rc=0. The only uncrossed step is the literal `git push` / gh-pages push to the **real `origin` remote**.
   - **Deliberately not triggered:** pushing throwaway fix branches or overwriting gh-pages on the real remote is an outward side effect outside the audit's mandate (deliverables-only, no source promoted). Constituent logic proven by decomposition.
   - Class: **outward side effect against a real remote** — intentionally not performed.

> Note on the full CLI `fix --non-interactive` wrapper: not run as a single command **because its non-interactive path performs a real `git push` to `origin`**. Every real code path it invokes was instead driven directly (AI generation, change apply+verify, branch create, PR build), and its arg-wiring is covered by `--help` (rc=0) and the unit tests. This is stricter than a single end-to-end invocation, not weaker.

## Not execution regions (clarification)
The Stage-2 deltas still marked "untested" (e.g. F4, F9–F12, F19, F21, F30–F32, F41, F44–F48, F54–F57, F64, F74, F76–F77, F79–F82) are **documentation-drift / static claims** ("does doc X say Y?"), not executable code paths — verified by reading, not running. They are out of scope for *execution* accounting and remain valid static findings in `02-static-audit.md`.

## Net result
Un-executed **code** regions: **14 → 2**, both with proof-of-attempt. Every previously credential-/dependency-/external-service-gated *logic* path was driven directly with only its boundary stubbed, capturing real inputs, outputs, and errors.
