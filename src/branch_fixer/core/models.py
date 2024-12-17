# branch_fixer/core/models.py
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
class FixAttempt:
    """Entity representing a single attempt to fix a test error"""
    temperature: float
    status: str = "in_progress"  # in_progress, success, failed
    id: UUID = field(default_factory=uuid4)

@dataclass
class TestError:
    """Aggregate root representing a failing test"""
    test_file: Path
    test_function: str
    error_details: ErrorDetails
    id: UUID = field(default_factory=uuid4)
    status: str = "unfixed"
    fix_attempts: List[FixAttempt] = field(default_factory=list)

    def start_fix_attempt(self, temperature: float) -> FixAttempt:
        """Start a new fix attempt with the given temperature"""
        if self.status == "fixed":
            raise ValueError("Cannot start new fix attempt on a fixed error")
            
        attempt = FixAttempt(temperature=temperature)
        self.fix_attempts.append(attempt)
        return attempt

    def mark_fixed(self, attempt: FixAttempt) -> None:
        """Mark the given attempt as successful and the error as fixed"""
        if attempt not in self.fix_attempts:
            raise ValueError("Attempt does not belong to this error")
            
        attempt.status = "success"
        self.status = "fixed"

    def mark_attempt_failed(self, attempt: FixAttempt) -> None:
        """Mark the given attempt as failed"""
        if attempt not in self.fix_attempts:
            raise ValueError("Attempt does not belong to this error")
            
        attempt.status = "failed"