class GitError(Exception):
    """Base exception for Git-related errors."""
    pass

class BranchCreationError(GitError):
    """Raised when branch creation fails."""
    pass

class MergeConflictError(GitError):
    """Raised when merging branches results in conflicts."""
    pass
