# Driving the fix pipeline on this repo's audit findings

_How to take the forensic-audit corpus in `audit/` and drive each finding to a
verified PR through the **AIV fix pipeline** (`aiv-workflow/orchestration/src/fix_pipeline.mjs`).
Every claim here is grounded in source; file references included._

> **Correction:** an earlier version of this doc analysed the in-repo Python
> `branch_fixer` tool as "the fix pipeline." That was wrong. `branch_fixer`
> repairs *failing pytest tests*; it only edits `error.test_file` and cannot
> touch the source-level defects the audit found. **The fix pipeline that drives
> a finding to a PR is the `.mjs` harness in `aiv-workflow`.** This doc is about
> that.

---

## Two systems

| | Where | Role |
|---|---|---|
| **Audit corpus** | `audit/` (this repo) | 88 findings (`02-findings.json`) + a 44-item remediation plan (`05-plan.json`), produced by a forensic-audit pipeline. The **input**. |
| **Fix pipeline** | `aiv-workflow/orchestration/src/fix_pipeline.mjs` | A deterministic harness that drives **one finding → merged PR** through 14 gated stages. The **engine**. |
| **Spec generator** | `aiv-workflow/orchestration/src/specgen_from_audit.mjs` | Joins the two: turns `02`+`05` into ready-to-drive specs. The **bridge**. |

## The pipeline (14 stages, two human touchpoints)

`fix_pipeline.mjs` drives `H1 → H2`: **H1** is the finding (already done — it's in
`02-static-audit.md`); **H2** is you, judging the evidence and merging. Everything
between is fresh isolated `claude -p` subagents calling the aiv-workflow skills,
each transition gated on a schema-valid machine verdict, HALTing fail-closed:

```
launch-brief → plan → check-drift(gate#1) → start-pr → ground → design-tests →
write-code(+aiv-packet/commit) → prove-it(SEAM gate) → push → CI →
or-review + aiv-audit(gate#2) → poll-ci loop → terminator → H2 judge → merge
```

Two properties make this safe to run unattended, and are why it — not
`branch_fixer` — is the right engine for source-level findings:
- **Separation of duties:** the review entity sees the PR + spec + evidence, never
  the implementer's reasoning. A weak driver can only fail-closed, never false-pass.
- **The `goalCondition` oracle:** an approach-agnostic, machine-checkable outcome
  decides "fixed" — not a test the agent could weaken.

Refutation is first-class: if a drive finds the finding isn't real, it writes
`REFUTED_<id>.md`, exits 5, and owes a correction back to the audit source.

## The bridge: from an 02 finding to a spec

`fix_pipeline.mjs` consumes a per-finding **spec** (`--drive --spec <f.json>`).
Its `intentSource` defaults to `audit/02-static-audit.md` and Class-E intent is
stamped at the finding's line — the 02 file is the pipeline's *native* input.
Each spec maps straight off the corpus:

| spec field | source |
|---|---|
| `intentSource` / `intentLine` | `audit/02-static-audit.md` + the finding's row line (Class-E anchor) |
| `bugSite` | the finding's `location` |
| `goalCondition` | the plan item's `verification_signal` — **sharpened** into a machine oracle (see below) |
| `depends_on` | the plan item's `depends_on` → drive order |

The generator builds these:

```bash
node ../aiv-workflow/orchestration/src/specgen_from_audit.mjs \
  --findings audit/.work/02-findings.json --plan audit/.work/05-plan.json \
  --audit-md audit/02-static-audit.md --oracles audit/drive-specs/oracles.json \
  --repo ImmortalDemonGod/Pytest-Error-Fixing-Framework --base origin/main \
  --tag pef --out audit/drive-specs
```

### The oracle gap (the one piece that isn't mechanical)

An 02 finding has `{location, class, severity, evidence}` — **no machine oracle.**
The 05-plan's `verification_signal` is the acceptance criterion, but ~14 of them
are prose, not a runnable check. `audit/drive-specs/oracles.json` supplies
hand-authored, **approach-agnostic OUTCOME** oracles for those (exit-code /
assert / count — never a fix-*mechanism* grep, which oscillates the review gate
per `fix_pipeline.mjs` `isMechanismGrep`/#191). With them, the queue is:

- **40 drivable now** (machine/pytest oracle at a code site)
- **4 goal/research items** (P41–P44 — draft as `feature-absent` drives)
- **88/88 findings covered**, no dependency cycles

## The drive queue

`audit/drive-specs/` holds the committed, regenerable queue:

- `oracles.json` — the 14 hand-authored oracles (the only authored artifact)
- `queue.jsonl` — harness-native rows `{finding_id, repo, location, goal_condition, depends_on, …}`
- `drive-order.json` — topological order (depends_on then plan order) + drivability flags
- `SPECGEN_REPORT.md` — human-facing table + the regenerate command
- `spec_*.json` — the per-finding specs (gitignored; regenerate on demand)

## Running it

```bash
# 0. from aiv-workflow/orchestration:
node src/fix_pipeline.mjs --selftest      # gates/validators (0 failed is the gate)
node src/fix_pipeline.mjs --dry-run       # full 14-stage flow, zero-API
node src/fix_pipeline.mjs --preflight     # one cheap real claude -p (proves auth)

# 1. one finding (worktree of THIS repo):
node src/fix_pipeline.mjs --drive --spec <repo>/audit/drive-specs/spec_P08_F15.json --cwd <worktree>

# 2. the batch: drive drive-order.json in sequence, honoring depends_on,
#    via src/drive_supervisor.sh <spec> <log> (self-detaching, auto-resuming).
```

### Environment requirements (read before a real drive)

A live drive needs three things this sandbox does **not** all have:
- `claude -p` — **present** here (preflight OK; defaults to haiku-4.5). ✓
- git push — **works** here. ✓
- `gh` — **absent** here, and the pipeline uses it for the PR/CI/merge back-half
  (`fix_pipeline.mjs` `gh pr view/edit`). ✗

So in this sandbox a drive can run the **front-half** (finding → plan → tests →
code → prove-it → pushed fix branch) but **cannot open/poll/merge PRs**. A full
finding→merged-PR campaign needs a `gh`-enabled environment (with `GIT_TOKEN`),
or the OpenRouter/local driver shim (`drivers/`) plus `gh`. A drive also needs the
target's env provisioned (`.venv` + deps) so the design-tests/prove-it stages can
run the suite.

## Why not `branch_fixer` for this?

`branch_fixer` is shown only `error.test_file` and prompted "provide the complete
fixed file," which overwrites that test file (`services/ai/manager.py:153`,
`services/code/change_applier.py:96`). Pointed at a source-level finding's repro
test, it would rewrite the *test* to pass — the verification theater the AIV
system exists to catch. `fix_pipeline.mjs` edits source, gates on an external
oracle, and enforces separation of duties. Use `branch_fixer` for genuinely
test-resident defects; use the AIV fix pipeline for the audit findings.
