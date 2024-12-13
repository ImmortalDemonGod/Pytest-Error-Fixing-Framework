# src/branch_fixer/domain/models.py
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from pathlib import Path
from typing import List, Optional

@dataclass(frozen=True)
class ErrorDetails:
    """Value object representing the details of a test error"""
    error_type: str
    message: str
    stack_trace: Optional[str] = None

@dataclass
class TestError:
    """Aggregate root representing a failing test"""
    test_file: Path
    test_function: str
    error_details: ErrorDetails
    id: UUID = field(default_factory=uuid4)
    status: str = "unfixed"
    fix_attempts: List = field(default_factory=list)