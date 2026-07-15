# Bug catalog — pef-p22-delete-dead-exception-taxono

| # | Location | Defect | Evidence (harness-executed) | Caught by |
|---|----------|--------|------------------------------|-----------|
| 1 | src/branch_fixer/core/exceptions.py:2-29 | Defines FixError, CoordinationError, WorkflowError, ComponentError, InteractionError. QUALITY_AUDIT.md row 21 confirms these are 'not imported by runtime code.' dispatcher.py redefines WorkflowError independently (line 5), creating a conflicting duplicate. None of these types appear in the assigned runtime files (orchestration, services, utils). Dead exception taxonomy adds naming confusion without providing any contract. | Grep across src/ and tests/ for these symbol names returns no production references; the full test suite passes after deletion. | `tests/test_pef_p22_delete_dead_exception_taxono.py` |

- **Expected (per the finding goal):** Grep across src/ and tests/ for these symbol names returns no production references; the full test suite passes after deletion.
- Every row above is recorded ground truth (finding fields + harness-executed command outputs); no value is estimated.

## Bullet detail (this is a deletion-only finding — no surviving behavior surface, per
plan §12/§17; entries restate the negative-space defects: presence where there should be absence)

- **Symptom:** `src/branch_fixer/core/exceptions.py:2-29` defines a 5-class exception taxonomy
  (`FixError`, `CoordinationError`, `WorkflowError`, `ComponentError`, `InteractionError`) that is
  never imported by any runtime/production code in `src/` or `tests/` (confirmed by
  `audit/02-static-audit.md:54` and `QUALITY_AUDIT.md:21`).
  **Wrong:** the module exists and is importable, presenting a false public API surface with zero
  actual contract (nothing raises or catches these types).
  **Correct:** the file does not exist; `from src.branch_fixer.core.exceptions import CoordinationError`
  (or any of the other 4 symbols) raises `ModuleNotFoundError`.

- **Symptom:** `src/branch_fixer/orchestration/dispatcher.py:5` independently redefines
  `WorkflowError(Exception)` with no inheritance relationship to `core/exceptions.py:14`'s
  `WorkflowError(FixError)`.
  **Wrong:** two same-named, unrelated exception classes coexist in the codebase — an `isinstance`
  check against one `WorkflowError` silently fails to catch instances of the other.
  **Correct:** no duplicate, unrelated class shares the name `WorkflowError` (both are deleted).

- **Symptom:** `src/branch_fixer/orchestration/dispatcher.py`'s `WorkflowDispatcher` class
  (`dispatch_fix_workflow`, `handle_component_error`) is a pure-`pass`-stub with zero callers anywhere
  in `src/` or `tests/`.
  **Wrong:** the class/methods exist, implying a working dispatch contract that does not exist —
  callers would silently get `None` back with no dispatch logic executed.
  **Correct:** the file does not exist; there is no dead stub implying unimplemented behavior.

- **Symptom:** `tests/unit/core/test_error.py` is a 0-byte placeholder test file for the
  soon-to-be-deleted `core/exceptions.py`.
  **Wrong:** an empty test file exists, testing nothing, for a module with no consumers.
  **Correct:** the file does not exist.

- **Symptom:** `docs/developer-guide/04-execution-flow.md:165` documents `FixError` "and subtypes" as
  part of the error hierarchy.
  **Wrong:** the docs describe a hierarchy that has no runtime contract and is about to be deleted,
  misleading future readers into thinking it is a live, used API.
  **Correct:** the bullet no longer references `FixError`; `GitError`/`AIManagerError` (the live,
  undeleted types in the same list) remain documented.
