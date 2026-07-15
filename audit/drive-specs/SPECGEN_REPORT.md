# specgen — drive queue from the audit corpus

Generated 44 specs from **audit/.work/02-findings.json** (88 findings) + **audit/.work/05-plan.json** (44 plan items).
Target repo: `ImmortalDemonGod/Pytest-Error-Fixing-Framework` · base `origin/main` · intent source `audit/02-static-audit.md`.

## Drivability

- **40** drivable now (machine/pytest oracle + code site) — start here.
- **0** need a sharpened `goalCondition` (verification_signal is prose — author a machine check before driving).
- **4** goal/research items (P41–P44 style — draft as `feature-absent` drives, not audit findings).
- Findings coverage: **88/88** covered by a plan item; **0** uncovered (listed in drive-order.json).


## Drive in this order (topological on depends_on, then plan order)

Each row = one `--drive --spec` invocation. ✅ = machine-checkable oracle ready.

| seq | plan | finding | sev | oracle | bug site | depends_on | title |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | P01 | F13 | high | machine ✅ | `scripts/analyze_code.sh:119` | — | P01 (F13): Remove hardcoded CodeScene API toke |
| 2 | P02 | F14 | medium | machine ✅ | `scripts/analyze_code.sh:95-99` | — | P02 (F14): Verify CodeScene CLI installer befo |
| 3 | P03 | F33 | medium | pytest ✅ | `scripts/hypot_test_gen.py:25,239,247,381` | — | P03 (F33): Harden hypot_test_gen subprocess +  |
| 4 | P04 | F53 | low | pytest ✅ | `src/branch_fixer/config/settings.py:6` | — | P04 (F53): Stop silently defaulting SECRET_KEY |
| 5 | P05 | F86 | high | machine ✅ | `src/branch_fixer/utils/cli.py:220-226` | — | P05 (F86): Push branch before creating PR; ret |
| 6 | P06 | F88 | high | pytest ✅ | `src/branch_fixer/orchestration/orchestrator.py:357` | — | P06 (F88): Guard transient API failures inside |
| 7 | P07 | F87 | medium | pytest ✅ | `src/branch_fixer/services/pytest/error_processor.py:49-54` | — | P07 (F87): Short-circuit pytest collection err |
| 8 | P08 | F15 | critical | machine ✅ | `src/branch_fixer/utils/cli.py:519,538-539,552` | P06 | P08 (F15): Track real fix success and return c |
| 9 | P09 | F83 | high | machine ✅ | `src/branch_fixer/storage/recovery.py:135,174,225` | — | P09 (F83): Resolve async/sync mismatch in Reco |
| 10 | P10 | F39 | medium | pytest ✅ | `src/branch_fixer/storage/recovery.py:200-263` | P09 | P10 (F39): Make restore_checkpoint actually re |
| 11 | P11 | F23 | medium | machine ✅ | `src/branch_fixer/utils/cli.py:325,344-348` | — | P11 (F23): Remove dev_force_success bypass and |
| 12 | P12 | F7 | medium | machine ✅ | `src/branch_fixer/services/git/branch_manager.py:169,225` | — | P12 (F7): Implement branch_manager metadata an |
| 13 | P13 | F66 | medium | pytest ✅ | `src/branch_fixer/services/git/repository.py:87-91` | — | P13 (F66): Let _find_git_root resolve repo roo |
| 14 | P14 | F68 | medium | pytest ✅ | `src/branch_fixer/services/git/repository.py:352,590-593` | — | P14 (F68): Implement pull() so sync_with_remot |
| 15 | P15 | F67 | low | machine ✅ | `src/branch_fixer/services/git/repository.py:314,325-335,612` | — | P15 (F67): Align push/merge return semantics w |
| 16 | P16 | F1 | medium | pytest ✅ | `src/branch_fixer/services/pytest/runner.py:218,388-415,173-183` | — | P16 (F1): Fix runner nodeid unpacking and skip |
| 17 | P17 | F3 | low | machine ✅ | `src/branch_fixer/services/pytest/runner.py:59-80` | — | P17 (F3): Remove unconditional collection debu |
| 18 | P18 | F52 | medium | pytest ✅ | `src/branch_fixer/services/pytest/parsers/failure_parser.py:9` | — | P18 (F52): Broaden failure_parser regex to non |
| 19 | P19 | F9 | low | machine ✅ | `src/branch_fixer/services/pytest/models.py:7` | — | P19 (F9): Avoid importing ExitCode from pytest |
| 20 | P20 | F37 | medium | pytest ✅ | `src/branch_fixer/config/logging_config.py:30-37` | — | P20 (F37): Make setup_logging idempotent and c |
| 21 | P21 | F63 | medium | pytest ✅ | `src/branch_fixer/utils/workspace.py:20` | — | P21 (F63): Remove snoop from hard runtime depe |
| 22 | P22 | F5 | medium | machine ✅ | `src/branch_fixer/core/exceptions.py:2-29` | — | P22 (F5): Delete dead exception taxonomy and s |
| 23 | P23 | F70 | high | machine ✅ | `src/branch_fixer/orchestration/coordinator.py` | — | P23 (F70): Delete dead SessionCoordinator clas |
| 24 | P24 | F49 | medium | pytest ✅ | `src/branch_fixer/services/git/pr_manager.py:43-44,66,114-186` | — | P24 (F49): Implement update_pr mutation; fix p |
| 25 | P25 | F26 | low | machine ✅ | `src/branch_fixer/core/models.py:112-115` | — | P25 (F26): Remove misleading empty original_co |
| 26 | P26 | F17 | low | pytest ✅ | `src/branch_fixer/services/ai/manager.py:217` | — | P26 (F17): Remove redundant inner import and u |
| 27 | P27 | F50 | medium | pytest ✅ | `src/branch_fixer/orchestration/orchestrator.py:248-273,344-356,428-430` | P06 | P27 (F50): Fix orchestrator per-error temperat |
| 28 | P28 | F11 | low | pytest ✅ | `tests/unit/git/test_pr_manager.py:139-148` | P20,P24 | P28 (F11): Rewrite codified-bug tests to asser |
| 29 | P29 | F72 | medium | pytest ✅ | `tests/unit/services/pytest/test_runner.py:470` | — | P29 (F72): Fix always-true and broken-raise te |
| 30 | P30 | F24 | low | pytest ✅ | `tests/integration/test_generator_e2e.py:171-182` | — | P30 (F24): Strengthen weak e2e and fabric-stra |
| 31 | P31 | F25 | medium | pytest ✅ | `tests/unit/utils/test_run_cli.py:179` | — | P31 (F25): Restore sys.modules after monkeypat |
| 32 | P32 | F65 | low | pytest ✅ | `tests/test_math_operations.py:3-8` | — | P32 (F65): Remove non-coverage test, split mis |
| 33 | P33 | F32 | medium | pytest ✅ | `.github/workflows/deploy.yml` | — | P33 (F32): Run pytest in CI and make security  |
| 34 | P34 | F20 | medium | machine ✅ | `README.md:52` | — | P34 (F20): Correct API-key env var in user/dev |
| 35 | P35 | F19 | medium | machine ✅ | `docs/developer-guide/02-contribution-guide.md:54` | — | P35 (F19): Fix contributor test-command drift  |
| 36 | P36 | F44 | medium | machine ✅ | `docs/design-and-research/01-strategic-analysis.md:49,131` | — | P36 (F44): Correct stale design/execution-flow |
| 37 | P37 | F21 | medium | machine ✅ | `tests/unit/core/test_verify_fix_workflow.py:1` | — | P37 (F21): Fix stale path comments, src.-prefi |
| 38 | P38 | F47 | medium | pytest ✅ | `docs/reference/hypothesis-guide.md:162` | — | P38 (F47): Fix reversed() doc example, venv Py |
| 39 | P39 | F18 | medium | pytest ✅ | `src/dev/test_generator/analyze/parser.py:53,152` | — | P39 (F18): Clean up inert skip-set, dev-local  |
| 40 | P40 | F16 | low | pytest ✅ | `src/branch_fixer/utils/cli.py:210-211` | — | P40 (F16): Use a single multi-error orchestrat |
| 41 | P41 | P41 | n/a | prose | `src/branch_fixer/services/ai/manager.py (prompt build)` | P16,P18 | P41 (P41): Add traceback-based fault localizat |
| 42 | P42 | P42 | n/a | prose | `src/branch_fixer/services/ai/manager.py (self._messages thread)` | P06 | P42 (P42): Inject exact failing assertion + bu |
| 43 | P43 | P43 | n/a | prose | `src/branch_fixer/orchestration/orchestrator.py (fix_error loop)` | P06,P41 | P43 (P43): Multi-candidate patch sampling with |
| 44 | P44 | P44 | n/a | prose | `new module under src/branch_fixer/services/ai/ (retrieval)` | P41 | P44 (P44): Add BM25 retrieval pre-filter befor |

## Run one

```bash
node orchestration/src/fix_pipeline.mjs --drive --spec audit/drive-specs/spec_P01_F13.json --cwd <worktree>
```

Pre-flight first: `fix_pipeline.mjs --selftest` then `--dry-run`. For a batch, feed `queue.jsonl` to `drive_supervisor.sh` per row, honoring the depends_on order above.

## Regenerate this queue

```bash
node orchestration/src/specgen_from_audit.mjs \
  --findings audit/.work/02-findings.json --plan audit/.work/05-plan.json --audit-md audit/02-static-audit.md \
  --oracles audit/drive-specs/oracles.json --repo ImmortalDemonGod/Pytest-Error-Fixing-Framework --base origin/main --tag pef --out audit/drive-specs
```

