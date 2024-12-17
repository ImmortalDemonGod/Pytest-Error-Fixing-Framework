# branch_fixer/services/git/models.py
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

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
