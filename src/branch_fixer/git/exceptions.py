class BranchCreationError(GitError):
    """Raised when branch creation fails."""
    pass

class MergeConflictError(GitError):
    """Raised when merging branches results in conflicts."""
    pass
