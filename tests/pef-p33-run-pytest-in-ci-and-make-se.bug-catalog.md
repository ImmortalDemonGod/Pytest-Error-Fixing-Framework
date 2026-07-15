# Bug catalog — pef-p33-run-pytest-in-ci-and-make-se (F32, F28)

- **F32 — docs deploy ships with no test gate.** `.github/workflows/deploy.yml:8-28`, job
  `build-and-deploy`. The job's `steps:` list goes straight from "Install dependencies" (`pip install
  -e ".[dev]"`) to "Build MkDocs site" (`mkdocs build --clean`) to the GitHub Pages deploy step — no
  step anywhere invokes `pytest`. Wrong: a broken/regressed test suite has zero effect on whether
  `deploy.yml` builds and publishes the docs site to GitHub Pages on every push to `main`. Correct: the
  job must run the project's test suite as a step before `mkdocs build`, and that step must be allowed
  to fail the job (no `continue-on-error: true`, no `|| true`) so a red test suite blocks the deploy
  step from ever running.

- **F28 — CVE gate is silently non-blocking with no tracking reference.** `.github/workflows/ci.yml:53-73`,
  job `security`. Line 57 sets `continue-on-error: true` on the `pip-audit` step at lines 72-73; the only
  explanation is the inline comment at line 56, `# Non-blocking — informational until vulnerable deps are
  upgraded`, which names no issue, ticket, or resolution date anywhere in the file or repo. Wrong: a
  `pip_audit` run in this repo currently reports 71 known vulnerabilities across 14 installed packages,
  and none of that is ever surfaced anywhere actionable — the job can stay green-but-lying indefinitely
  with no paper trail. Correct: the `security` job must either (a) drop `continue-on-error` so it fails
  the build on discovered CVEs, or (b) keep `continue-on-error: true` but have its
  comment/documentation link a real, dated GitHub tracking issue for the CVE debt (e.g. a
  `github.com/<org>/<repo>/issues/<n>` reference) instead of an unreferenced "informational" note.
