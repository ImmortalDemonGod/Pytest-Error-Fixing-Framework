# Bug Catalog — pef-p21-remove-snoop-from-hard-runti

- **Symptom:** Tool refuses to start (`ImportError`) in any environment that does not have the debug-only `snoop` package installed, even though `snoop` is never required for correct runtime behavior.
  **Location:** `src/branch_fixer/utils/workspace.py:20`
  **Wrong:** `"snoop"` is listed in `WorkspaceValidator.REQUIRED_DEPENDENCIES` (line 20), so `check_dependencies()` (line 94) treats a missing `snoop` import exactly like a missing `click`/`pytest`/`aiohttp`/`git` import and raises `ImportError`, blocking the entire tool from starting.
  **Correct:** `snoop` is a debugging aid (per CLAUDE.md: "Use snoop, not custom print/log statements" — a developer-experience tool), not a runtime requirement. `"snoop"` must not appear in `REQUIRED_DEPENDENCIES`, and `check_dependencies()` must not raise `ImportError` when only `snoop` is unimportable; production installations without debug tooling must still start successfully.
