class NotAGitRepositoryError(Exception):
    """Exception raised when a directory is not a valid git repository."""
    pass

class GitError(Exception):
    """Generic exception for Git errors."""
    pass
