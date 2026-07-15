# Bug catalog — pef-p22-delete-dead-exception-taxono

| # | Location | Defect | Evidence (harness-executed) | Caught by |
|---|----------|--------|------------------------------|-----------|
| 1 | src/branch_fixer/core/exceptions.py:2-29 | Defines FixError, CoordinationError, WorkflowError, ComponentError, InteractionError. QUALITY_AUDIT.md row 21 confirms these are 'not imported by runtime code.' dispatcher.py redefines WorkflowError independently (line 5), creating a conflicting duplicate. None of these types appear in the assigned runtime files (orchestration, services, utils). Dead exception taxonomy adds naming confusion without providing any contract. | Grep across src/ and tests/ for these symbol names returns no production references; the full test suite passes after deletion. | `tests/test_pef_p22_delete_dead_exception_taxono.py` |

- **Expected (per the finding goal):** Grep across src/ and tests/ for these symbol names returns no production references; the full test suite passes after deletion.
- Every row above is recorded ground truth (finding fields + harness-executed command outputs); no value is estimated.
