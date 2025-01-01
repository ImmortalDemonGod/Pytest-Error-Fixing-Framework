from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ErrorDetails:
    """Value object representing the details of a test error"""

    error_type: str
    message: str
    stack_trace: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "stack_trace": self.stack_trace,
        }

    @staticmethod
    def from_dict(data: dict) -> "ErrorDetails":
        return ErrorDetails(
            error_type=data["error_type"],
            message=data["message"],
            stack_trace=data.get("stack_trace"),
        )


@dataclass
class FixAttempt:
    """Entity representing a single attempt to fix a test error"""

    temperature: float
    status: str = "in_progress"  # in_progress, success, failed
    id: UUID = field(default_factory=uuid4)

    def to_dict(self) -> dict:
        return {
            "temperature": self.temperature,
            "status": self.status,
            "id": str(self.id),
        }

    @staticmethod
    def from_dict(data: dict) -> "FixAttempt":
        return FixAttempt(
            temperature=data["temperature"],
            status=data["status"],
            id=UUID(data["id"]),
        )


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
        if self.status == "fixed":
            raise ValueError("Cannot start new fix attempt on a fixed error")
        attempt = FixAttempt(temperature=temperature)
        self.fix_attempts.append(attempt)
        return attempt

    def mark_fixed(self, attempt: FixAttempt) -> None:
        if attempt not in self.fix_attempts:
            raise ValueError("Attempt does not belong to this error")
        if self.status == "fixed":
            raise ValueError("Error is already fixed")
        attempt.status = "success"
        self.status = "fixed"

    def mark_attempt_failed(self, attempt: FixAttempt) -> None:
        if attempt not in self.fix_attempts:
            raise ValueError("Attempt does not belong to this error")
        if self.status == "fixed":
            raise ValueError("Cannot fail an attempt on a fixed error")
        attempt.status = "failed"

    def to_dict(self) -> dict:
        return {
            "test_file": str(self.test_file),
            "test_function": self.test_function,
            "error_details": self.error_details.to_dict(),
            "id": str(self.id),
            "status": self.status,
            "fix_attempts": [fa.to_dict() for fa in self.fix_attempts],
        }

    @staticmethod
    def from_dict(data: dict) -> "TestError":
        return TestError(
            test_file=Path(data["test_file"]),
            test_function=data["test_function"],
            error_details=ErrorDetails.from_dict(data["error_details"]),
            id=UUID(data["id"]),
            status=data["status"],
            fix_attempts=[FixAttempt.from_dict(fa) for fa in data["fix_attempts"]],
        )


@dataclass
class CodeChanges:
    """Represents code changes suggested by AI."""

    original_code: str
    modified_code: str
