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

### Two AI Managers
1. **`services/ai/manager.py`** — active, LiteLLM-based, OpenRouter. Simple: sends prompt, replaces whole file.
2. **`services/ai/manager_design_draft.py`** — design draft, Marvin/Assistants API-based. Surgical line-level edits (`LineChange` with ADD/EDIT/REMOVE per line number). Not wired up. Better architecture for future work.

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
