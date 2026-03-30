# Documentation Issues & Feature Status

Audit conducted 2026-03-30. Critical user-guide fixes already applied.

---

## Project Feature Status

This project has TWO intended features, only ONE of which is implemented:

### Feature 1: Test Fixing — IMPLEMENTED
Entry point: `.venv/bin/python -m branch_fixer.main fix`
Code lives in: `src/branch_fixer/`

### Feature 2: Test Generation — SCAFFOLD ONLY, NOT IMPLEMENTED
Entry point: `src/dev/cli/generate.py` — empty file
Code lives in: `src/dev/test_generator/` — every single file is 0 bytes

The full intended architecture for test generation:
- `src/dev/test_generator/analyze/parser.py` — parse source to find untested functions
- `src/dev/test_generator/analyze/extractor.py` — extract function signatures/docstrings
- `src/dev/test_generator/generate/strategies/hypothesis.py` — property-based test generation
- `src/dev/test_generator/generate/strategies/pynguin.py` — automated test synthesis
- `src/dev/test_generator/generate/strategies/fabric.py` — LLM-based test generation
- `src/dev/test_generator/generate/templates.py` — test templates
- `src/dev/test_generator/generate/optimizer.py` — deduplicate/optimize generated tests
- `src/dev/test_generator/output/formatter.py` — format output
- `src/dev/test_generator/output/writer.py` — write to disk
- `src/dev/shared/` — shared git, logging, testing utilities (also empty)

---

## What Each Doc Is Actually For

### User Guide — operational docs for Feature 1 (fix)
- `01-installation.md` — setup. Fixed.
- `02-quickstart.md` — example run. Fixed.
- `03-cli-reference.md` — CLI options for `fix` command. Fixed.

### Developer Guide — architecture and process docs
- `01-architecture.md` — accurate reference for Feature 1's layer design
- `02-contribution-guide.md` — PR/linting workflow. Minor issue: says `pytest` not `.venv/bin/python -m pytest`
- `03-testing-strategy.md` — SPLIT: first half (philosophy, layer descriptions) is valid; second half (lines 68–317) is pre-implementation pseudocode for Feature 1 that was never cleaned up. Imports/classes all wrong.
- `04-execution-flow.md` — call chain walkthrough for Feature 1. Mostly accurate, a few stale code snippets.

### Developer Guide / prompts — design specs for Feature 2 (generate)
These are the intended prompts that `src/dev/test_generator/generate/strategies/fabric.py` would use once implemented. Not wired to anything yet.
- `pytest-generation.md` — system prompt for LLM-based test generation
- `test-refactoring.md` — prompt for consolidating/improving generated tests
- `Structured-Test-Development-Process.md` — pre-analysis checklist before generating tests
- `Code-Refactoring-Instructions.md` — refactoring types reference; also relevant to test improvement step

### Design and Research — strategic vision for both features
- `01-strategic-analysis.md` — full outside-in assessment of the project. Covers both features, their purpose, and fit within the "Cultivation" ecosystem. One stale reference: mentions deleted `manager_design_draft.py`.
- `02-swe-bench-strategy.md` — raw AI conversation about using Feature 1 against the SWE-bench benchmark. Not a structured document but contains real strategic ideas.
- `03-git-api-design.md` — raw AI conversation about git operation gaps. Relevant backlog for `src/dev/shared/git.py` once Feature 2 is built.

### Reference — background knowledge that informed the design
- `ddd-principles.md` — explains why `src/branch_fixer/` is organized the way it is (aggregates, value objects, etc.)
- `debugging-workflow.md` — systematic debugging methodology that shaped how Feature 1 approaches error analysis
- `bug-taxonomy.md` — defect classification background; relevant to how Feature 2 would categorize what kinds of tests to generate
- `hypothesis-guide.md` — practical guide for the Hypothesis strategy in `src/dev/test_generator/generate/strategies/hypothesis.py` once it's implemented
- `target-audience.md` — user persona analysis (Alex the engineer, Maria the tech lead, Ren the researcher)

---

## Remaining Accuracy Issues

### High
- `developer-guide/03-testing-strategy.md` lines 68–317: planning pseudocode with wrong imports, wrong class names, wrong field names. Delete or replace with real examples.
- `developer-guide/04-execution-flow.md`: `envvar='OPENAI_API_KEY'` in code snippet (wrong), mentions `marvin` (deleted), shows `async run_command` (actually sync).

### Medium
- `design-and-research/01-strategic-analysis.md`: references deleted `manager_design_draft.py`.
- `reference/target-audience.md` line 60: wrong command `python -m src.branch_fixer.main fix`.
- `developer-guide/02-contribution-guide.md`: says `pytest` not `.venv/bin/python -m pytest`.

### Minor
- `reference/ddd-principles.md`: mentions `GenerationStrategy` — doesn't exist in code yet (would be part of Feature 2).
- `developer-guide/prompts/test-refactoring.md`: says "ready-to-run with `python -m unittest`" — project uses pytest.
- `reference/hypothesis-guide.md`: `reversed(reversed(xs)) == xs` in example fails — `reversed()` returns an iterator.
