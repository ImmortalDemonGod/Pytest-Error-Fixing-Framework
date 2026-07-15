# Bug catalog — pef-p12-implement-branch-manager-met

- **Symptom:** `BranchManager.get_branch_metadata()` unconditionally raises `NotImplementedError`, even for a valid, existing branch name on a healthy repository.
  **Location:** `src/branch_fixer/services/git/branch_manager.py:169` (`get_branch_metadata`)
  **Wrong:** Any caller (status checks, PR enrichment) gets an unhandled `NotImplementedError` instead of a `BranchMetadata` instance, despite the method's documented signature and return type (`BranchMetadata`) implying it is implemented.
  **Correct:** For a known branch, `get_branch_metadata(branch_name)` should return a populated `BranchMetadata(name=..., current=..., upstream=..., last_commit=..., modified_files=...)` reflecting the real state of the branch (e.g. `name` equals the requested branch, `current` is `True` when it is the checked-out branch, `last_commit` equals the branch tip's commit SHA, `modified_files` reflects uncommitted changes).

- **Symptom:** `BranchManager.is_branch_merged()` unconditionally raises `NotImplementedError`, even when asked whether a branch that has genuinely been merged (or genuinely not been merged) into a target branch is merged.
  **Location:** `src/branch_fixer/services/git/branch_manager.py:225` (`is_branch_merged`)
  **Wrong:** Callers cannot ever get a `bool` answer — every invocation raises, regardless of the branches' actual merge state, despite the documented return type (`bool`).
  **Correct:** `is_branch_merged(branch_name, target_branch=...)` should return `True` when `branch_name`'s history is fully contained in `target_branch` (i.e. it was merged), and `False` when `branch_name` has commits not reachable from `target_branch` (i.e. it was not merged) — without raising in either case.
