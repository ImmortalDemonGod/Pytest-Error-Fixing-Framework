# branch_fixer/services/git/models.py
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ErrorDetails:
    """Class to store detailed error information."""
    error_type: str
    message: Optional[str] = None

@dataclass
class GitErrorDetails:
    """
    Class to store details of a Git-related error or metadata.

    Previously named 'TestError'—now renamed to avoid confusion 
    with the core.models.TestError used for test failures.
    """
    test_function: str
    test_file: str
    error_details: ErrorDetails
@dataclass
class CommandResult:
    """Represents the result of a Git command execution"""
    returncode: int
    stdout: str
    stderr: str
    command: List[str]  # Changed from str to List[str]

    @property
    def failed(self) -> bool:
        """Check if command failed"""
        return self.returncode != 0

    @property
    def success(self) -> bool:
        """Check if command succeeded"""
        return self.returncode == 0

    def __str__(self) -> str:
        """String representation of command result"""
        return f"CommandResult(command='{' '.join(self.command)}', returncode={self.returncode})"
    
class PRStatus(Enum):
    """Pull request status states"""
    DRAFT = "draft"
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"
    MERGED = "merged"
    CLOSED = "closed"

@dataclass
class PRChange:
    """Record of a change made to a pull request"""
    timestamp: datetime
    field: str
    old_value: Any
    new_value: Any
    reason: Optional[str] = None

@dataclass
class PRDetails:
    """Comprehensive pull request details"""
    id: int
    title: str
    description: str
    branch_name: str
    status: PRStatus
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    modified_files: List[Path] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    change_history: List[PRChange] = field(default_factory=list)

@dataclass
class BackupMetadata:
    """Metadata for repository backups"""
    id: str
    timestamp: datetime
    description: str
    branch_name: str
    file_hashes: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass
class BranchStatus:
    """
    Represents the status of a Git branch.
    
    Attributes:
        current_branch (str): The name of the current branch.
        has_changes (bool): Indicates if there are uncommitted changes.
        changes (List[str]): List of changed files.
    """
    current_branch: str
    has_changes: bool
    changes: List[str]

@dataclass
class BranchMetadata:
    """
    Metadata about a Git branch.
    
    Attributes:
        name: Branch name
        current: Whether this is the current branch
        upstream: Remote tracking branch if any
        last_commit: SHA of last commit
        modified_files: Files with uncommitted changes
    """
    name: str
    current: bool 
    upstream: Optional[str]
    last_commit: str
    modified_files: List[Path]

