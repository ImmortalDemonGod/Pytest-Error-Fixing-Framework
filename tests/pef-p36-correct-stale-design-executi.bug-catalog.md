# Bug catalog — F44 doc-drift bundle (F44, F45, F55, F56, F4)

Covers the GOAL condition from `audit/05-plan.md:376`: "Grep across docs returns no
`manager_design_draft`, no `[Current Date]`, no `marvin` backend, and no `async def run_command`;
`QUALITY_AUDIT.md` row 46 is marked resolved." Each bullet below names the symptom, the exact
`file:line`, and the wrong-vs-correct behavior the accompanying RED test asserts against.

- **BUG-1 — stale `manager_design_draft.py`/`marvin` reference (F44).**
  `docs/design-and-research/01-strategic-analysis.md:48`. Wrong: prose states, present tense, "A
  `manager_design_draft.py` shows forward-thinking exploration of more advanced, tool-using agents
  with `marvin`" — but `CLAUDE.md` ("One AI Manager") and `find src -iname manager_design_draft.py`
  (zero hits) both confirm the file was deleted, not a currently-existing module. Correct: the
  sentence is reframed past-tense as historical record (per plan D2) so the literal substrings
  `manager_design_draft` and `marvin` no longer appear anywhere in the sentence.

- **BUG-2 — three unfilled `[Current Date]` placeholders (F45).**
  `docs/design-and-research/01-strategic-analysis.md:131,273,383`. Wrong: three
  `**Analysis Date:** [Current Date]` header lines were never filled in — `git log -S'[Current
  Date]'` shows all three were introduced in commit `23f2743` (2025-07-28) and never resolved.
  Correct: all three occurrences are replaced with the literal recovered date `2025-07-28` (plan
  D1), not left as a placeholder and not three independently-guessed dates.

- **BUG-3 — stale `marvin` backend mention (F55).**
  `docs/developer-guide/04-execution-flow.md:118`. Wrong: "Generate code changes via an LLM call
  (`litellm` or `marvin` or whichever backend)" implies `marvin` is still a live option; `marvin` is
  not imported anywhere under `src/` (`grep -rn "import marvin\|from marvin" src/` → 0 hits).
  Correct: the sentence is reframed past-tense ("explored `marvin` early on but it was not
  adopted") so the literal substring `marvin` no longer appears.

- **BUG-4 — `run_command` shown as `async def` when the real implementation is synchronous (F56).**
  `docs/developer-guide/04-execution-flow.md:149,152-156`. Wrong: the doc's code sample reads
  `async def run_command(self, cmd: List[str]) -> CommandResult:` with `await
  asyncio.create_subprocess_exec(...)`, and the preceding sentence says it "spawns an async
  subprocess for Git". The real implementation
  (`src/branch_fixer/services/git/repository.py:130-159`) is `def run_command(self, cmd:
  List[str]) -> CommandResult:` — plain synchronous code calling `_prepare_git_command` →
  `_execute_subprocess` → `_check_command_error`, no `asyncio`/`await` anywhere. Correct: the code
  sample and prose match the real synchronous signature verbatim; the literal substring `async def
  run_command` no longer appears.

- **BUG-5 — `QUALITY_AUDIT.md` rows 46 and 60 not marked resolved (F4 + F44's own audit record).**
  `audits/QUALITY_AUDIT.md:46` (the `pytest/runner.py`/Environment row, F4's canonical target —
  claims `verify_fix()` "shells out to the `pytest` executable, which may not match the active
  interpreter/venv", but `src/branch_fixer/services/pytest/runner.py:449-450` already invokes
  `sys.executable, '-m', 'pytest'`, so the row is itself stale) and `audits/QUALITY_AUDIT.md:60`
  (the `services/ai/manager_design_draft.py`/Maintainability row, F44's own audit record). Wrong:
  neither row's Recommendation cell contains a resolved/closed/done marker today. Correct: both
  rows carry a grep-able `resolved|closed|done` marker in their Recommendation cell (plan D6 — both
  rows, not just one, since they close two distinct findings, F4 and F44's audit-record).
