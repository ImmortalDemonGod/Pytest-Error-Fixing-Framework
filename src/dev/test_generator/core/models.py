from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional, Tuple
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoverageGap:
    """Lines in a named entity not executed by any existing test.

    uncovered_lines is a sorted tuple of 1-based line numbers from
    ``pytest-cov``/``coverage.py`` output.
    """

    entity_name: str
    uncovered_lines: Tuple[int, ...]

    @property
    def is_empty(self) -> bool:
        return len(self.uncovered_lines) == 0


@dataclass(frozen=True)
class AnalysisContext:
    """Rich context about a source file collected before LLM generation.

    Carries everything the FabricStrategy needs to write informed tests:
    the source itself, static-analysis findings, and which lines lack coverage.

    Build with ``AnalysisContext.empty(source_code)`` when tools are unavailable
    or when a cheap context-free run is acceptable.
    """

    source_code: str
    mypy_issues: Tuple[str, ...]
    ruff_issues: Tuple[str, ...]
    coverage_gaps: Tuple[CoverageGap, ...]
    # Source snippets for classes/functions imported from project-internal modules.
    # Helps the LLM understand constructor signatures it wouldn't otherwise see.
    dependency_code: str = ""

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def has_coverage_gaps(self) -> bool:
        """True if any entity has at least one uncovered line."""
        return any(not g.is_empty for g in self.coverage_gaps)

    def gaps_for(self, entity_name: str) -> Optional[CoverageGap]:
        """Return the CoverageGap for *entity_name*, or None if not found."""
        return next(
            (g for g in self.coverage_gaps if g.entity_name == entity_name), None
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def empty(cls, source_code: str) -> "AnalysisContext":
        """Minimal context when static-analysis tools are unavailable."""
        return cls(
            source_code=source_code,
            mypy_issues=(),
            ruff_issues=(),
            coverage_gaps=(),
        )


class GenerationVariant(str, Enum):
    """Which Hypothesis test variant to generate for an entity."""

    DEFAULT = "default"
    ERRORS = "errors"             # --except ValueError --except TypeError (methods only)
    ROUNDTRIP = "roundtrip"       # encode/decode pairs
    IDEMPOTENT = "idempotent"     # transform/convert
    ERRORS_EQUIVALENT = "errors_equivalent"  # validate/verify
    BINARY_OP = "binary_op"       # add/multiply


@dataclass(frozen=True)
class TestableEntity:
    """Value object representing a single class, method, or function to test."""

    name: str
    module_path: str  # dotted import path, e.g. "branch_fixer.core.models.TestError"
    entity_type: Literal["class", "method", "function", "instance_method"]
    parent_class: Optional[str] = None

    @property
    def full_path(self) -> str:
        if self.parent_class:
            return f"{self.module_path}.{self.parent_class}.{self.name}"
        return f"{self.module_path}.{self.name}"


@dataclass(frozen=True)
class ParsedModule:
    """Value object: result of parsing a Python source file."""

    source_path: Path
    module_dotpath: str  # e.g. "branch_fixer.core.models"
    entities: tuple  # tuple[TestableEntity, ...] — frozen, so tuple not list

    def entities_of_type(
        self, entity_type: Literal["class", "method", "function", "instance_method"]
    ) -> List[TestableEntity]:
        return [e for e in self.entities if e.entity_type == entity_type]


@dataclass(frozen=True)
class GenerationConfig:
    """Value object: configuration for a generation run."""

    output_dir: Path
    strategy_name: str = "hypothesis"
    max_entities: Optional[int] = None  # None = no limit


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


@dataclass
class GenerationAttempt:
    """Entity: one attempt to generate tests for a single TestableEntity."""

    entity: TestableEntity
    variant: GenerationVariant
    status: str = "pending"  # pending | success | failed | skipped
    generated_code: Optional[str] = None
    error_message: Optional[str] = None
    id: UUID = field(default_factory=uuid4)

    def mark_success(self, code: str) -> None:
        if self.status not in ("pending", "failed"):
            raise ValueError(f"Cannot mark success from status '{self.status}'")
        self.generated_code = code
        self.status = "success"

    def mark_failed(self, reason: str) -> None:
        self.error_message = reason
        self.status = "failed"

    def mark_skipped(self, reason: str) -> None:
        self.error_message = reason
        self.status = "skipped"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "entity_name": self.entity.name,
            "entity_type": self.entity.entity_type,
            "module_path": self.entity.module_path,
            "parent_class": self.entity.parent_class,
            "variant": self.variant.value,
            "status": self.status,
            "generated_code": self.generated_code,
            "error_message": self.error_message,
        }


# ---------------------------------------------------------------------------
# Aggregate Root
# ---------------------------------------------------------------------------


@dataclass
class GenerationRequest:
    """Aggregate root: a request to generate tests for a parsed module."""

    parsed_module: ParsedModule
    config: GenerationConfig
    id: UUID = field(default_factory=uuid4)
    status: str = "pending"  # pending | in_progress | completed | failed
    attempts: List[GenerationAttempt] = field(default_factory=list)

    def start(self) -> None:
        if self.status != "pending":
            raise ValueError(f"Cannot start request in status '{self.status}'")
        self.status = "in_progress"

    def add_attempt(self, attempt: GenerationAttempt) -> None:
        if self.status != "in_progress":
            raise ValueError("Request must be in_progress to add attempts")
        self.attempts.append(attempt)

    def complete(self) -> None:
        if self.status != "in_progress":
            raise ValueError(f"Cannot complete request in status '{self.status}'")
        self.status = "completed"

    def fail(self) -> None:
        self.status = "failed"

    @property
    def successful_attempts(self) -> List[GenerationAttempt]:
        return [a for a in self.attempts if a.status == "success"]

    @property
    def failed_attempts(self) -> List[GenerationAttempt]:
        return [a for a in self.attempts if a.status == "failed"]

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "source_path": str(self.parsed_module.source_path),
            "module_dotpath": self.parsed_module.module_dotpath,
            "strategy_name": self.config.strategy_name,
            "output_dir": str(self.config.output_dir),
            "status": self.status,
            "attempts": [a.to_dict() for a in self.attempts],
        }
