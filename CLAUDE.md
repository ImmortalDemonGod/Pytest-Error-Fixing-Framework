# Project: Pytest-Error-Fixing-Framework

## Critical Rules

### Commits
- **1 file per commit, always.** No exceptions. Verify with `git diff --stat` before committing.

### Python Environment
- Always use `.venv/bin/python` (Python 3.13). Never use system python3 or python3.11.
- Run tests with `.venv/bin/python -m pytest`, not bare `pytest`.

---

## Debugging

### Use snoop, not custom print/log statements
Snoop is installed in the venv. Use it instead of writing manual debug instrumentation:

```python
import snoop

@snoop
def my_function(...):
    ...

# or inline:
with snoop():
    result = subprocess.run(...)
```

Install globally in a session: `snoop.install()` — then `@snoop` works everywhere.
This is especially useful for tracing subprocess calls, return codes, and variable state.

---

## Architecture

### One AI Manager
- **`services/ai/manager.py`** — active, LiteLLM-based, OpenRouter. Persistent conversation thread per error (`self._messages`), analyze-before-fix pipeline at `temperature=0.1`, then fix generation. `manager_design_draft.py` was deleted — all valuable ideas (thread, analysis, confidence) are now in `manager.py`.
- Unimplemented features documented as `# Not yet implemented` comments in manager.py: flaky test detection, line-level edits, confidence-gated retry, Docker isolation.

### AI Model
- Default: `openrouter/openai/gpt-5-mini` (via `AIManager` default arg)
- `gpt-4o-mini` is too weak for code generation — inconsistent, frequent syntax errors
- `gpt-5-mini` fixes tests reliably on first attempt
- API key: `OPENROUTER_API_KEY` from `.env`

### Key Bug History (already fixed)
- **`change_applier.py`**: fence stripping used `[8:]` instead of `[9:]` for `` ```python `` — left stray `n` at start of every AI-generated file, breaking syntax check on every fix attempt.
- **`runner.py`**: `report.function` is absent during in-process pytest runs — `test_function` defaulted to `"unknown"`, causing `verify_fix` to run against a non-existent test node. Fixed by parsing from `report.nodeid.split("::")[-1]`.
- **`state_manager.py`**: `valid_transitions` dict used UPPERCASE keys but `FixSessionState` enum values are lowercase — `validate_transition()` always returned False.
- **`orchestrator.py`**: imported `state_manager` module then passed it as an instance — module-as-instance bug.
- **`fix_service.py`**: bare `snoop()` call at import time (line 194), and string `"FixSessionState.COMPLETED"` instead of enum value.

### Verify Fix Behavior
- `verify_fix` runs pytest as a **subprocess** (not in-process) for a clean environment.
- Uses `sys.executable -m pytest` — correct venv resolution.
- Returns True only if exit code == 0.
- Skipped tests (exit code 0) count as "fixed" — this is intentional.

---

## Running the Fixer

```bash
set -a && source .env && set +a
.venv/bin/python -m branch_fixer.main fix --non-interactive --test-path <path>
```

End-to-end pipeline: discover → parse errors → create git branch → AI generate → apply → syntax check → verify → push → cleanup.

---

## Test Generation Feature (Feature 2)

### Entry Points
- **Current (working script):** `python scripts/hypot_test_gen.py <path/to/source.py>`
- **New DDD CLI:** `.venv/bin/python -m branch_fixer.main generate --source-path <path> --output-dir generated_tests`

### Architecture (src/dev/test_generator/)
DDD layers implemented:
- `core/models.py` — domain: `GenerationRequest` (aggregate), `GenerationAttempt` (entity), `TestableEntity`, `ParsedModule`, `GenerationConfig`, `GenerationVariant`
- `analyze/parser.py` — `ModuleParser` AST visitor → `ParsedModule`
- `analyze/extractor.py` — `select_variants()` pure variant selection
- `generate/templates.py` — `build_hypothesis_command()` pure command builder
- `generate/strategies/hypothesis.py` — `HypothesisStrategy` subprocess wrapper
- `generate/optimizer.py` — `GenerationOrchestrator` application service
- `output/formatter.py` — `fix_generated_code()` AST post-processor
- `output/writer.py` — `write_attempt()` file writer
- `cli/generate.py` — Click command registered in `run_cli.py`

### Variant Logic (must match original scripts/hypot_test_gen.py exactly)
- **Classes:** `[DEFAULT]`
- **Methods/instance_methods:** `[DEFAULT, ERRORS]` + all matching specials — specials **stack** (multiple can apply to one entity)
- **Functions:** `[DEFAULT]` + only `ROUNDTRIP` or `BINARY_OP` (first match only; NO `IDEMPOTENT` or `ERRORS_EQUIVALENT` for functions)
- `ERRORS` variant = `--except ValueError --except TypeError`

### Critical subprocess gotchas
- **Always use venv-local hypothesis binary:** `Path(sys.executable).parent / "hypothesis"` — bare `hypothesis` resolves to system Python and crashes with pth file conflicts.
- **`_ensure_importable` must add both:** (1) the file's parent dir AND (2) the `src/` root when `"src"` is in the path. Adding only one breaks dotted module imports for src-layout packages without `__init__.py`.
- **`_module_dotpath_from_path` src-layout strategy:** if `"src"` is in the path, take everything after the last `src/` segment — do NOT rely on `__init__.py` walking, because top-level packages in this project (`branch_fixer`, `dev`) have no `__init__.py` at that level.
- **`hypothesis write` requires `black`:** install with `pip install 'hypothesis[cli]'` not just `pip install hypothesis`.

### Not yet implemented (Phase 4+)
- `generate/strategies/fabric.py` — LLM-based generation via LiteLLM (same pattern as `AIManager`)
- `generate/strategies/pynguin.py` — Pynguin whole-module synthesis
- `generate/optimizer.py` — coverage-gated generation (only generate when coverage < 100%)
- `shared/git.py`, `shared/testing.py`, `shared/logging.py`
