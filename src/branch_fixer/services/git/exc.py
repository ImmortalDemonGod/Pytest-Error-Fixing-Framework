
from branch_fixer.git.exceptions import GitError, NotAGitRepositoryError

class InvalidGitRepositoryError(GitError):
    """Raised when repository initialization fails."""
    pass

class NoSuchPathError(GitError):
    """Raised when the specified path does not exist."""
    pass
