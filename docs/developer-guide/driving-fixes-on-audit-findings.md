# Driving the Fix Pipeline on Audit Findings

_How to take the forensic-audit corpus (`audit/`) and actually get its findings
repaired — what works today, what produces "verification theater," and what to
build. Every claim here is grounded in source; file:line references included._

---

## TL;DR

The audit corpus already hands you an **execution-ready remediation plan**
(`audit/.work/05-plan.json`): 44 items, each carrying `location` (diff target),
`change` (the edit), `verification_signal` (acceptance test), and `depends_on`
(ordering DAG). But **nothing executes it** — the AIV forensic pipeline stops at
Stage 5 by design (`"This PR records the audit; it does not fix any findings."`).

You cannot naively "point the fixer at the findings," because there are **three
shape mismatches** between the corpus and the `branch_fixer` fix pipeline:

| # | Mismatch | Consequence |
|---|---|---|
| 1 | **Input**: the pipeline consumes a *failing pytest test*; findings have no test node | Must materialize each finding as a failing test first |
| 2 | **Edit target**: the pipeline edits **only `error.test_file`**; 56/88 findings are *source* bugs | It literally cannot write a source fix — driving it produces test-rewriting theater |
| 3 | **Executor**: the audit pipeline plans but never applies; the fixer is the closest executor but wrong-shaped | The "Stage 6" that drives fixes does not exist yet |

Three real paths follow (§3). **Recommended: Path B** — build the missing
Stage-6 executor that consumes `05-plan.json` directly, gated by AIV's
anti-cheat validator so it can't cheat.

---

## 1. What each side actually is

### 1a. The audit corpus (what you have)

Produced by the forensic-audit pipeline (`audit/.work/orchestrator.mjs`, a
sibling of `aiv-protocol`'s `forensic_pipeline.mjs`). Two machine-readable
artifacts matter:

**`audit/.work/02-findings.json`** — 88 findings. Schema per finding (exactly 6
fields):

```
id, location (file:line), class, severity, evidence (prose), intent_mismatch (bool)
```

- Severity: **1 critical / 5 high / 34 medium / 48 low**.
- Class: bug 31, design_defect 25, doc_drift 17, test_gap 8, security 4, other 2, performance 1.
- **There is no `verification_signal`, `test_node`, or `repro` field on a
  finding.** Repro info lives only inside `evidence` prose (which does name exact
  symbols + line numbers). `intent_mismatch: true` (35/88) is a cheap pre-filter
  for "code does the wrong thing."

**`audit/.work/05-plan.json`** — 44 remediation items (`P01`–`P44`). Schema (9
fields):

```
id, title, links_to, location, change, verification_signal, depends_on[], order, effort (S|M|L)
```

- `verification_signal` is present on **all 44** and **is** the acceptance
  criterion — but it is *prose*, e.g. P08:
  _"A run that successfully fixes >=1 error returns exit code 0 and prints the
  true success count; a run that fixes none returns non-zero."_
- `links_to` back-references finding IDs (`"F33,F34,F35,F36"`); for P41–P44 it's
  a `GOAL:…` string instead.

The AIV pipeline **stops here** — 5 stages (understanding → static-audit →
execution → goal → plan), `main()` returns after Stage 5. Invariant 5 in both
orchestrators: _"mutation is a means, not a deliverable; the only shipped output
is the audit docs."_ Applying fixes is explicitly left to a human or a separate
tool. **That separate tool is what §3 is about.**

### 1b. The fix pipeline (what would consume them)

Entry: `branch_fixer.main fix --non-interactive --test-path <path>`.

```
run_cli.fix                              # utils/run_cli.py:127,166,186
  └─ test_runner.run_test(test_path)     #   runs pytest → SessionResult
  └─ process_pytest_results(result)      #   SessionResult → List[TestError]   (error_processor.py:18)
  └─ cli.process_errors(errors)          #   drive the fixer
       └─ orchestrator.fix_error(error)  #   retry loop, temperature bump       (orchestrator.py:322)
            └─ FixService.attempt_fix     #   generate → apply → verify          (fix_service.py:83)
```

Two facts about this path are decisive for your question:

1. **The only input is a failing pytest test.** `process_pytest_results` builds
   `TestError`s *exclusively* from a pytest `SessionResult` (`error_processor.py:18-57`).
   A `TestError` is `{test_file, test_function, error_details}`. There is no
   constructor for "a static finding."

2. **The pipeline edits only the test file.** `generate_fix` reads
   `error.test_file.read_text()` as the code to fix, prompts the model
   _"Fix this failing test … Provide the complete fixed file"_
   (`manager.py:144,153,261-275`), and `apply_changes_with_backup(error.test_file,
   changes)` overwrites **that same file** (`fix_service.py:129`,
   `change_applier.py:96`). **The source-under-test is never read and never
   edited.**

Safety rails: backup/restore + `compile()` syntax check + an **AST guard** that
rejects a fix only if the test's assert count drops from `>0` to **exactly 0**
(`change_applier.py:199`). Note the shallowness — weakening `assert x == 5` to
`assert x is not None` sails through.

Also relevant: the pipeline **cannot currently report which findings it fixed** —
`success_count` is initialized to 0 and never incremented (`cli.py:519,538`), and
`process_errors` returns success only when `success_count == total_processed`
(`cli.py:509`), true only when *nothing* was processed. That is finding **F15**,
the single critical, and it means any driver must track success itself until P08
lands.

---

## 2. The three shape mismatches, in detail

**Mismatch 1 — Input.** A finding is `{location, class, severity, evidence}`.
The pipeline needs `{test_file, test_function, error_details}` from a *live
pytest run*. Bridge: author (or generate) a failing test that encodes the
finding, then run it so the pipeline discovers it. The plan's
`verification_signal` is the spec for that test — but it's prose, so this is a
codegen/authoring step, not a lookup.

**Mismatch 2 — Edit target (the important one).** 56 of 88 findings are
code-resident (`bug` + `design_defect`), living in `src/branch_fixer/**`, not in
tests. The pipeline writes to `error.test_file`. So if you materialize F15 as
`tests/…/test_exit_code.py` and drive the fixer, the model — shown only the test
file, told to "return the complete fixed file" — will **rewrite the test to pass**
rather than fix `cli.py`. If it weakens the assertion (keeping ≥1 assert to clear
the AST guard), `verify_fix` goes green and the finding is reported "fixed" while
the bug remains. **That is exactly the verification theater / "Hallucination
Cascade" the AIV audit exists to catch.** The pipeline is structurally incapable
of fixing a source bug; only test-resident defects are in its native reach.

**Mismatch 3 — Executor gap.** The audit pipeline is deliberately audit-only.
The `branch_fixer` fix pipeline is the nearest thing to an executor, but per
Mismatch 2 it is the wrong shape for 56/88 findings. So "drive the fix pipeline
on the findings" is really "supply the missing Stage 6," one of three ways.

---

## 3. Three paths to actually drive fixes

### Path A — Drive the *existing* pipeline on the subset it can natively reach

**Scope: small and honest.** Only defects whose *root cause is in a test file*.
The corpus hands you six ready-made ones: existing tests that currently **pass
while asserting wrong behavior** — invert the assertion and they fail without you
authoring anything:

| Finding | The wrong-asserting test |
|---|---|
| F12 | `test_repeated_calls_add_snoop_handler_but_basicconfig_is_noop_for_root` (asserts `len(after) == len(before)+1`) |
| F11, F72, F24, F73, F81 | see `evidence` in `02-findings.json` |

**Procedure:**
1. Invert the assertion so the test encodes *correct* behavior → it now fails.
2. `fix --non-interactive --test-path <that test file>`.
3. Manually confirm the fix is real (the model may have re-weakened the test).

**Limit:** works only when the fix genuinely belongs in the test. The moment the
root cause is in `src/`, this path degenerates into Mismatch 2. Expect ~6–8
items, not 44. Do **not** use this for the bug/design_defect findings.

### Path B — Build the missing Stage-6 executor (RECOMMENDED)

Don't bend the test-fixer into something it isn't. Build the symmetric "apply"
loop the audit pipeline stops short of — it already shows you how, via `runAgent`
(`forensic_pipeline.mjs`): spawn `claude -p --output-format json
--permission-mode acceptEdits` with a schema output-contract and validate/retry.
Do the same, but for *applying* a plan item:

```
for item in topo_sort(load("05-plan.json"), key=depends_on, then order):
    finding = findings[item.links_to]           # pull evidence for context
    agent = claude -p --permission-mode acceptEdits \
        --prompt: "Apply this remediation. Edit SOURCE at {item.location}.
                   Change: {item.change}
                   Evidence of the defect: {finding.evidence}
                   Do NOT modify tests to pass. Add/adjust a regression test that
                   encodes: {item.verification_signal}"
    # 1. agent edits src/ (and adds a regression test)
    # 2. VERIFY: turn verification_signal into a real check and run it:
    #      - pytest-shaped signal  -> run the named/added test, require green
    #      - grep-shaped  (P01)    -> run the grep, require zero hits
    #      - e2e/manual   (P05)    -> run the e2e harness
    # 3. HONESTY GATE: run the diff through aiv ValidationPipeline (see §4).
    #      If it modified a test without Class-F justification -> reject, retry.
    # 4. commit 1 file per commit (CLAUDE.md rule) + one AIV packet per fix.
```

**Why this is the right shape:** it edits *source*, it consumes the plan the
audit already made execution-ready, its acceptance test comes straight from
`verification_signal`, and `depends_on` gives you safe ordering (e.g. P08
depends_on P06; P10 depends_on P09).

**Scope:** the ~17–18 code-resident plan items —
`P05, P06, P07, P08, P09, P10, P11, P12, P13, P14, P15, P16, P18, P20, P24, P27, P40`
— **plus** the non-code items the test-fixer could never touch but a general
agent can (security `P01–P04`, docs `P34–P38`), because their
`verification_signal` is grep/observation-based, not a pytest node.

### Path C — Upgrade the fixer into a real APR tool

Make the fixer *able* to edit source, then Path A generalizes. This is not
speculative — **it is the audit's own Band 9** (`05-plan.md`, items P41–P44):

| Item | Capability it adds | Why it unblocks driving-on-findings |
|---|---|---|
| P41 | Traceback fault localization | Find the *source* line to edit, not just the test |
| P44 | BM25 retrieval over the repo | Put the relevant *source* files in the model's context |
| P43 | Multi-candidate sampling | APR-style patch search instead of single-shot |
| P42 | Structured failure injection | Systematize finding → failing-test |

Plus two core edits outside Band 9: (a) let `generate_fix`/`apply` target a
source path, not `error.test_file`; (b) fix F15 so success is tracked. This is
the largest lift but turns the fixer into a genuine automated-program-repair
engine you *can* aim at the whole corpus.

---

## 4. The honesty gate — where this rejoins AIV

Whichever path you drive, the failure mode is identical: an agent makes the
*acceptance check* pass without fixing the defect (weaken the assertion, delete
the test, stub the function). The fixer's own defense — the assert-count AST
guard — is shallow (§1b). AIV already ships the real defense:
`aiv.lib.validators.pipeline.ValidationPipeline` (`aiv-protocol`), Stages 7–8:

- **Stage 7 Anti-Cheat** — scans the diff for test manipulation.
- **Stage 8 Cross-Reference** — any test modification **requires an Evidence
  Class F claim with a `Justification:`**, else it blocks with `E011`
  (`pipeline.py:143-162`).

So the clean architecture is a closed loop that uses both systems for what each
is good at:

```
AIV forensic pipeline  →  05-plan.json  →  Stage-6 executor (Path B)  →  fix diff
        ↑ audits                                                            │
        └──────────────  AIV ValidationPipeline (anti-cheat) gates ────────┘
```

Skip the gate and you rebuild, by hand, the exact Hallucination Cascade the AIV
project was created to expose.

---

## 5. Worked example — the critical finding, end-to-end (Path B)

**F15 → P08.** Finding evidence: `success_count` never incremented
(`cli.py:519,538`); exit code always wrong (`cli.py:509`).

```
Plan item P08 (05-plan.json):
  location:            src/branch_fixer/utils/cli.py:519,538-539,552
  change:              "Increment success_count when a verified fix succeeds;
                        process_errors returns 0 when >=1 fix succeeded; fix the
                        summary line to report the actual count."
  verification_signal: "A run that fixes >=1 error returns exit 0 and prints the
                        true count; a run that fixes none returns non-zero."
  depends_on:          [P06]        # guard transient API failures first
```

Executor steps:
1. **Order check** — P06 must be applied first (`depends_on`).
2. **Materialize the acceptance test** from `verification_signal`:
   `tests/unit/utils/test_process_errors_exit_code.py` — one case fixes ≥1 error
   (expect exit 0, summary count == fixes), one fixes none (expect non-zero). It
   fails against current `cli.py`.
3. **Agent applies to SOURCE** — `_process_all_errors` returns a real
   `success_count`; `process_errors` returns `0 if success_count > 0`.
4. **Verify** — run the new test; require green.
5. **Honesty gate** — diff touches `cli.py` (source) + a *new* test → AIV
   anti-cheat passes (no *existing* test weakened).
6. **Commit** — `cli.py` and the test file as **separate commits** (1-file rule);
   attach an AIV packet citing the test as Class-A evidence.

---

## 6. Recommended immediate sequence

1. **Fix F15/P08 by hand first** (it's the critical, and every driver needs
   honest success accounting). This also validates the Path-B recipe on one item.
2. **Prototype the Stage-6 executor** (Path B) against the P05–P16 cluster —
   highest-severity, all code-resident, mostly independent.
3. **Wire the AIV anti-cheat gate** (§4) before running unattended.
4. **Reserve Path A** for the ~6 test-resident items (F11/F12/F72/F24/F73/F81).
5. **Treat Path C (P41–P44) as the roadmap** to eventually aim the fixer itself
   at the corpus rather than a bespoke executor.

---

## Appendix — drivable subsets

- **Cleanly test-expressible source findings (~29):**
  F1, F2, F7, F8, F15, F16, F23, F29, F37, F38, F39, F42, F43, F49, F50, F51,
  F52, F60, F61, F62, F66, F68, F82, F83, F84, F85, F86, F87, F88
- **Code-resident plan items (Path B core, ~17–18):**
  P05–P16, P18, P20, P24, P27, P40 (P26 partial)
- **Test-resident (Path A, ~6):** F11, F12, F72, F24, F73, F81
- **Not pipeline-shaped (~42 findings):** security secrets, CI/build config, doc
  drift, dead-code deletion, dependency hygiene — for an agent (Path B), not the
  test-fixer.

_Sources: `src/branch_fixer/**` (fix pipeline), `audit/.work/{02-findings,05-plan}.json`
(corpus), `aiv-protocol/src/aiv/lib/validators/pipeline.py` (honesty gate),
`aiv-protocol/docs/audits/2026-06-18-forensic/pipeline/forensic_pipeline.mjs.md`
(the audit-only boundary)._
