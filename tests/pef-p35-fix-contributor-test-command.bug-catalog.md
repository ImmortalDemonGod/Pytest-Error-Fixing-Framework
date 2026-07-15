# Bug catalog — pef-p35-fix-contributor-test-command (F19, F74)

This change is a pure Markdown text substitution (no executable code, no new branch/function/class),
so there is no runtime-behavior surface to catalog. Per the plan (§9, "Design-tests commitment"), this
file records the doc-drift defects the RED test below catches instead of code bugs.

- **F19 — bare `pytest` in contribution guide.**
  `docs/developer-guide/02-contribution-guide.md:55` instructs contributors to run `pytest` (bare, no
  interpreter path) inside the "Run the Full Test Suite" step. CLAUDE.md ("Python Environment") mandates
  `.venv/bin/python -m pytest` and explicitly says "Never use system python3." A contributor who copies
  the guide's command runs whatever `pytest` resolves to on `PATH` — potentially a mismatched system
  Python — instead of the project's Python 3.13 `.venv`.
  - Wrong (current): `pytest`
  - Correct (required): `.venv/bin/python -m pytest`

- **F74 — bare `pytest` in CONTRIBUTING.md.**
  `CONTRIBUTING.md:39` instructs contributors, under "Run the tests", to run `pytest` (bare). Same
  CLAUDE.md mandate as F19 applies: the venv-qualified invocation is required so tests run against
  Python 3.13 and the project's installed dependencies, not whatever `pytest` happens to be on `PATH`.
  - Wrong (current): `pytest`
  - Correct (required): `.venv/bin/python -m pytest`
