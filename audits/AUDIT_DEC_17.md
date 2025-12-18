
# Audit-of-Audit: Coverage Gaps in `QUALITY_AUDIT.md`

**Single purpose:** Identify parts of this repository that are **not covered (explicitly or implicitly)** by `audits/QUALITY_AUDIT.md`, so the checklist can be extended to avoid blind spots.

## Coverage classification used
 - **Unmentioned**: no reference in `QUALITY_AUDIT.md` (neither checklist nor findings)
 - **Findings-only**: referenced in the findings table but not represented as a checklist item
 - **Referenced-only**: appears only as an aside/recommendation (not evidence of review)
 - **Directory-only**: parent directory is checklisted, but the specific file/module is not named anywhere (coverage is ambiguous)

## What `QUALITY_AUDIT.md` currently covers (high-level)
- Domain: `src/branch_fixer/core/models.py`
- Orchestration: `src/branch_fixer/orchestration/fix_service.py`, `orchestrator.py`
- Services: `services/ai/manager.py`, `services/code/change_applier.py`, `services/git/*` (generic), `services/pytest/runner.py`, `services/pytest/error_processor.py`
- Storage: `storage/session_store.py`, `storage/state_manager.py`
- Tests: unit/integration/fixtures (generic)
- Cross-cutting: CLI + logging + dependencies (generic)

Everything below lists **coverage gaps** (or “coverage uncertainty”) with a concrete checklist addition to close each gap.

---

## A. Runtime code gaps (`src/branch_fixer/`) not named in the checklist

| Gap | Coverage status in `QUALITY_AUDIT.md` | Why it matters | Proposed checklist addition |
| :--- | :--- | :--- | :--- |
| `src/branch_fixer/main.py` | Unmentioned | This is a real entry point (Taskfile runs `python -m branch_fixer.main`). Startup-side effects (sys.path manipulation, snoop/logging installation) can impact every run. | Add **Entry Point (`main.py`)**: startup behavior, environment assumptions, side effects, logging init. |
| `src/branch_fixer/utils/workspace.py` | Unmentioned | Workspace/Git validation and dependency checks gate the whole tool and control error messages presented to users. | Add **Workspace Validation (`utils/workspace.py`)**: Git discovery, permission handling, dependency verification UX. |
| `src/branch_fixer/config/settings.py` | Findings-only | Central config affects safety (debug/secrets), defaults, and environment assumptions. | Add **Configuration Modules (`config/*.py`)**: secret handling, defaults, override strategy. |
| `src/branch_fixer/config/defaults.py` | Unmentioned | Defaults shape behavior in non-obvious ways and can drift away from CLI flags and docs. | Add **Configuration Modules (`config/*.py`)**: secret handling, defaults, override strategy. |
| `src/branch_fixer/core/exceptions.py` | Referenced-only | Exception taxonomy is part of the domain contract and influences orchestration/CLI behavior. | Add **Domain Exceptions (`core/exceptions.py`)**: consistency, layering, and mapping to user errors. |
| `src/branch_fixer/orchestration/exceptions.py` | Unmentioned | Orchestrator/fix-service error typing determines retry/abort behavior and message quality. | Add **Orchestration Exceptions (`orchestration/exceptions.py`)**: typed errors + propagation boundaries. |
| `src/branch_fixer/orchestration/dispatcher.py`, `coordinator.py` | Unmentioned | These modules exist and can drift into dead-code / misleading architecture if not explicitly tracked. | Add **Orchestration Support Modules**: confirm implemented, intentionally stubbed, or removed. |
| `src/branch_fixer/storage/recovery.py` | Findings-only | Recovery/rollback is core resilience logic but is not currently a checklist item. | Add **Recovery & Checkpointing (`storage/recovery.py`)**: correctness, sync/async alignment, atomicity. |
| `src/branch_fixer/services/pytest/parsers/*` | Unmentioned | Parser correctness affects failure ingestion (even as fallback) and determines what gets fixed. | Add **Pytest Parsers (`services/pytest/parsers/`)**: edge cases, consistency with plugin-captured results. |
| `src/branch_fixer/services/pytest/models.py`, `exceptions.py`, `error_info.py`, `config.py` | Unmentioned | These define the result/error schema and config contracts; drift here silently breaks parsing + prompts. | Add **Pytest Data Contracts**: schemas + exceptions + config usage. |
| `src/branch_fixer/services/git/pr_manager.py`, `services/git/models.py` | Directory-only | PR plumbing and Git data contracts can introduce security/permissions issues and consistency drift. | Add **PR Management + Git Models**: behavior, validation, and security boundaries. |
| `src/branch_fixer/services/ai/manager_design_draft.py` | Unmentioned | Non-runtime “design draft” code still lives in-tree and can confuse maintenance/coverage. | Add **Non-runtime / Draft Modules**: ensure they are clearly isolated or excluded from production/lint/test scopes. |

---

## B. Dev tooling code (`src/dev/`) not covered

| Gap | Coverage status in `QUALITY_AUDIT.md` | Why it matters | Proposed checklist addition |
| :--- | :--- | :--- | :--- |
| `src/dev/test_generator/**` | Unmentioned | This is substantial code with its own analyzers/generators; it can become a maintenance/security risk even if not part of runtime CLI. | Add **Dev Tooling (`src/dev/`)**: intended use, safety, dependency pinning, and test coverage expectations. |
| `src/dev/cli/**`, `src/dev/shared/**` | Unmentioned | Even if empty today, the presence of these modules suggests future tooling; should be tracked explicitly. | Add **Dev CLI & Shared Utilities**: ensure intentional stubs vs incomplete implementations are documented. |

---

## C. Repo automation & operational surfaces not covered

| Gap | Coverage status in `QUALITY_AUDIT.md` | Why it matters | Proposed checklist addition |
| :--- | :--- | :--- | :--- |
| `.github/workflows/*.yml` | Unmentioned | CI defines what “green” means. Version mismatches (e.g., CI Python vs `requires-python`) and missing files (e.g., requirements) can invalidate audit conclusions. | Add **CI/CD Workflows**: Python version alignment, install strategy, secrets handling, and artifact correctness. |
| `Taskfile.yml` | Unmentioned | Task runner is the canonical dev workflow; tasks can drift from docs and real entry points. | Add **Task Runner (`Taskfile.yml`)**: verify tasks reflect real packaging/entry points and don’t rely on ignored files incorrectly. |
| Packaging split-brain (`pyproject.toml` vs `setup.py`) | Findings-only | Two packaging definitions can produce different installs/entry points depending on toolchain. | Add **Packaging Consistency**: single source of truth, entry points, editable installs, CI install path. |

---

## D. Documentation system not covered

| Gap | Coverage status in `QUALITY_AUDIT.md` | Why it matters | Proposed checklist addition |
| :--- | :--- | :--- | :--- |
| `mkdocs.yml` and `docs/**` | Unmentioned | Docs can contradict actual CLI behavior and mislead users; docs build is a deployable artifact. | Add **Documentation Alignment**: ensure docs examples match current CLI/Taskfile and that docs build in CI. |

---

## E. Test suite surfaces not explicitly covered

| Gap | Coverage status in `QUALITY_AUDIT.md` | Why it matters | Proposed checklist addition |
| :--- | :--- | :--- | :--- |
| `tests/test_click.py` | Unmentioned | Root-level tests can carry important behavior checks (CLI wiring, Click options) but can be forgotten when focusing on `tests/unit/` + `tests/integration/`. | Add **Top-level Tests (`tests/*.py`)**: ensure these are intentional, stable, and aligned with CI expectations. |
| `tests/test_math_operations.py`, `tests/temp_failing_test.py` | Findings-only | These exist to fail/demonstrate behavior; they directly affect `pytest`/CI signal. | Add **Intentional Failure Tests Policy**: require `xfail`/markers or relocation under a dedicated examples folder excluded from CI. |
| `tests/test_generator/` | Unmentioned | A directory stub suggests planned coverage for dev tooling; without a checklist item it will remain invisible. | Add **Dev Tooling Tests**: either remove stubs or ensure dev tooling has an explicit testing strategy. |

---

## F. Repository metadata, config, and operational artifacts not covered

| Gap | Coverage status in `QUALITY_AUDIT.md` | Why it matters | Proposed checklist addition |
| :--- | :--- | :--- | :--- |
| `pytest.ini` | Unmentioned | Pytest config controls discovery/markers/addopts and can invalidate conclusions about test execution and CI parity. | Add **Test Configuration (`pytest.ini`)**: ensure markers, addopts, and pythonpath match docs/CI/Taskfile. |
| `.gitignore` | Unmentioned | The tool creates artifacts (logs, backups, sessions). If ignore rules don’t match reality, sensitive or noisy files can leak into git. | Add **Generated Artifacts Policy**: verify backups/logs/session data paths are gitignored consistently. |
| `.env` / `.secrets` patterns | Unmentioned | Secret storage is implied by README finding, but there’s no checklist item to validate secret hygiene end-to-end. | Add **Secrets Handling**: env var precedence, redaction policy, and which files must never be committed. |
| `.python-version` | Unmentioned | Runtime Python version pinning impacts reproducibility and CI alignment. | Add **Runtime/Toolchain Versioning**: align `.python-version`, CI python-version, and `pyproject` constraints. |
| `uv.lock` | Directory-only | Dependency locking impacts determinism; audit should verify how installs happen (uv vs pip vs CI). | Add **Reproducible Installs**: document/verify the intended installer + lockfile usage across Taskfile/CI. |
| `session_data/`, `logs/`, `.coverage` | Unmentioned | These are operational outputs; without checklist items they become “unknown unknowns” for cleanup and privacy. | Add **Operational Outputs**: retention/cleanup policy and default locations. |

---

## G. Minimal checklist extensions (copy/paste candidates)

These are phrased as small checklist bullets you can drop into `QUALITY_AUDIT.md`:
- **Entry Point (`src/branch_fixer/main.py`)**
- **Workspace Validation (`src/branch_fixer/utils/workspace.py`)**
- **Configuration Modules (`src/branch_fixer/config/*.py`)**
- **Exception Taxonomy (`core/exceptions.py`, `orchestration/exceptions.py`)**
- **Recovery & Checkpointing (`storage/recovery.py`)**
- **Pytest Data Contracts (`services/pytest/models.py`, `exceptions.py`, `error_info.py`, `config.py`)**
- **Pytest Parsers (`services/pytest/parsers/`)**
- **PR Management + Git Models (`services/git/pr_manager.py`, `services/git/models.py`)**
- **Dev Tooling (`src/dev/**`)**
- **CI/CD Workflows (`.github/workflows/*.yml`)**
- **Task Runner (`Taskfile.yml`)**
- **Docs Build & Alignment (`mkdocs.yml`, `docs/**`)**
- **Test Configuration (`pytest.ini`)**
- **Generated Artifacts & Secrets Hygiene (`.gitignore`, `.env` policy, backup/session/log locations)**

---

## H. Audit-process gaps (concerns not represented as checklist items)

These are not “files”, but recurring audit categories that are not explicitly represented:
- **Secret handling policy** (redaction, env var precedence, avoiding logging keys)
- **Idempotency** (logging setup, repeated runs, cleanup safety)
- **Operational safety** (backup retention, cleanup of generated artifacts)
- **Performance limits** (large repos, many tests, long outputs)

Proposed checklist addition: **Operational & Security Posture** (cross-cutting): secret redaction, idempotency, cleanup policy, performance constraints.

