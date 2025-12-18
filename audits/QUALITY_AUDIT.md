# Pytest-Fixer Quality & Resilience Audit

**Auditor:** `Cascade`
**Date Started:** `2025-12-17`

This document contains the findings of a comprehensive code audit of the `pytest-fixer` repository. Its purpose is to identify areas of strength and opportunities for improvement in architecture, code quality, resilience, documentation, and testing.

---

## Audit Findings

*Use the table below to log your findings as you discover them. Add new rows as needed.*

| Component      | Category          | Finding / Observation                                                                                                                       | Severity (Low/Med/High) | Recommendation                                                                                                                  |
| :------------- | :---------------- | :------------------------------------------------------------------------------------------------------------------------------------------ | :---------------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| `AIManager`    | Error Handling    | If the AI returns malformed JSON, `_parse_response` raises a generic `ValueError`. This makes it hard for the orchestrator to know *why* it failed. | Medium                  | Create a new `ParsingError` subclass of `AIManagerError` and raise that instead.                                              |
 | `README.md`    | Doc Alignment     | The README and docs provide mixed invocation guidance (`task run:fix` vs `python -m branch_fixer.main` vs `python -m src.branch_fixer.main`), reinforcing inconsistent import roots (including tests importing `src.branch_fixer.*`) and likely motivating `sys.path` hacks in `main.py`. | High                    | Standardize on a single invocation/import root and update README/docs/tests accordingly; remove `sys.path` manipulation once unified. |
| `core/models.py` | Domain Integrity | Domain invariants rely on plain string `status` fields and generic `ValueError`s (e.g., fixed vs unfixed). This makes it harder for orchestration/CLI layers to distinguish user-error vs system-error and to implement consistent retries/telemetry. | Medium | Introduce domain-specific exceptions (from `core/exceptions.py` or a richer taxonomy) and replace string statuses with an `Enum`/`Literal` + validation. |
| `core/models.py` | Serialization | `TestError.from_dict()` assumes keys like `fix_attempts` are always present and does not validate `status` values. This is brittle for persisted sessions / schema evolution. | Medium | Use defensive defaults (`data.get("fix_attempts", [])`), validate required fields, and consider schema versioning in storage. |
| `core/models.py` | Completeness | `CodeChanges` has no `to_dict`/`from_dict`, which may complicate persistence and debugging if changes need to be stored in sessions. | Low | Add explicit serialization methods (or document that `CodeChanges` is transient-only) and ensure orchestrator/storage agree on the representation. |
 | `core/exceptions.py` | Error Taxonomy | The exception taxonomy appears mislocated and unused: it defines coordination/workflow/component-interaction errors (orchestration-level concerns) rather than domain invariant violations, is not imported by runtime code, and overlaps in naming with exceptions redefined elsewhere (e.g., orchestration stubs). | Medium | Either redesign `core/exceptions.py` to contain true domain invariant exceptions and adopt them in `core/models.py` + tests, or remove/move these types into the orchestration layer and centralize exception taxonomy to avoid duplicate/competing definitions. |
 | `orchestration/fix_service.py` | Side Effects | A bare `snoop()` call is executed at import-time, which is likely leftover debugging and introduces unexpected behavior/overhead. | High | Remove the stray call and keep snoop usage behind explicit dev flags or targeted decorators. |
 | `orchestration/fix_service.py` | Resilience | If an exception occurs after `apply_changes_with_backup()` succeeds (e.g., `_verify_fix()` raises), there is no guaranteed backup restoration path, so the workspace can be left in a mutated state for subsequent attempts. | High | Ensure restore happens on *all* failure/exception paths once a backup exists (e.g., `finally` block or explicit exception handling that restores when `backup_path` is set). |
 | `orchestration/fix_service.py` | Error Handling | Failures are often collapsed into a generic `FixServiceError` message, reducing the orchestrator/CLI’s ability to classify retryable vs fatal errors and to present consistent user-facing messages. | Medium | Introduce typed exceptions (or structured result objects) so orchestration can decide retry/abort and can report actionable errors without losing context. |
 | `orchestration/orchestrator.py` | State Management | Both `FixService` and `FixOrchestrator` mutate `FixSession.completed_errors`; `FixOrchestrator._handle_error_fix()` appends unconditionally, risking duplicates and skewing completion logic (e.g., counts/"all fixed" checks). | Medium | Centralize session mutation in one layer and guard against duplicates before appending. |
 | `orchestration/orchestrator.py` | Correctness | In `fix_error()`, `FixService` is instantiated with `state_manager=state_manager` where `state_manager` is the imported module, not a `StateManager` instance; this likely breaks state transitions in `_update_session_if_present()`. | High | Pass the configured `StateManager` instance (or `None`) consistently, and add type checks/validation at initialization time. |
 | `orchestration/orchestrator.py` | Error Handling | The module defines `FixOrchestratorError`/`SessionError`, but most code raises `RuntimeError`/`ValueError` and does not catch `FixServiceError`, so a single exception can bypass retry logic and abort the session. | Medium | Use the orchestrator’s exception types consistently and treat known `FixServiceError`s as a failed attempt (unless explicitly fatal). |
 | `orchestration/exceptions.py` | Error Taxonomy | The orchestration exception hierarchy is inconsistent and partially unused: `FixOrchestratorError`/`SessionError`/`FixAttemptError` are not referenced by the orchestrator code, while `FixServiceError` is a separate base type used heavily by `fix_service.py`, making consistent catch/route logic difficult. | Medium | Consolidate under a single orchestration base exception (or make `FixServiceError` a subclass of `FixOrchestratorError`), and preserve structured context (retryable vs fatal + root cause) instead of collapsing most failures into string-wrapped exceptions. |
 | `AIManager` | Security | `AIManager.__init__()` mutates global process environment variables (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`), potentially overwriting user configuration and exposing keys to child processes. | Medium | Avoid global env mutation; prefer provider-specific client configuration or a scoped env override that is restored after use. |
 | `AIManager` | Error Handling | `generate_fix()` wraps prompt construction, provider errors, and parse failures into `CompletionError`, reducing classification of retryable vs fatal failures. | Medium | Add a dedicated parsing exception (or keep `PromptGenerationError`/`CompletionError` distinct) so orchestrator can handle parse failures differently from transport/provider failures. |
 | `code/change_applier.py` | Safety | Backups are written to `<test_dir>/.backups/` with no obvious gitignore rule; backups can accumulate and be accidentally committed. | Medium | Store backups under a single tool-owned, gitignored directory (e.g., `session_data/` or `.branch_fixer/backups/`) and optionally prune on success. |
 | `code/change_applier.py` | Resilience | `apply_changes_with_backup()` catches all exceptions and returns `(False, backup_path)`, making it hard for callers to distinguish backup failure vs write failure vs verification failure. | Medium | Raise typed errors (`BackupError`/`ChangeApplicationError` or central taxonomy) and let orchestration decide retry/abort while ensuring restore happens when a backup exists. |
 | `code/change_applier.py` | Atomicity | Writes use `Path.write_text()` directly; a crash/interruption can corrupt the file, and restore is best-effort only. | Medium | Use atomic write pattern (write temp then replace) and guarantee restore in a `finally` once a backup exists. |
 | `git/repository.py` | Resilience | `_find_git_root()` requires `.git/` to exist in the provided directory and fails when invoked from subdirectories, despite using `search_parent_directories=True` later. | High | Remove the pre-check and rely on GitPython’s parent search (or walk parents) so the tool works from any subdirectory. |
 | `git/repository.py` | Correctness | `_get_main_branch()` reads `.git/HEAD` and raises on detached HEAD; this can break in CI or after checking out a commit SHA. | Medium | Detect detached HEAD and fall back to a configured default (or derive main branch via `git symbolic-ref refs/remotes/origin/HEAD`). |
 | `git/branch_manager.py` / `git/repository.py` | Consistency | Branch name validation exists in multiple places with different rules, risking inconsistent behavior across call sites. | Medium | Centralize branch naming rules/validation in one component and reuse it consistently. |
 | `git/repository.py` / `git/pr_manager.py` | Correctness | `GitRepository.create_pull_request_sync()` is annotated/documented as returning `bool` but returns the `PRDetails` object from `PRManager.create_pr()`. This is currently “truthy” so CLI conditionals pass, but it is a contract bug that will confuse callers and tests. | Medium | Make `create_pull_request_sync()` return `PRDetails` (or an explicit result type) and update call sites accordingly; avoid relying on truthiness for control flow. |
 | `git/pr_manager.py` | Completeness | PR operations are largely placeholders: `create_pr()` does not perform any of its documented validations (required fields, branch existence/conflicts, max-files enforcement), `update_pr()` does not apply updates or track history, and `get_pr_history()` / `close_pr()` are unimplemented. | Medium | Either explicitly scope PR management as “in-memory/demo only” (and remove async stubs), or implement validation + change history + integration hooks (and add tests). |
 | `git/models.py` | Consistency | Git models mix several unrelated concerns (command execution results, PR domain models, branch metadata, and a separate `ErrorDetails`/`GitErrorDetails` that overlaps conceptually with `core.models.ErrorDetails` and `core.models.TestError`). This increases cognitive load and risks drift/duplication across layers. | Medium | Split models by concern (e.g., `command_models.py`, `pr_models.py`, `branch_models.py`) and align error/test representations with the domain layer to avoid parallel, inconsistent schemas. |
 | `git/pr_manager.py` / `git/models.py` | Correctness | `PRManager.create_pr()` accepts `modified_files` but does not propagate them into `PRDetails.modified_files`, so PR details lose critical context. | Low | Populate `PRDetails.modified_files` (and metadata) from inputs and add unit tests for field propagation. |
 | `pytest/models.py` | Data Contract | `TestResult`/`SessionResult` define a very broad schema (markers, parameters, stdout/stderr/log_output, traceback) but the runner populates only a subset. This makes it unclear which fields are part of the stable contract vs aspirational, and increases drift risk. | Medium | Either slim the models to fields that are actually captured today (and document that contract), or fully populate the declared fields and add tests that assert completeness of captured data. |
 | `pytest/config.py` / `pytest/exceptions.py` | Consistency | `PytestConfig` and typed exceptions (`PytestExecutionError`, `PytestTimeoutError`, etc.) exist but are not used by `PytestRunner` (runner does not accept a config object and does not raise these exception types). This weakens failure classification and creates dead/rot-prone API surface. | Medium | Integrate `PytestConfig` + typed exceptions into `PytestRunner` (validate config, raise typed errors) or remove them until they are actually part of the supported contract. |
 | `pytest/error_info.py` | Duplication | `ErrorInfo` is a parallel error schema used by the string-parsing parsers, while the primary CLI path uses structured `SessionResult` + `TestResult` plus `process_pytest_results`. This splits the error contract across two representations with inconsistent naming/types (e.g., `function` vs `test_function`, `str` paths vs `Path`). | Medium | Choose one canonical representation for pytest failures. If parsers are intended as a fallback, align their schema to the structured model and document which path is authoritative. |
 | `pytest/parsers/*` | Correctness | The parser stack is effectively unused and likely incompatible with the current captured output: `FailureParser.parse_test_failures()` only starts after seeing a `FAILURES` section and underscore test headers, while `PytestRunner.capture_test_output()` emits simplified `FAILED ...`/`E ...` lines. `UnifiedErrorParser` is not referenced by runtime code. | Medium | Either delete the parsers/unified parser path in favor of the structured `SessionResult -> TestError` flow, or rework runner output capture to preserve raw pytest text and align parser triggers; add integration tests proving the chosen ingestion path extracts representative failures and collection errors. |
 | `pytest/parsers/collection_parser.py` | Robustness | `CollectionParser` relies on a complex multi-line regex and returns only a synthetic message; it drops useful structured fields (e.g., both the collected path and conflicting path). This overlaps with the structured path, which currently uses a placeholder collection file path. | Medium | Preserve actual file paths and conflict details (either via plugin capture or parser output), and unify collection-error handling so downstream fixing targets the real file; add tests for multiple collection error formats. |
 | `pytest/runner.py` | UX | `PytestPlugin.pytest_collection_modifyitems()` prints every collected test to stdout unconditionally, which can clutter CLI output and interfere with downstream parsing. | Low | Use logging gated behind a debug/verbose flag instead of printing. |
 | `pytest/runner.py` | Environment | `verify_fix()` shells out to the `pytest` executable, which may not match the active interpreter/venv. | Medium | Invoke `sys.executable -m pytest` for consistent environments and dependency resolution. |
 | `pytest/error_processor.py` | Correctness | Collection errors are converted to `TestError` with a placeholder `unknown_collection_file.py`, preventing targeted fixing and potentially misleading prompts. | Medium | Parse the real file path from the collection error (or carry it from the plugin) and populate `TestError.test_file` accurately. |
 | `storage/session_store.py` | Resilience | Session storage does not appear to handle a corrupt `sessions.json` (e.g., JSON decode errors) and has no schema versioning strategy for forward compatibility. | Medium | Add corruption handling (backup corrupt file and recreate), add `schema_version`, and include migration logic/tests. |
 | `storage/session_store.py` | Serialization | Persisted sessions omit key fields (e.g., `errors`, `warnings`) and store `completed_errors`/`current_error` as IDs only, so `load_session()` cannot reconstruct a meaningful `FixSession` without external state. | High | Persist `FixSession.to_dict()` (or a deliberate, documented subset) and add round-trip tests to ensure complete serialization/deserialization. |
 | `storage/state_manager.py` | Correctness | `valid_transitions` uses uppercase keys (e.g., `INITIALIZING`) but validation uses `FixSessionState.value` (lowercase), making transitions invalid; `validate_session_state()` compares to `"COMPLETED"` instead of `"completed"`. | High | Use Enum consistently (`state.name` or lowercase keys), fix comparisons, and add unit tests for allowed/denied transitions. |
 | `storage/recovery.py` / `orchestration/orchestrator.py` | Correctness | Recovery APIs (`create_checkpoint`, `handle_failure`, `restore_checkpoint`) are `async` but invoked synchronously in the orchestrator, and restore logic is largely a stub (no file restore). | High | Either make recovery synchronous or make orchestrator async and `await` recovery calls; implement concrete file restore + atomic writes/locking for recovery index updates. |
 | `tests/` | Test Hygiene | The repo includes intentionally failing tests (`tests/test_math_operations.py`, `tests/temp_failing_test.py`) that will fail a normal `pytest` run, undermining CI signal and developer confidence. | High | Move demo/failing tests under dedicated fixtures/examples, mark as `xfail`, or exclude them from the default test suite. |
 | `tests/conftest.py` | Test Infrastructure | `tests/conftest.py` modifies `sys.path` and uses wildcard imports for fixtures. Combined with `pytest.ini` `pythonpath=src`, this increases risk of import ambiguity and namespace pollution. | Medium | Prefer a single import strategy (use `pythonpath=src` only) and import fixtures explicitly rather than `import *`. |
 | `tests/fixtures/integration_fixtures.py` | Test Correctness | The fixture suite appears out of sync with current implementations (e.g., `AIManager` mocked as async, mismatch between `ChangeApplier.apply_changes` vs `apply_changes_with_backup`, `TestRunner.run_test` vs `verify_fix`). | Medium | Update fixtures to match real interfaces (or delete unused ones) and add a small number of integration tests that exercise real orchestration paths with realistic mocks. |
 | `tests/unit/git/` | Coverage Gap | The unit test tree has fixtures for Git but no actual unit tests for `services/git/*` behavior (branch creation/cleanup, error wrapping, detached HEAD cases). | Medium | Add focused unit tests for GitRepository/BranchManager invariants and error classification (mocking subprocess/GitPython as needed). |
 | `config/settings.py` | Security | `DEBUG` is hardcoded to `True` and `SECRET_KEY` is hardcoded (`'your-secret-key'`), which is unsafe if this config is ever used in production paths or logged. | High | Remove hardcoded secrets, default `DEBUG` to `False`, and read settings from environment variables (or a config system). |
 | `config/logging_config.py` | Logging | `setup_logging()` adds handlers each time it is called (potential duplicate logs) and routes snoop logs to the same file without checking existing handlers. There is also no explicit redaction strategy for secrets. | Medium | Make logging setup idempotent (check existing handlers), add redaction for sensitive fields, and consider routing file logs to a tool-owned directory under the repo root. |
 | `pyproject.toml` | Dependencies | Some dependencies appear unused or redundant (`marvin`, `iniconfig`, `pluggy`), and `setup.py` conflicts with `pyproject.toml` as the canonical packaging source. | Medium | Audit imports to remove unused deps, rely on `pyproject.toml` as the single source of truth, and align dependency management (optionally commit `uv.lock` if using uv for reproducible installs). |
 | `setup.py` | Packaging | `setup.py` declares only `mkdocs` in `install_requires`, conflicting with the `pyproject.toml` dependency list; `pip install .` (CI) likely installs an incomplete environment and can cause runtime/tests to fail. | High | Remove or modernize `setup.py` and add an explicit `pyproject.toml` build-system section so dependencies/entry points come from a single source of truth. |
 | `services/ai/manager_design_draft.py` | Maintainability | The draft implementation lives in the shipped runtime package and defines a parallel `AIManager` + duplicate models (including a third `TestError`), while also calling async recovery APIs synchronously (`create_checkpoint`, `handle_failure`). Although currently unused, this increases cognitive load and risks accidental import. | Medium | Move to `src/dev/` or docs (or delete) and exclude from runtime/lint/test/package surfaces; reassess whether `marvin` is needed as a dependency. |
 | `storage/recovery.py` | Atomicity | Recovery point index updates (`recovery_points.json`) are read-modify-write with no atomic replace/locking and may corrupt on crash; restore logic does not actually restore files and uses `print` instead of logging. | Medium | Use atomic write + file locking for index updates, implement a concrete file restore strategy, and route messages through the logger. |
 | `main.py` | Packaging | The entry point mutates `sys.path` at import time and installs `snoop` globally on import, creating side effects and undermining packaging/venv expectations. | High | Remove `sys.path` hacks, provide a real console entry point, and gate `snoop.install` behind a debug flag with idempotent setup. |
| `pytest.ini` | Test Configuration | `pythonpath=src` combined with additional `sys.path` manipulation (e.g., `tests/conftest.py`) and tests importing `src.branch_fixer.*` creates multiple import roots, increasing the risk of duplicate module loads and hard-to-debug import behavior. | Medium | Standardize on a single import strategy (prefer `branch_fixer.*`), remove `sys.path` hacks, and keep `pytest.ini` minimal. |
| `.github/workflows/*.yml` | CI/CD Reliability | CI uses Python 3.10 despite `requires-python >= 3.13`, and other workflows reference a missing `requirements.txt` and wrong source dir (`pytest_fixer` vs `branch_fixer`), making CI/coverage/docstring jobs likely broken. | High | Align workflows with `pyproject.toml` (Python 3.13, install via `uv` or `pip install -e '.[dev]'`) and remove/replace `requirements.txt` assumptions; validate source dirs. |
| `docs/user-guide/01-installation.md` | Doc Alignment | Docs instruct `uv sync` "from the lock file", but `uv.lock` is currently gitignored, so a clean clone cannot follow the reproducible install steps. | Medium | Either commit `uv.lock` (preferred for reproducibility) or update docs to describe generating a lock / using `uv pip install -e '.[dev]'`. |
| `docs/user-guide/02-quickstart.md` | Doc Alignment | The quickstart suggests invoking the tool via `python -m src.branch_fixer.main ...`, which conflicts with the Taskfile (`python -m branch_fixer.main`) and reinforces inconsistent import roots. | Medium | Standardize on a single invocation path and update docs to match the supported packaging/entry points. |
| `.gitignore` | Hygiene | `uv.lock` is gitignored (undermining reproducible installs) and backup directories like `.backups/` (used by `ChangeApplier`) are not explicitly ignored, risking accidental commits. | Medium | Decide whether to commit `uv.lock` and align docs accordingly; ignore tool-generated backup directories consistently. |
| `src/dev/**` | Packaging | `src/dev` is a Python package (has `__init__.py`) and will be included by `find_packages`, potentially shipping incomplete dev tooling (`dev.*`) to end users. | Medium | Move dev tooling outside `src` or explicitly exclude it from packaging; alternatively, complete and document it. |
 | `.python-version` | Reproducibility | There is no `.python-version` pin despite requiring Python 3.13+, so toolchain alignment relies on external discipline. | Low | Add `.python-version` (or equivalent pinning strategy) and keep it aligned with CI + `pyproject.toml`. |
 | *(Add your findings here)* | ...               | ...                                                                                                                                         | ...                     | ...                                                                                                                             |

---

## Component Audit Checklist

*Use this checklist to guide your exploration of the codebase. Check off items as you complete your analysis for that component.*

### I. Core Logic & Domain Integrity (`src/branch_fixer/core/`)

- [x] **Domain Models (`models.py`)**
    -   **Architectural Consistency:** Are the aggregate/entity/value-object roles clear?
    -   **Code Quality:** Are the `to_dict`/`from_dict` methods comprehensive?
    -   **Resilience:** How are business rules enforced (e.g., preventing a fix on an already-fixed error)? Is `ErrorDetails` truly immutable?
- [x] **Domain Exceptions (`exceptions.py`)**
    -   **Architectural Consistency:** Does the exception taxonomy reflect domain invariants and support higher-layer classification?
    -   **Resilience:** Are domain errors specific enough to drive retries/user messaging without relying on generic `ValueError`?

### II. Application Orchestration & State Flow (`src/branch_fixer/orchestration/`)

- [x] **Single-Error Workflow (`fix_service.py`)**
    -   **Architectural Consistency:** Trace the `attempt_fix` method. Does it correctly coordinate the different infrastructure services?
    -   **Resilience:** How are failures during the workflow handled? Is the backup/restore mechanism correctly invoked?
- [x] **Multi-Error Workflow (`orchestrator.py`)**
    -   **Architectural Consistency:** Does the `FixOrchestrator` cleanly manage the `FixSession` lifecycle?
    -   **Code Quality:** Is the multi-retry logic (with temperature scaling) clear and easy to follow?
- [x] **Orchestration Exceptions (`exceptions.py`)**
    -   **Error Handling:** Are exceptions typed and used consistently across orchestrator + fix service?
- [x] **Orchestration Support Modules (`dispatcher.py` and `coordinator.py`)**
    -   **Completeness:** Are these production code, intentionally stubbed, or dead code? Do they match documented architecture?

### III. Infrastructure Services & External Interactions (`src/branch_fixer/services/`)

- [x] **AI Manager (`ai/manager.py`)**
    -   **Resilience:** How are LLM API errors (e.g., timeouts, key errors) and malformed responses handled?
    -   **Code Quality:** Is the prompt construction logic clear? Is the response parsing robust?
- [x] **Code Applier (`code/change_applier.py`)**
    -   **Resilience:** Is the backup-and-restore mechanism safe and atomic? What happens if the backup or restore operation itself fails?
    -   **Code Quality:** Is the syntax validation (`compile()`) sufficient for its purpose?
 - [x] **Git Repository (`git/`)**
     -   **Resilience:** Are `subprocess` and `GitPython` errors handled gracefully and wrapped in custom exceptions?
     -   **Code Quality:** Is the state management clean (i.e., does the tool reliably return the user to their original branch)?
 - [x] **Pytest Runner (`pytest/`)**
     -   **Architectural Consistency:** Review `runner.py`. Is the data capture via the custom plugin robust?
     -   **Code Quality:** Review `error_processor.py`. Is the mapping from a `SessionResult` to domain `TestError`s complete and correct?
 - [x] **Git PR Management + Models (`git/pr_manager.py` and `git/models.py`)**
     -   **Completeness:** Are PR operations implemented (or explicitly non-goals) and validated?
     -   **Code Quality:** Are Git-related models coherent and used consistently across services?
 - [x] **Pytest Data Contracts (`pytest/models.py`, `pytest/exceptions.py`, `pytest/error_info.py`, `pytest/config.py`)**
     -   **Architectural Consistency:** Are result/error schemas stable and complete for downstream consumers (orchestration, prompts, persistence)?
     -   **Resilience:** Are exceptions typed and actionable (retryable vs fatal)? Is configuration actually used?
 - [x] **Pytest Parsers (`pytest/parsers/`)**
     -   **Correctness:** Do parsers handle real-world edge cases and remain consistent with the plugin-based capture?
     -   **Usage/Compatibility:** The parser stack is effectively unused and likely incompatible with the current captured output. 
 - [x] **Non-runtime / Draft Modules (`ai/manager_design_draft.py`)**
     -   **Maintainability:** Is draft code clearly isolated/excluded from runtime/lint/test surfaces to avoid confusion?

### IV. Persistence, State, and Recovery (`src/branch_fixer/storage/`)

- [x] **Session Storage (`session_store.py`)**
    -   **Resilience:** How does the store handle a missing or corrupt `sessions.json` file?
    -   **Code Quality:** Are all `FixSession` fields correctly serialized and deserialized?
- [x] **State Machine (`state_manager.py`)**
    -   **Architectural Consistency:** Is the state machine logic correctly enforcing valid transitions?
- [x] **Recovery & Checkpointing (`recovery.py`)**
    -   **Resilience:** Are checkpoints created/restored atomically? Is sync/async usage consistent with callers?

### V. Test Suite Quality (`tests/`)

- [x] **Unit Tests (`tests/unit/`)**
    -   **Test Quality:** Do tests cover edge cases and error conditions, or just the happy path? Are mocks used effectively?
- [x] **Integration Tests (`tests/integration/`)**
    -   **Test Quality:** Do the tests cover key interactions between layers (e.g., `Orchestrator` -> `Service` -> `AIManager`)?
- [x] **Test Infrastructure (`tests/fixtures/` and `tests/conftest.py`)**
    -   **Code Quality:** Are the fixtures easy to understand and use? Do they set up and tear down state reliably?
- [x] **Top-level Tests (`tests/*.py`)**
    -   **Test Quality:** Are top-level tests stable, intentional, and aligned with CI expectations?
- [x] **Intentional Failure / Demo Tests Policy**
    -   **Resilience:** Are any intentionally failing tests marked/isolated so they don’t break normal `pytest`/CI runs?
- [x] **Dev Tooling Tests (`tests/test_generator/`)**
    -   **Completeness:** Does dev tooling have an explicit test strategy, or should these stubs be removed?

### VI. Cross-Cutting Concerns

- [x] **Configuration & CLI (`utils/run_cli.py` and `utils/cli.py`)**
    -   **Architectural Consistency:** How are configuration settings propagated through the system?
    -   **Resilience:** Is user input validated? How are CLI-level errors reported?
- [x] **Logging (`config/logging_config.py`)**
    -   **Documentation Alignment:** Do log messages provide a clear and useful trace of the application's execution? Are there any potential secrets being logged?
- [x] **Dependencies (`pyproject.toml` and `uv.lock`)**
    -   **Architectural Consistency:** Are the dependencies well-chosen? Are there any that seem unnecessary?
- [x] **Operational & Security Posture (Cross-Cutting)**
    -   **Secret handling:** Are API keys/config handled via env vars/.env without being logged or persisted?
    -   **Idempotency:** Are repeated runs safe (logging setup, snoop setup, cleanup)?
    -   **Operational outputs:** Are backups/sessions/logs created under predictable, gitignored locations?
    -   **Performance constraints:** Are there hot paths (subprocess-heavy loops, verbose stdout) that may not scale?

### VII. Repository Tooling, CI/CD, and Documentation

- [x] **Entry Point (`src/branch_fixer/main.py`)**
    -   **Correctness:** Does startup have side effects (e.g., `sys.path` changes) that could break packaging or user environments?
    -   **Observability:** Is logging/snoop configuration idempotent and correctly scoped to debug/dev modes?
- [x] **Workspace Validation (`src/branch_fixer/utils/workspace.py`)**
    -   **Resilience:** Are Git discovery, permission checks, and dependency checks accurate and user-actionable?
- [x] **Configuration Modules (`src/branch_fixer/config/settings.py` and `defaults.py`)**
    -   **Security:** Are secrets and debug flags handled safely (no hardcoded secrets, safe defaults)?
    -   **Consistency:** Do defaults align with CLI flags and documentation?
- [x] **Packaging Consistency (`pyproject.toml` and `setup.py`)**
    -   **Correctness:** Is there a single source of truth for dependencies and entry points across dev/CI installs?
- [x] **Test Configuration (`pytest.ini`)**
    -   **Correctness:** Do markers, addopts, and pythonpath settings match the intended test execution environment?
- [x] **CI/CD Workflows (`.github/workflows/*.yml`)**
    -   **Reliability:** Do workflows reference existing files and install dependencies in a way that matches local development?
    -   **Security:** Are secrets handled safely and logs/artifacts free of sensitive data?
- [x] **Task Runner (`Taskfile.yml`)**
    -   **Dev Workflow Consistency:** Do tasks match documented setup, CI behavior, and the actual entry points?
- [x] **Docs Build & Alignment (`mkdocs.yml`, `docs/**`, `README.md`)**
    -   **Doc Alignment:** Do docs accurately describe installation/configuration (e.g., `.env` keys) and CLI behavior?
- [x] **Generated Artifacts & Secrets Hygiene (`.gitignore`, `.env`, operational outputs)**
    -   **Hygiene:** Are backups/logs/session data and other generated artifacts consistently gitignored and cleaned up?
- [x] **Dev Tooling (`src/dev/**`)**
    -   **Scope & Maintenance:** Is dev tooling intentionally supported (with docs/tests) or should it be isolated/removed?
- [x] **Runtime/Toolchain Versioning (`.python-version`)**
    -   **Reproducibility:** Are toolchain pins aligned with CI and `pyproject` requirements?
