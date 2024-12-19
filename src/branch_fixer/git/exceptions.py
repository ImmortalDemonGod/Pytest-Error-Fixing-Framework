
class GitError(Exception):
    """Base exception for Git-related errors."""
    pass

class NotAGitRepositoryError(GitError):
    """Raised when the target directory is not a Git repository."""
    pass
