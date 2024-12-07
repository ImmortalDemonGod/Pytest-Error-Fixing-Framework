# Domain-Driven Design Concepts Guide for pytest-fixer

## Introduction

This guide explains the Domain-Driven Design (DDD) concepts necessary to rebuild `pytest-fixer`. Each concept is illustrated with concrete examples from our domain.

## Table of Contents

1. [Core DDD Concepts](#core-ddd-concepts)
   - [1. Ubiquitous Language](#1-ubiquitous-language)
   - [2. Bounded Contexts](#2-bounded-contexts)
   - [3. Aggregates](#3-aggregates)
   - [4. Entities](#4-entities)
   - [5. Value Objects](#5-value-objects)
   - [6. Domain Services](#6-domain-services)
   - [7. Repositories](#7-repositories)
   - [8. Domain Events](#8-domain-events)
   - [9. Application Services](#9-application-services)
2. [Common DDD Patterns](#common-ddd-patterns)
   - [1. Factory Pattern](#1-factory-pattern)
   - [2. Specification Pattern](#2-specification-pattern)
   - [3. Anti-Corruption Layer](#3-anti-corruption-layer)
3. [DDD Best Practices](#ddd-best-practices)
4. [Avoiding Common Mistakes](#avoiding-common-mistakes)
5. [Practical Tips for pytest-fixer](#practical-tips-for-pytest-fixer)

---

## Core DDD Concepts

### 1. Ubiquitous Language

The shared language between developers and domain experts. For `pytest-fixer`, this includes:

- **Test Error**: A failing pytest test that needs fixing
- **Fix Attempt**: A single try at fixing a test error
- **Fix Generation**: The process of creating a fix
- **Verification**: Checking if a fix works
- **Code Changes**: Modifications made to fix an error

**Why it matters**: Using consistent terminology prevents confusion and misunderstandings. For example, we always say "fix attempt" rather than "try" or "fix iteration".

---

### 2. Bounded Contexts

Separate domains with their own models and rules. In `pytest-fixer`:

1. **Error Analysis Context**
   - Handles test error parsing and analysis
   - Own concept of what an error means
   - Focuses on error details and classification

2. **Fix Generation Context**
   - Handles creating and applying fixes
   - Manages AI interaction
   - Tracks fix attempts and results

3. **Test Execution Context**
   - Handles running tests
   - Manages test discovery
   - Processes test results

4. **Version Control Context**
   - Manages code changes
   - Handles branching strategy
   - Controls commit operations

Each context has its own:
- Models and rules
- Interfaces and services
- Data structures and validation

---

### 3. Aggregates

Clusters of related objects treated as a single unit. Key aggregates in `pytest-fixer`:

#### 1. TestError Aggregate

```python
class TestError:  # Aggregate Root
    id: UUID
    test_file: Path
    test_function: str
    error_details: ErrorDetails  # Value Object
    location: CodeLocation      # Value Object
    fix_attempts: List[FixAttempt]  # Child Entity
    status: FixStatus          # Value Object

    def start_fix_attempt(self, temperature: float) -> FixAttempt:
        """Create and track a new fix attempt"""
```

#### 2. FixSession Aggregate

```python
class FixSession:  # Aggregate Root
    id: UUID
    error: TestError
    current_attempt: Optional[FixAttempt]
    attempts: List[FixAttempt]
    status: FixSessionStatus
```

**Rules for Aggregates**:
- Only reference other aggregates by ID
- Maintain consistency boundaries
- Handle transactional requirements

---

### 4. Entities

Objects with identity that changes over time. Key entities:

#### 1. FixAttempt

```python
@dataclass
class FixAttempt:
    id: UUID
    error_id: UUID
    attempt_number: int
    temperature: float
    changes: Optional[CodeChanges]
    status: FixStatus
```

#### 2. TestCase

```python
@dataclass
class TestCase:
    id: UUID
    file_path: Path
    function_name: str
    source_code: str
```

**Entity characteristics**:
- Have unique identity
- Mutable over time
- Track state changes
- Maintain history

---

### 5. Value Objects

Immutable objects without identity. Examples:

```python
@dataclass(frozen=True)
class CodeLocation:
    file_path: Path
    line_number: int
    column: Optional[int] = None
    function_name: Optional[str] = None

@dataclass(frozen=True)
class ErrorDetails:
    error_type: str
    message: str
    stack_trace: Optional[str] = None
    captured_output: Optional[str] = None

@dataclass(frozen=True)
class CodeChanges:
    original: str
    modified: str
    location: CodeLocation
    description: Optional[str] = None
```

**Value Object rules**:
- Immutable
- No identity
- Equality based on attributes
- Self-validating

---

### 6. Domain Services

Services that handle operations not belonging to any entity:

```python
class ErrorAnalysisService:
    """Analyzes test output to create TestError instances"""
    def analyze_error(self, test_output: str, test_file: Path) -> TestError:
        """Extract error information from test output"""

class FixGenerationService:
    """Generates fixes using AI"""
    def generate_fix(self, error: TestError, attempt: FixAttempt) -> CodeChanges:
        """Generate a fix for the error"""
```

**When to use Services**:
- Operation spans multiple entities
- Complex domain logic
- External system integration

---

### 7. Repositories

Interfaces for persisting and retrieving aggregates:

```python
class TestErrorRepository(Protocol):
    def get_by_id(self, error_id: UUID) -> Optional[TestError]:
        """Retrieve a TestError by ID"""
    
    def save(self, error: TestError) -> None:
        """Save a TestError"""
    
    def get_unfixed_errors(self) -> List[TestError]:
        """Get all unfixed errors"""
```

**Repository principles**:
- One repository per aggregate
- Hide storage details
- Return fully-loaded aggregates
- Handle persistence concerns

---

### 8. Domain Events

Notifications of significant changes in the domain:

```python
@dataclass
class FixAttemptStarted:
    error_id: UUID
    attempt_id: UUID
    timestamp: datetime

@dataclass
class FixVerificationCompleted:
    error_id: UUID
    attempt_id: UUID
    success: bool
    verification_output: str
```

**When to use Events**:
- State changes matter to other contexts
- Need to maintain audit trail
- Cross-context communication needed

---

### 9. Application Services

Orchestrate the use cases of the application:

```python
class TestFixingApplicationService:
    def __init__(
        self,
        error_analysis: ErrorAnalysisService,
        fix_generation: FixGenerationService,
        version_control: VersionControlService,
        error_repository: TestErrorRepository,
        event_publisher: EventPublisher
    ):
        # Initialize dependencies...

    def attempt_fix(self, error_id: UUID, temperature: float = 0.4) -> FixAttempt:
        """Coordinate the process of attempting a fix"""
```

**Application Service responsibilities**:
- Use case orchestration
- Transaction management
- Event publishing
- Error handling

---

## Common DDD Patterns

### 1. Factory Pattern

Use factories to create complex aggregates:

```python
class TestErrorFactory:
    def from_test_output(
        self,
        test_output: str,
        test_file: Path,
        test_function: str
    ) -> TestError:
        """Create TestError from test output"""
```

---

### 2. Specification Pattern

Express complex queries or validations:

```python
class FixableErrorSpecification:
    def is_satisfied_by(self, error: TestError) -> bool:
        """Check if error can be fixed"""
```

---

### 3. Anti-Corruption Layer

Protect domain model from external systems:

```python
class AIServiceAdapter:
    """Adapt AI service responses to our domain model"""
    def adapt_response(self, ai_response: dict) -> CodeChanges:
        """Convert AI response to domain model"""
```

---

## DDD Best Practices

1. **Start with Bounded Contexts**
   - Identify clear boundaries first
   - Define context interactions
   - Document context maps

2. **Focus on Behavior**
   - Model behavior, not just data
   - Use rich domain models
   - Encapsulate business rules

3. **Use Value Objects**
   - Create immutable value objects
   - Validate on creation
   - Make invalid states unrepresentable

4. **Handle Edge Cases**
   - Define error scenarios
   - Use domain events
   - Maintain consistency

5. **Test Domain Logic**
   - Unit test aggregates
   - Test business rules
   - Mock infrastructure

---

## Avoiding Common Mistakes

1. **Anemic Domain Model**
   - Don't create data-only classes
   - Include business logic
   - Use rich behavior

2. **Leaky Abstractions**
   - Keep infrastructure out of domain
   - Use clean interfaces
   - Maintain boundaries

3. **Missing Events**
   - Use events for important changes
   - Track state transitions
   - Maintain audit trail

4. **Complex Aggregates**
   - Keep aggregates focused
   - Use proper boundaries
   - Split if too complex

---

## Practical Tips for pytest-fixer

1. **Start with Core Domain Model (TestError)**
2. **Add Behavior Incrementally**
3. **Use Events for Tracking**
4. **Keep Interfaces Clean**
5. **Test Domain Logic Thoroughly**

---

## Additional Blueprint: Aligning on Goals

🧙🏾‍♂️: Below is a cohesive, from-scratch rewrite that combines the strengths of previous approaches into a cleaner, domain-driven, and modular architecture. It clarifies domain logic, separates concerns, and provides a strong foundation for future extensions. This blueprint focuses on core functionality: discovering test errors, generating fixes using AI (via a hypothetical `AIManager` or `Coder`), applying changes, verifying them, and persisting state. It employs DDD patterns, a clear layering approach, and sets up a workable starting point.

### Key Design Principles

1. **Domain-Driven Design (DDD)**
   - **Domain Model**: Defines `TestError`, `FixAttempt`, `ErrorDetails`, and related entities as the heart of the domain.
   - **Value Objects**: `CodeLocation`, `CodeChanges` are immutable and model specific domain concepts clearly.
   - **Repositories**: Abstract away persistence details behind interfaces.
   - **Domain Services**: Provide business logic that doesn't belong inside entities.

2. **Clean Architecture Layers**
   - **Domain (Core)**: Entities, Value Objects, Domain Services, Repository Interfaces.
   - **Application**: Orchestrates use cases, coordinates domain objects, and triggers domain services.
   - **Infrastructure**: Implementation details like Git-based repository, AI integration, running `pytest`, file I/O.

3. **Events & Extensibility**
   - Define domain events minimally for the starting point.
   - Events can be published to other interested parties (e.g., logging, analytics, asynchronous pipelines).

4. **Testing & Configuration**
   - Testing can be added incrementally.
   - Configuration handled through environment variables or a config file.
   - Placeholders for integration points (`AIManager`, `TestRunner`, `VCSManager`) to be implemented concretely later.

### Project Structure

```
pytest_fixer/
├── domain/
│   ├── models.py        # Entities, Value Objects
│   ├── events.py        # Domain events
│   ├── repositories.py  # Repository interfaces
│   ├── services.py      # Domain services (e.g., ErrorAnalysis)
│   └── __init__.py
├── application/
│   ├── usecases.py      # Application services (Use cases)
│   ├── dto.py           # Data Transfer Objects if needed
│   └── __init__.py
├── infrastructure/
│   ├── ai_manager.py     # AI integration (fix generation)
│   ├── test_runner.py    # Pytest integration
│   ├── vcs_manager.py    # Git operations
│   ├── repository_impl.py# Git or file-based repository implementation
│   ├── change_applier.py # Applying and reverting code changes
│   └── __init__.py
└── main.py
```

---

### Detailed Implementation

#### `domain/models.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

@dataclass(frozen=True)
class CodeLocation:
    file_path: Path
    line_number: int
    column: Optional[int] = None
    function_name: Optional[str] = None

@dataclass(frozen=True)
class ErrorDetails:
    error_type: str
    message: str
    stack_trace: Optional[str] = None
    captured_output: Optional[str] = None

@dataclass(frozen=True)
class CodeChanges:
    original: str
    modified: str
    description: Optional[str] = None

@dataclass
class FixAttempt:
    id: UUID = field(default_factory=uuid4)
    error_id: UUID = field(default_factory=uuid4)
    attempt_number: int = 1
    temperature: float = 0.4
    changes: Optional[CodeChanges] = None
    status: str = "pending"
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def mark_success(self, changes: CodeChanges):
        self.changes = changes
        self.status = "success"
        self.completed_at = datetime.utcnow()

    def mark_failure(self):
        self.status = "failed"
        self.completed_at = datetime.utcnow()

@dataclass
class TestError:
    id: UUID = field(default_factory=uuid4)
    test_file: Path = field(default_factory=Path)
    test_function: str = ""
    error_details: ErrorDetails = field(default_factory=ErrorDetails)
    location: CodeLocation = field(default_factory=lambda: CodeLocation(Path("."), 0))
    fix_attempts: List[FixAttempt] = field(default_factory=list)
    status: str = "unfixed"
    
    def start_fix_attempt(self, temperature: float) -> FixAttempt:
        attempt = FixAttempt(
            error_id=self.id,
            attempt_number=len(self.fix_attempts) + 1,
            temperature=temperature
        )
        self.fix_attempts.append(attempt)
        return attempt

    def mark_fixed(self, attempt: FixAttempt):
        attempt.status = "success"
        self.status = "fixed"

    def mark_attempt_failed(self, attempt: FixAttempt):
        attempt.mark_failure()

    def can_attempt_fix(self) -> bool:
        return self.status == "unfixed"
```

---

#### `domain/events.py`

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class FixAttemptStarted:
    error_id: UUID
    attempt_id: UUID
    timestamp: datetime

@dataclass
class FixAttemptCompleted:
    error_id: UUID
    attempt_id: UUID
    success: bool
    timestamp: datetime
```

---

#### `domain/repositories.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from .models import TestError

class TestErrorRepository(ABC):
    @abstractmethod
    def get_by_id(self, error_id: UUID) -> Optional[TestError]:
        pass

    @abstractmethod
    def save(self, error: TestError) -> None:
        pass

    @abstractmethod
    def get_unfixed_errors(self) -> List[TestError]:
        pass
```

---

#### `domain/services.py`

```python
import re
from pathlib import Path
from typing import Optional, List
from .models import ErrorDetails, TestError, CodeLocation

class ErrorAnalysisService:
    def analyze_errors(self, test_output: str) -> Optional[List[TestError]]:
        # Basic regex-based approach to find failing tests:
        # Placeholder: Real logic might integrate directly with pytest APIs.
        pattern = r"(.*?::(.*?) FAILED (.*)\n([\s\S]*?)(?=\n\n|$))"
        matches = re.finditer(pattern, test_output)
        errors = []
        for m in matches:
            file_path, test_func, err_type, details = m.groups()
            location = CodeLocation(Path(file_path), 0)
            err_details = ErrorDetails(
                error_type=err_type.strip(),
                message=details.strip(),
                stack_trace=details
            )
            errors.append(TestError(
                test_file=Path(file_path),
                test_function=test_func,
                error_details=err_details,
                location=location
            ))
        return errors if errors else None
```

---

#### `application/usecases.py`

```python
from typing import Optional
from uuid import UUID

from ..domain.models import TestError
from ..domain.repositories import TestErrorRepository
from ..infrastructure.ai_manager import AIManager
from ..infrastructure.test_runner import TestRunner
from ..infrastructure.vcs_manager import VCSManager
from ..infrastructure.change_applier import ChangeApplier

class TestFixingService:
    def __init__(
        self,
        error_repo: TestErrorRepository,
        ai_manager: AIManager,
        test_runner: TestRunner,
        vcs_manager: VCSManager,
        change_applier: ChangeApplier,
        initial_temp: float = 0.4,
        temp_increment: float = 0.1,
        max_retries: int = 3
    ):
        self.error_repo = error_repo
        self.ai_manager = ai_manager
        self.test_runner = test_runner
        self.vcs = vcs_manager
        self.change_applier = change_applier
        self.initial_temp = initial_temp
        self.temp_increment = temp_increment
        self.max_retries = max_retries

    def discover_and_record_errors(self) -> None:
        stdout, stderr = self.test_runner.run_all_tests()
        analysis_service = self.test_runner.get_analysis_service()
        errors = analysis_service.analyze_errors(stdout + stderr)
        if not errors:
            return
        for e in errors:
            self.error_repo.save(e)

    def attempt_fix(self, error_id: UUID) -> bool:
        error = self.error_repo.get_by_id(error_id)
        if not error or not error.can_attempt_fix():
            return False

        temperature = self.initial_temp
        for _ in range(self.max_retries):
            attempt = error.start_fix_attempt(temperature)
            # Generate fix
            changes = self.ai_manager.generate_fix(error, temperature)
            if not changes:
                # No fix generated, increase temp and continue
                error.mark_attempt_failed(attempt)
                temperature += self.temp_increment
                continue

            # Apply changes
            self.change_applier.apply(changes, error.location)
            
            # Verify fix
            passed = self.test_runner.run_test_and_check(
                error.test_file, error.test_function
            )
            
            if passed:
                # Commit changes to VCS
                self.vcs.commit_changes(f"Fix {error.test_file}:{error.test_function}")
                attempt.mark_success(changes)
                error.mark_fixed(attempt)
                self.error_repo.save(error)
                return True
            else:
                # Revert changes and mark attempt failed
                self.change_applier.revert()
                error.mark_attempt_failed(attempt)
                self.error_repo.save(error)
                temperature += self.temp_increment

        # No success after max retries
        self.error_repo.save(error)
        return False
```

---

#### `infrastructure/ai_manager.py`

```python
from typing import Optional
from ..domain.models import TestError, CodeChanges

class AIManager:
    def __init__(self, model_name: str = "gpt-4"):
        self.model_name = model_name

    def generate_fix(self, error: TestError, temperature: float) -> Optional[CodeChanges]:
        # Placeholder logic - integrate with OpenAI or Aider coder
        # Construct a prompt from error details
        prompt = f"Fix this test error:\n{error.error_details.message}"
        # Here you'd call the AI API or Aider coder to get a changed version of the file
        # For demonstration, let's pretend we got a changed file content:
        modified = error.location.file_path.read_text().replace("bug", "fix")
        original = error.location.file_path.read_text()
        return CodeChanges(original=original, modified=modified, description="AI suggested fix")
```

---

#### `infrastructure/test_runner.py`

```python
from typing import Tuple
from .ai_manager import AIManager
from ..domain.services import ErrorAnalysisService
from pathlib import Path
import subprocess

class TestRunner:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.analysis_service = ErrorAnalysisService()

    def run_all_tests(self) -> Tuple[str, str]:
        cmd = ["pytest", "-v"]
        result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True)
        return result.stdout, result.stderr

    def run_test_and_check(self, test_file: Path, test_function: str) -> bool:
        cmd = ["pytest", "-q", f"{test_file}::{test_function}"]
        result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True)
        # If it returns 0 and '1 passed' is in stdout, we consider it passed
        return (result.returncode == 0 and "1 passed" in result.stdout.lower())

    def get_analysis_service(self) -> ErrorAnalysisService:
        return self.analysis_service
```

---

#### `infrastructure/vcs_manager.py`

```python
import subprocess
from pathlib import Path

class VCSManager:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def commit_changes(self, message: str):
        subprocess.run(["git", "add", "."], cwd=self.project_dir, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=self.project_dir, check=True)
```

---

#### `infrastructure/change_applier.py`

```python
from ..domain.models import CodeChanges, CodeLocation

class ChangeApplier:
    def __init__(self):
        self.backup_content = None
        self.target_file = None

    def apply(self, changes: CodeChanges, location: CodeLocation):
        self.target_file = location.file_path
        self.backup_content = self.target_file.read_text()
        self.target_file.write_text(changes.modified)

    def revert(self):
        if self.target_file and self.backup_content is not None:
            self.target_file.write_text(self.backup_content)
```

---

#### `infrastructure/repository_impl.py`

```python
from uuid import UUID
from typing import Optional, List
from pathlib import Path
import json

from ..domain.models import TestError
from ..domain.repositories import TestErrorRepository

class FileBasedTestErrorRepository(TestErrorRepository):
    """Simple file-based repository using JSON to store errors."""
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_error_file(self, error_id: UUID) -> Path:
        return self.storage_path / f"{error_id}.json"

    def get_by_id(self, error_id: UUID) -> Optional[TestError]:
        f = self._get_error_file(error_id)
        if not f.exists():
            return None
        data = json.loads(f.read_text())
        return self._deserialize_testerror(data)

    def save(self, error: TestError) -> None:
        f = self._get_error_file(error.id)
        f.write_text(json.dumps(self._serialize_testerror(error), indent=2))

    def get_unfixed_errors(self) -> List[TestError]:
        errors = []
        for f in self.storage_path.glob("*.json"):
            data = json.loads(f.read_text())
            err = self._deserialize_testerror(data)
            if err.status == "unfixed":
                errors.append(err)
        return errors

    def _serialize_testerror(self, error: TestError) -> dict:
        return {
            "id": str(error.id),
            "test_file": str(error.test_file),
            "test_function": error.test_function,
            "status": error.status,
            "error_details": {
                "error_type": error.error_details.error_type,
                "message": error.error_details.message,
                "stack_trace": error.error_details.stack_trace,
                "captured_output": error.error_details.captured_output
            },
            "location": {
                "file_path": str(error.location.file_path),
                "line_number": error.location.line_number,
                "column": error.location.column
            },
            "fix_attempts": [
                {
                    "id": str(a.id),
                    "error_id": str(a.error_id),
                    "attempt_number": a.attempt_number,
                    "temperature": a.temperature,
                    "status": a.status,
                    "started_at": a.started_at.isoformat(),
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "changes": {
                        "original": a.changes.original if a.changes else None,
                        "modified": a.changes.modified if a.changes else None,
                        "description": a.changes.description if a.changes else None
                    } if a.changes else None
                } for a in error.fix_attempts
            ]
        }

    def _deserialize_testerror(self, data: dict) -> TestError:
        from datetime import datetime
        from uuid import UUID
        from ..domain.models import ErrorDetails, CodeLocation, CodeChanges, FixAttempt, TestError
        fix_attempts = []
        for a in data.get("fix_attempts", []):
            changes = a["changes"]
            fix_attempts.append(FixAttempt(
                id=UUID(a["id"]),
                error_id=UUID(a["error_id"]),
                attempt_number=a["attempt_number"],
                temperature=a["temperature"],
                status=a["status"],
                started_at=datetime.fromisoformat(a["started_at"]),
                completed_at=datetime.fromisoformat(a["completed_at"]) if a["completed_at"] else None,
                changes=CodeChanges(**changes) if changes and changes["original"] else None
            ))

        return TestError(
            id=UUID(data["id"]),
            test_file=Path(data["test_file"]),
            test_function=data["test_function"],
            status=data["status"],
            error_details=ErrorDetails(**data["error_details"]),
            location=CodeLocation(
                Path(data["location"]["file_path"]),
                data["location"]["line_number"],
                data["location"]["column"]
            ),
            fix_attempts=fix_attempts
        )
```

---

#### `main.py` (Example Entry Point)

```python
import sys
from pathlib import Path
from uuid import UUID

from pytest_fixer.domain.repositories import TestErrorRepository
from pytest_fixer.infrastructure.repository_impl import FileBasedTestErrorRepository
from pytest_fixer.infrastructure.ai_manager import AIManager
from pytest_fixer.infrastructure.test_runner import TestRunner
from pytest_fixer.infrastructure.vcs_manager import VCSManager
from pytest_fixer.infrastructure.change_applier import ChangeApplier
from pytest_fixer.application.usecases import TestFixingService

def main():
    project_dir = Path(".")
    storage_path = project_dir / ".pytest_fixer_storage"
    error_repo: TestErrorRepository = FileBasedTestErrorRepository(storage_path)
    ai_manager = AIManager(model_name="gpt-4")
    test_runner = TestRunner(project_dir)
    vcs_manager = VCSManager(project_dir)
    change_applier = ChangeApplier()

    service = TestFixingService(
        error_repo=error_repo,
        ai_manager=ai_manager,
        test_runner=test_runner,
        vcs_manager=vcs_manager,
        change_applier=change_applier,
        initial_temp=0.4,
        temp_increment=0.1,
        max_retries=3
    )

    # Discover new errors
    service.discover_and_record_errors()

    # Attempt fix on all unfixed errors
    unfixed = error_repo.get_unfixed_errors()
    for err in unfixed:
        print(f"Attempting to fix error {err.id} in {err.test_file}:{err.test_function}")
        success = service.attempt_fix(err.id)
        if success:
            print(f"Error {err.id} fixed!")
        else:
            print(f"Failed to fix error {err.id}")

if __name__ == "__main__":
    main()
```

---

### Next Steps

- **Add Tests**: Unit tests for domain models, application services, and repositories.
- **Robust Error Analysis**: Improve parsing logic to handle real pytest output.
- **Real AI Integration**: Implement `AIManager` to communicate with OpenAI or a local LLM.
- **Enhanced Verification**: Capture test output logs, enable incremental verification, and implement more robust revert strategies.
- **Event Handling**: Integrate event dispatchers or log all domain events as needed.
- **Configuration & Logging**: Integrate a configuration file or environment variables and a structured logging solution.

---

This setup is cleaner, better modularized, and follows best practices by combining a domain-driven structure with a clear separation of concerns. It enhances maintainability and extensibility, providing a solid foundation that can be refined and expanded as the project’s complexity grows.

---

## Visual Enhancements

To further enhance the readability and visual appeal of your Markdown document, consider the following tips:

- **Consistent Heading Levels**: Ensure that heading levels (`#`, `##`, `###`, etc.) are used consistently to represent the document structure.
- **Code Blocks**: Use triple backticks (\`\`\`) for code blocks with proper syntax highlighting by specifying the language (e.g., \`\`\`python).
- **Lists and Indentation**: Use bullet points or numbered lists to organize information clearly.
- **Bold and Italics**: Highlight key terms and important points using **bold** or *italics*.
- **Tables**: For comparing options or presenting structured data, use Markdown tables.
- **Spacing**: Add blank lines between sections and elements to prevent clutter and improve readability.