# branch_fixer/services/git/models.py
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ErrorDetails:
    """Class to store detailed error information."""
    error_type: str
    message: Optional[str] = None

@dataclass
class TestError:
    """Class to store details of a test error."""
    test_function: str
    test_file: str
    error_details: ErrorDetails
class CommandResult:
    """Represents the result of a Git command execution"""
    returncode: int
    stdout: str
    stderr: str
    command: str
    
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

