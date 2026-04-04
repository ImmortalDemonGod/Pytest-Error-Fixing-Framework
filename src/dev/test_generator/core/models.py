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
        """
        Whether the coverage gap contains no uncovered lines.
        
        Returns:
            True if the `uncovered_lines` tuple is empty, False otherwise.
        """
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
        """
        Determine whether any coverage gaps exist in this analysis context.
        
        Returns:
            `true` if at least one CoverageGap has one or more uncovered lines, `false` otherwise.
        """
        return any(not g.is_empty for g in self.coverage_gaps)

    def gaps_for(self, entity_name: str) -> Optional[CoverageGap]:
        """
        Finds the CoverageGap for the given entity name.
        
        Returns:
            The matching CoverageGap if present, `None` otherwise.
        """
        return next(
            (g for g in self.coverage_gaps if g.entity_name == entity_name), None
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def empty(cls, source_code: str) -> "AnalysisContext":
        """
        Create a minimal AnalysisContext containing only the provided source code.
        
        Parameters:
            source_code (str): The module's source code.
        
        Returns:
            AnalysisContext: An AnalysisContext with the given source_code and empty `mypy_issues`, `ruff_issues`, and `coverage_gaps`.
        """
        return cls(
            source_code=source_code,
            mypy_issues=(),
            ruff_issues=(),
            coverage_gaps=(),
        )


class GenerationVariant(str, Enum):
    """Which Hypothesis test variant to generate for an entity."""

    DEFAULT = "default"
    ERRORS = "errors"  # --except ValueError --except TypeError (methods only)
    ROUNDTRIP = "roundtrip"  # encode/decode pairs
    IDEMPOTENT = "idempotent"  # transform/convert
    ERRORS_EQUIVALENT = "errors_equivalent"  # validate/verify
    BINARY_OP = "binary_op"  # add/multiply


@dataclass(frozen=True)
class TestableEntity:
    """Value object representing a single class, method, or function to test."""

    name: str
    module_path: str  # dotted import path, e.g. "branch_fixer.core.models.TestError"
    entity_type: Literal["class", "method", "function", "instance_method", "module"]
    parent_class: Optional[str] = None

    @property
    def full_path(self) -> str:
        """
        Builds the dotted path to the entity, including the parent class when present.
        
        Returns:
            full_path (str): Dotted module path to the entity (e.g. "package.module.Class.method" or "package.module.function").
        """
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
        """
        Filter entities to those with the specified entity type.
        
        Parameters:
            entity_type: One of "class", "method", "function", or "instance_method" specifying which entity kinds to include.
        
        Returns:
            A list of TestableEntity instances whose `entity_type` equals the provided `entity_type`.
        """
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
        """
        Mark the attempt as successful and store the generated test code.
        
        Sets this attempt's `generated_code` to `code` and updates `status` to `"success"`.
        This transition is allowed only when the current `status` is `"pending"` or `"failed"`.
        
        Parameters:
            code (str): The generated test code to attach to this attempt.
        
        Raises:
            ValueError: If the current status is not `"pending"` or `"failed"`.
        """
        if self.status not in ("pending", "failed"):
            raise ValueError(f"Cannot mark success from status '{self.status}'")
        self.generated_code = code
        self.status = "success"

    def mark_failed(self, reason: str) -> None:
        """
        Mark the generation attempt as failed and record the failure reason.
        
        Parameters:
            reason (str): Human-readable explanation of why the attempt failed; stored on the attempt as `error_message`.
        """
        self.error_message = reason
        self.status = "failed"

    def mark_skipped(self, reason: str) -> None:
        """
        Mark the generation attempt as skipped and record the reason.
        
        Parameters:
            reason (str): Explanation for why the attempt was skipped; assigned to `error_message`.
        """
        self.error_message = reason
        self.status = "skipped"

    def to_dict(self) -> dict:
        """
        Produce a dictionary representation of the GenerationAttempt suitable for JSON serialization.
        
        Returns:
            dict: A mapping with the following keys:
                - "id": UUID as a string
                - "entity_name": the target entity's name
                - "entity_type": the target entity's type
                - "module_path": the module dot-path containing the entity
                - "parent_class": the parent class name or None
                - "variant": the generation variant's string value
                - "status": current attempt status
                - "generated_code": generated test code or None
                - "error_message": failure or skip reason or None
        """
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
        """
        Transition the request's status from "pending" to "in_progress".
        
        Raises:
            ValueError: If the request's current status is not "pending".
        """
        if self.status != "pending":
            raise ValueError(f"Cannot start request in status '{self.status}'")
        self.status = "in_progress"

    def add_attempt(self, attempt: GenerationAttempt) -> None:
        """
        Append a GenerationAttempt to this request while the request is in progress.
        
        Parameters:
            attempt (GenerationAttempt): The attempt to append to the request's attempts list.
        
        Raises:
            ValueError: If the request's status is not "in_progress".
        """
        if self.status != "in_progress":
            raise ValueError("Request must be in_progress to add attempts")
        self.attempts.append(attempt)

    def complete(self) -> None:
        """
        Mark the generation request as completed.
        
        Raises:
            ValueError: If the request's current status is not "in_progress".
        """
        if self.status != "in_progress":
            raise ValueError(f"Cannot complete request in status '{self.status}'")
        self.status = "completed"

    def fail(self) -> None:
        """
        Mark the generation request as failed.
        
        Sets the request's status to "failed" without performing any validation.
        """
        self.status = "failed"

    @property
    def successful_attempts(self) -> List[GenerationAttempt]:
        """
        Collects all generation attempts that completed successfully.
        
        Returns:
            List[GenerationAttempt]: Attempts whose `status` is `"success"`.
        """
        return [a for a in self.attempts if a.status == "success"]

    @property
    def failed_attempts(self) -> List[GenerationAttempt]:
        """
        Return all generation attempts that have failed.
        
        Returns:
            failed_attempts (List[GenerationAttempt]): List of attempts whose status equals "failed".
        """
        return [a for a in self.attempts if a.status == "failed"]

    def to_dict(self) -> dict:
        """
        Serialize the generation request into a JSON-serializable mapping of its metadata and attempts.
        
        Returns:
            dict: A mapping containing the request `id` (string), `source_path` (string), `module_dotpath` (string), `strategy_name` (string), `output_dir` (string), `status` (string), and `attempts` (list of attempt dictionaries produced by each attempt's `to_dict()`).
        """
        return {
            "id": str(self.id),
            "source_path": str(self.parsed_module.source_path),
            "module_dotpath": self.parsed_module.module_dotpath,
            "strategy_name": self.config.strategy_name,
            "output_dir": str(self.config.output_dir),
            "status": self.status,
            "attempts": [a.to_dict() for a in self.attempts],
        }
