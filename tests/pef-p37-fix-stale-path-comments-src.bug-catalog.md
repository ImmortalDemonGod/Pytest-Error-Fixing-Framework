# Bug catalog — pef-p37-fix-stale-path-comments-src (F21)

- **Symptom**: The module-level header comment at the top of the test file names a location the
  file has never occupied in the current tree (it reads as if the file still lived under
  `src/branch_fixer/services/pytest/`), misdirecting a developer who greps/reads the comment to
  locate the file on disk.
  - **Location**: `tests/unit/core/test_verify_fix_workflow.py:1`
  - **Wrong (current)**: `# src/branch_fixer/services/pytest/test_verify_fix_workflow.py`
  - **Correct (expected)**: `# tests/unit/core/test_verify_fix_workflow.py` — the file's actual
    on-disk path, per plan decision D-1 (`.aiv/plans/pef-p37-fix-stale-path-comments-src-plan.md` §7).
