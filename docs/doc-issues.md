# Documentation Issues & Feature Status

Audit conducted 2026-03-30. Critical user-guide fixes already applied.

---

## Project Feature Status

This project has TWO features. Both exist, but in different states of integration.

### Feature 1: Test Fixing — FULLY INTEGRATED
Entry point: `.venv/bin/python -m branch_fixer.main fix`
Code: `src/branch_fixer/` — full DDD architecture, wired to CLI, tests exist

### Feature 2: Test Generation — WORKING SCRIPT, NOT YET INTEGRATED
The actual implementation lives in `scripts/hypot_test_gen.py` — it is real,
working code. The `src/dev/test_generator/` directory is empty scaffolding
created afterwards to receive a cleaned-up version of this script.

**What `scripts/hypot_test_gen.py` actually does:**
- Parses a Python source file with AST (`ModuleParser`) to discover all
  public classes, methods, and functions (`TestableEntity`)
- Calls `hypothesis write <module.path.Entity>` for each entity to auto-generate
  property-based tests
- Applies smart variant selection based on method name patterns:
  - `encode`/`decode` → roundtrip tests
  - `transform`/`convert` → idempotent tests
  - `validate`/`verify` → errors-equivalent tests
  - `add`/`multiply` → binary-op tests
- Post-processes output with an AST transformer (`TestFixer`) that fixes duplicate
  `self` parameters that `hypothesis write` sometimes emits
- Writes generated tests to `generated_tests/` directory
- Entry point: `python scripts/hypot_test_gen.py <path/to/source.py>`

**What `src/dev/test_generator/` is:**
Empty placeholder files for the planned refactored/integrated version:
- `analyze/parser.py` ← will replace `ModuleParser` in hypot_test_gen.py
- `analyze/extractor.py` ← will replace `get_module_contents`
- `generate/strategies/hypothesis.py` ← will replace `TestGenerator.run_hypothesis_write`
- `generate/strategies/pynguin.py` ← planned alternative: Pynguin automated test synthesis
- `generate/strategies/fabric.py` ← planned LLM-based generation (uses prompts/ templates)
- `generate/templates.py` ← planned for LLM prompt templates
- `generate/optimizer.py` ← planned deduplication/optimization pass
- `output/formatter.py`, `output/writer.py` ← planned to replace direct file writes
- `cli/generate.py` ← planned CLI entry point (currently no `generate` subcommand)

**What the `docs/developer-guide/prompts/` folder is for:**
These are the AI prompt templates intended for `strategies/fabric.py` (LLM-based
generation strategy), which is not yet implemented:
- `pytest-generation.md` — system prompt for generating tests from a function
- `test-refactoring.md` — prompt for consolidating/improving generated tests
- `Structured-Test-Development-Process.md` — pre-analysis checklist before generation
- `Code-Refactoring-Instructions.md` — refactoring reference baked into the refactor prompt

**What `scripts/analyze_code.sh` is:**
The developer workflow tool that ties everything together today (before the CLI
integration exists):
1. Runs CodeScene (code complexity/health analysis) on a source file
2. Runs Mypy (type checking)
3. Runs Ruff (linting + formatting, auto-fix)
4. Detects if a test file exists and runs coverage
5. If coverage < 100%, auto-activates test mode
6. Appends the appropriate AI prompt (test generation or refactoring) to the analysis
7. Copies the full combined report to clipboard — ready to paste into an AI assistant

So the current workflow is: `analyze_code.sh file.py` → clipboard → paste into AI →
AI writes tests or refactors → developer reviews. The `src/dev/` scaffold is meant
to automate this loop inside the CLI as a `generate` subcommand.

---

## What Each Doc Is Actually For (Corrected)

### User Guide — operational docs for Feature 1 (fix)
- `01-installation.md` — setup. Fixed in this audit.
- `02-quickstart.md` — example run of `fix`. Fixed in this audit.
- `03-cli-reference.md` — CLI options for `fix`. Fixed in this audit.
  Note: missing documentation of the planned `generate` subcommand entirely.

### Developer Guide
- `01-architecture.md` — accurate reference for Feature 1's layer design
- `02-contribution-guide.md` — PR/linting workflow. Says `pytest` not `.venv/bin/python -m pytest`
- `03-testing-strategy.md` — SPLIT: first half (philosophy, layer descriptions) valid;
  second half (lines 68–317) is pre-implementation pseudocode for Feature 1, never cleaned up
- `04-execution-flow.md` — call chain for Feature 1. Mostly accurate, a few stale snippets

### Developer Guide / prompts — AI prompt templates for Feature 2's LLM strategy
Intended for `strategies/fabric.py`. Currently used manually via `analyze_code.sh`.

### Design and Research
- `01-strategic-analysis.md` — full assessment of both features and their strategic context.
  References deleted `manager_design_draft.py`.
- `02-swe-bench-strategy.md` — raw AI conversation about using Feature 1 against SWE-bench
- `03-git-api-design.md` — raw AI conversation; backlog for `src/dev/shared/git.py`

### Reference
- `ddd-principles.md` — explains Feature 1's architecture choices
- `debugging-workflow.md` — systematic debugging methodology behind Feature 1's design
- `bug-taxonomy.md` — defect classification background for Feature 2's test targeting
- `hypothesis-guide.md` — practical guide for Feature 2's `strategies/hypothesis.py`
- `target-audience.md` — user persona analysis. Wrong command at line 60.

---

## Remaining Accuracy Issues

### High
- `developer-guide/03-testing-strategy.md` lines 68–317: planning pseudocode with
  wrong imports (`src.domain.models`), wrong class names, wrong field names.
- `developer-guide/04-execution-flow.md`: `envvar='OPENAI_API_KEY'` (wrong),
  mentions `marvin` (deleted), shows `async run_command` (actually sync).

### Medium
- `design-and-research/01-strategic-analysis.md`: references deleted `manager_design_draft.py`
- `reference/target-audience.md` line 60: wrong command `python -m src.branch_fixer.main fix`
- `developer-guide/02-contribution-guide.md`: says `pytest` not `.venv/bin/python -m pytest`
- No documentation anywhere for Feature 2's current entry point (`scripts/hypot_test_gen.py`)
  or the developer workflow (`scripts/analyze_code.sh`)

### Minor
- `reference/ddd-principles.md`: mentions `GenerationStrategy` — doesn't exist yet
- `developer-guide/prompts/test-refactoring.md`: says "ready-to-run with `python -m unittest`"
- `reference/hypothesis-guide.md`: `reversed(reversed(xs)) == xs` fails (iterator, not list)
