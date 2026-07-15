# Bug catalog — pef-p23-delete-dead-sessioncoordinat

| # | Location | Defect | Evidence (harness-executed) | Caught by |
|---|----------|--------|------------------------------|-----------|
| 1 | src/branch_fixer/orchestration/coordinator.py | `SessionCoordinator.coordinate_fix_attempt` body is `pass` with a comment `# Implement coordination logic here`. The method is async and returns `None` unconditionally. Any orchestration code that depends on session coordination being performed silently gets a no-op. The class is in the production `orchestration` package, not a stub/test directory. | Grep across src/ and tests/ for SessionCoordinator/coordinate_fix_attempt/handle_failure(coordinator) returns zero hits; the full test suite passes after deletion. | `tests/test_pef_p23_delete_dead_sessioncoordinat.py` |

- **Expected (per the finding goal):** Grep across src/ and tests/ for SessionCoordinator/coordinate_fix_attempt/handle_failure(coordinator) returns zero hits; the full test suite passes after deletion.
- Every row above is recorded ground truth (finding fields + harness-executed command outputs); no value is estimated.
