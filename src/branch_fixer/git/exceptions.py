class NotAGitRepositoryError(Exception):
    """Exception raised when a directory is not a valid git repository."""
    pass

class BranchCreationError(GitError):
    """Exception raised when branch creation fails."""
    pass

class MergeConflictError(GitError):
    """Exception raised when a merge conflict occurs."""
    pass
