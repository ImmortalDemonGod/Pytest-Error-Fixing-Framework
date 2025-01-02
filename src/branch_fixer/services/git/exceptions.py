# branch_fixer/services/git/exceptions.py
from typing import TYPE_CHECKING

class GitError(Exception):
    """Base class for exceptions in this module."""
    pass

class NotAGitRepositoryError(GitError):
    """Exception raised when a directory is not a valid git repository."""
    pass

class BranchCreationError(GitError):
    """Exception raised when branch creation fails."""
    pass

class MergeConflictError(GitError):
    """Exception raised when a merge conflict occurs."""
    pass


class PRError(Exception):
    """Base exception for PR operations"""
    pass

class PRCreationError(PRError):
    """Raised when PR creation fails"""
    pass

class PRUpdateError(PRError):
    """Raised when PR update fails"""
    pass

class PRValidationError(PRError):
    """Raised when PR validation fails"""
    pass

class SafetyError(Exception):
    """Base exception for safety operations"""
    pass

class BackupError(SafetyError):
    """Raised when backup operations fail"""
    pass

class RestoreError(SafetyError):
    """Raised when restore operations fail"""
    pass

class ProtectedPathError(SafetyError):
    """Raised when attempting to modify protected paths"""
    pass

class InvalidGitRepositoryError(GitError):
    """Raised when repository initialization fails."""
    pass

class NoSuchPathError(GitError):
    """Raised when the specified path does not exist."""
    pass

class BranchNameError(GitError):
    """Raised when branch name is invalid."""
    pass

if TYPE_CHECKING:
    pass
