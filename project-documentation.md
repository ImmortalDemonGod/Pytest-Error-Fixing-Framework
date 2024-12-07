# pytest-fixer Documentation

## Overview

pytest-fixer is an AI-powered tool that automatically identifies and fixes failing pytest tests in Python projects. It combines OpenAI's GPT models with intelligent error analysis and Git-based change management to provide a robust testing automation solution.

## Core Architecture

### Component Structure
1. **PytestErrorFixer**
   - Main orchestrator coordinating all components
   - Manages execution flow and state
   - Handles component initialization and cleanup

2. **TestRunner**
   - Discovers test files matching `test_*.py`
   - Executes individual tests or full suites
   - Captures stdout, stderr, and results
   - Provides standardized test result objects

3. **ErrorProcessor**
   - Parses pytest output into structured data
   - Handles test failures, collection errors, runtime errors
   - Extracts context and error details
   - Manages error state through fixing process

4. **DependencyMapper**
   - Analyzes imports and code references
   - Maps relationships between test and source files
   - Handles both direct and convention-based mappings
   - Supports relative and absolute imports

5. **AIManager**
   - Manages OpenAI API interactions
   - Implements temperature-based retry strategy
   - Constructs and manages prompts
   - Parses AI responses into actionable changes

6. **StateManager**
   - Tracks execution progress
   - Manages checkpoints and recovery
   - Coordinates with LogStore
   - Handles session state

7. **ChangeHandler**
   - Applies code modifications
   - Manages change verification
   - Handles reversions
   - Preserves logs during operations

### Component Interaction
```
TestRunner → ErrorProcessor → AIManager
     ↑            ↓             ↓
StateManager ← ChangeHandler ← LogStore
     ↓            ↑
DependencyMapper → PytestErrorFixer
```

## Key Features

### Test Processing
- Automatic test discovery with `.venv` exclusion
- Individual test function or file execution
- Output and error capture
- Dependency analysis and mapping
- Comprehensive error detail extraction

### AI Integration
- OpenAI GPT model integration
- Smart retry mechanism:
  ```python
  initial_temperature = 0.4
  temperature_increment = 0.1
  max_retries = 3
  ```
- Context-aware prompt construction:
  - Error details and stack traces
  - Previous attempt history
  - Code context and dependencies
  - Test output and logs

### Interactive Mode
Four operational modes:
- `DISABLED`: Fully automated operation
- `ON_FAILURE`: Interactive after failed attempts
- `ALWAYS`: Interactive for all fixes
- `MANUAL`: Only when explicitly triggered

Interactive commands:
```
show    - Display current error and changes
edit    - Edit changes in default editor
apply   - Apply and test changes
retry   - Retry with higher temperature
prompt  - Modify AI prompt
diff    - Show git differences
history - View change history
quit    - Exit without changes
```

### State Management
- Session state tracking
- Checkpoint creation and restoration
- Error state progression monitoring
- Change history tracking
- Log persistence

### Git Integration
- Isolated fix branches
- Base automation branch ("pytest-aider-automation")
- Change management and reversion
- Branch lifecycle handling

## Setup

### Requirements
```
Python 3.8+
Git
OpenAI API Key
pytest
```

### Installation
```bash
git clone https://github.com/your-repo/pytest-fixer.git
cd pytest-fixer
pip install -r requirements.txt
```

### Configuration
```env
OPENAI_API_KEY=your-api-key
MODEL_NAME=gpt-4o-mini
INITIAL_TEMPERATURE=0.4
TEMPERATURE_INCREMENT=0.1
MAX_RETRIES=3
```

### Usage
```bash
python -m pytest_fixer.main /path/to/project [options]

Options:
  --initial-temperature FLOAT  Initial AI temperature (default: 0.4)
  --temperature-increment FLOAT Temperature increase (default: 0.1)
  --max-retries INT          Maximum fix attempts (default: 3)
  --model STRING            AI model name (default: gpt-4o-mini)
  --debug                   Enable debug logging
  --manual-fix             Enable manual fix mode
```

## Error Handling

### Error Propagation
1. Component-level errors:
   - Each component handles domain-specific errors
   - Errors are logged and propagated up
   - State is preserved when possible

2. System-level errors:
   - Managed by PytestErrorFixer
   - Trigger session cleanup
   - Preserve logs and state

### Recovery Mechanisms
1. State Recovery:
   - Checkpoint-based recovery
   - Log-based state reconstruction
   - Branch restoration

2. Change Recovery:
   - Git-based change reversion
   - Log preservation
   - State rollback

## Known Limitations

### Technical Limitations
- Git integration assumes "main" branch
- No parallel test execution
- Basic pytest plugin support
- OpenAI-specific AI integration
- Limited session recovery

### Operational Limitations
- Single branch workflow
- Basic prompt management
- No learning from history
- Limited error pattern recognition

## Best Practices

### Operation
1. Version Control:
   - Clean working directory
   - Dedicated fix branches
   - Review before merging

2. Configuration:
   - Start with default temperatures
   - Enable debug for investigation
   - Use interactive mode for complex fixes

3. Monitoring:
   - Watch progress logs
   - Review generated fixes
   - Monitor state changes

### Troubleshooting
1. AI Issues:
   - Verify API key
   - Check model availability
   - Review prompt formatting

2. Git Issues:
   - Clean working directory
   - Check permissions
   - Verify branch state

3. Test Issues:
   - Verify pytest setup
   - Check test discovery
   - Review dependencies

## Implementation Details

### State Persistence
```python
@dataclass
class CheckpointState:
    timestamp: str
    current_error: Optional[Dict[str, Any]]
    current_branch: Optional[str]
    completed_files: List[str]
    failed_files: List[str]
    in_progress: bool
    current_status: FixStatus
```

### Error Processing
```python
@dataclass
class RawError:
    test_file: str
    function: str
    error_type: str
    error_details: str
    line_number: str
    code_snippet: str
    captured_output: str
    captured_log: str
```

### Change Management
```python
@dataclass
class ChangeRecord:
    changes: str
    timestamp: str
    branch: Optional[str]
    reverted: bool
    error: Optional[str]
```

## Support

For assistance:
1. Enable debug logging
2. Check logs in ~/.pytest_fixer/logs
3. Include with issues:
   - Error details
   - Log files
   - Steps to reproduce
   - Configuration details

# Domain-Driven Design Concepts Guide for pytest-fixer

## Introduction
This guide explains the Domain-Driven Design (DDD) concepts you need to understand to rebuild pytest-fixer. Each concept is explained with concrete examples from our domain.

## Core DDD Concepts

### 1. Ubiquitous Language
The shared language between developers and domain experts. For pytest-fixer, this includes:

- **Test Error**: A failing pytest test that needs fixing
- **Fix Attempt**: A single try at fixing a test error
- **Fix Generation**: The process of creating a fix
- **Verification**: Checking if a fix works
- **Code Changes**: Modifications made to fix an error

Why it matters: Using consistent terminology prevents confusion and misunderstandings. For example, we always say "fix attempt" rather than "try" or "fix iteration".

### 2. Bounded Contexts
Separate domains with their own models and rules. In pytest-fixer:

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

### 3. Aggregates
Clusters of related objects treated as a single unit. Key aggregates in pytest-fixer:

1. **TestError Aggregate**
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

2. **FixSession Aggregate**
```python
class FixSession:  # Aggregate Root
    id: UUID
    error: TestError
    current_attempt: Optional[FixAttempt]
    attempts: List[FixAttempt]
    status: FixSessionStatus
```

Rules for Aggregates:
- Only reference other aggregates by ID
- Maintain consistency boundaries
- Handle transactional requirements

### 4. Entities
Objects with identity that changes over time. Key entities:

1. **FixAttempt**
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

2. **TestCase**
```python
@dataclass
class TestCase:
    id: UUID
    file_path: Path
    function_name: str
    source_code: str
```

Entity characteristics:
- Have unique identity
- Mutable over time
- Track state changes
- Maintain history

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

Value Object rules:
- Immutable
- No identity
- Equality based on attributes
- Self-validating

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

When to use Services:
- Operation spans multiple entities
- Complex domain logic
- External system integration

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

Repository principles:
- One repository per aggregate
- Hide storage details
- Return fully-loaded aggregates
- Handle persistence concerns

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

When to use Events:
- State changes matter to other contexts
- Need to maintain audit trail
- Cross-context communication needed

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

Application Service responsibilities:
- Use case orchestration
- Transaction management
- Event publishing
- Error handling

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

### 2. Specification Pattern
Express complex queries or validations:

```python
class FixableErrorSpecification:
    def is_satisfied_by(self, error: TestError) -> bool:
        """Check if error can be fixed"""
```

### 3. Anti-Corruption Layer
Protect domain model from external systems:

```python
class AIServiceAdapter:
    """Adapt AI service responses to our domain model"""
    def adapt_response(self, ai_response: dict) -> CodeChanges:
        """Convert AI response to domain model"""
```

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

## Practical Tips for pytest-fixer

1. Start with core domain model (TestError)
2. Add behavior incrementally
3. Use events for tracking
4. Keep interfaces clean
5. Test domain logic thoroughly
==========
🧙🏾‍♂️: [aligning on my goal]  
[emoji]: Below is a cohesive, from-scratch rewrite that combines the strengths of the previous approaches into a cleaner, domain-driven, and modular architecture. It clarifies domain logic, separates concerns, and provides a strong foundation for future extensions. This blueprint focuses on the core functionality: discovering test errors, generating fixes using AI (via a hypothetical `AIManager` or `Coder`), applying changes, verifying them, and persisting state. It uses domain-driven design patterns, a clear layering approach, and sets up a workable starting point.

### Key Design Principles

1. **Domain-Driven Design (DDD)**:  
   - **Domain Model**: Defines `TestError`, `FixAttempt`, `ErrorDetails`, and related entities as the heart of the domain.
   - **Value Objects**: `CodeLocation`, `CodeChanges` are immutable and model specific domain concepts clearly.
   - **Repositories**: Abstract away persistence details behind interfaces.
   - **Domain Services**: Provide business logic that doesn't belong inside entities.

2. **Clean Architecture Layers**:  
   - **Domain (Core)**: Entities, Value Objects, Domain Services, Repositories Interfaces.
   - **Application**: Orchestrates the use cases, coordinates domain objects, and triggers domain services.
   - **Infrastructure**: Implementation details like Git-based repository, AI integration, running `pytest`, file I/O.

3. **Events & Extensibility**:  
   Although we define domain events, we keep them minimal for this starting point. In a more complex scenario, these events can be published to other interested parties (e.g., logging, analytics, asynchronous pipelines).

4. **Testing & Configuration**:  
   Testing can be added incrementally. Configuration can be handled through environment variables or a config file. The code below includes some placeholders for integration points (like `AIManager`, `TestRunner`, `VCSManager`) that you'd implement concretely later.

### Project Structure

```
pytest_fixer/
├─ domain/
│  ├─ models.py        # Entities, Value Objects
│  ├─ events.py        # Domain events
│  ├─ repositories.py  # Repository interfaces
│  ├─ services.py      # Domain services (e.g. ErrorAnalysis)
│  └─ __init__.py
├─ application/
│  ├─ usecases.py      # Application services (Use cases)
│  ├─ dto.py           # Data Transfer Objects if needed
│  └─ __init__.py
├─ infrastructure/
│  ├─ ai_manager.py     # AI integration (fix generation)
│  ├─ test_runner.py    # Pytest integration
│  ├─ vcs_manager.py    # Git operations
│  ├─ repository_impl.py# Git or file-based repository implementation
│  ├─ change_applier.py # Applying and reverting code changes
│  └─ __init__.py
└─ main.py
```

---

### Detailed Implementation

**`domain/models.py`**:
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

**`domain/events.py`** (domain events if needed):
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

**`domain/repositories.py`**:
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

**`domain/services.py`**:
```python
import re
from pathlib import Path
from typing import Optional
from .models import ErrorDetails, TestError, CodeLocation

class ErrorAnalysisService:
    def analyze_errors(self, test_output: str) -> Optional[List[TestError]]:
        # Basic regex-based approach to find failing tests:
        # This is a placeholder. Real logic might integrate directly with pytest APIs.
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

**`application/usecases.py`**:
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
        errors = analysis_service.analyze_errors(stdout+stderr)
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

**`infrastructure/ai_manager.py`**:
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

**`infrastructure/test_runner.py`**:
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

**`infrastructure/vcs_manager.py`**:
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

**`infrastructure/change_applier.py`**:
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

**`infrastructure/repository_impl.py`**:
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

**`main.py`** (Example entry point):
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
- **Enhanced Verification**: Consider capturing test output logs, enabling incremental verification, and more robust revert strategies.
- **Event Handling**: If needed, integrate event dispatchers or log all domain events.
- **Configuration & Logging**: Integrate a configuration file or environment variables and a structured logging solution.

This setup is cleaner, better modularized, and follows best practices combining the domain-driven structure with a clear separation of concerns, making it more maintainable and extensible. It provides a solid starting point that can be refined and expanded as the project’s complexity grows.
==========
🧙🏾‍♂️: [aligning on my goal]
[emoji]: Let’s adopt a fully test-driven development (TDD) approach. This means we define our desired behavior and outcomes as tests first—no production code will be written until we have tests describing what we want.

Below is an outline of how we can start from scratch, writing tests for the core functionality of the pytest-fixer project. After we agree on and finalize these tests (the contract of what we want), we would then proceed to implement the code that makes these tests pass.

Key Principles:
	1.	Test-Driven Development (TDD):
	•	Write tests that define the desired functionality and behavior.
	•	Run tests and see them fail.
	•	Write just enough code to make tests pass.
	•	Refactor as needed, keeping tests green.
	2.	Domain-Driven & Layered Architecture:
As previously discussed, we want a clean architecture (domain, application, infrastructure), but let’s start simple. Our initial tests will focus on core domain logic and application-level use cases. We’ll add complexity as we go.
	3.	Incremental Approach:
Start with the simplest domain behaviors (managing TestError aggregates, fix attempts) and move outward to application services (attempting a fix) and then to integration with AIManager, TestRunner, and ChangeApplier. Each step: write tests first, then code.

What We Want to Achieve

Core User Story:
	•	As a developer, I want the pytest-fixer tool to identify test failures from pytest output, store them, and attempt to fix them by:
	1.	Generating fixes with AI.
	2.	Applying changes to the code.
	3.	Verifying if the fix resolves the test failure.
	4.	If it fails, revert changes and try again with increased AI “temperature”.
	5.	If it succeeds, mark the error as fixed.

We break this story into smaller, testable chunks.

Project Structure

We’ll plan tests first. A suggested structure:

pytest_fixer/
├─ tests/
│  ├─ test_domain_models.py
│  ├─ test_error_analysis_service.py
│  ├─ test_application_usecases.py
│  ├─ test_integration.py
│  └─ __init__.py
└─ src/
   ├─ domain/
   ├─ application/
   ├─ infrastructure/
   └─ ...

We place all tests in tests/ and our future code in src/. Right now, we’ll only write tests. No code in src/ yet.

Step 1: Domain Model Tests

Goal: Ensure our TestError and FixAttempt domain models behave correctly. We want to confirm that we can create TestError aggregates, add fix attempts, and mark them as fixed or failed.

tests/test_domain_models.py:

import unittest
from uuid import UUID

class TestDomainModels(unittest.TestCase):
    def test_create_test_error(self):
        # We want to create a TestError with file, function, error details
        # We expect an unfixed status initially
        # Pseudocode usage:
        # error = TestError(
        #     test_file=Path("tests/test_example.py"),
        #     test_function="test_something",
        #     error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        # )
        # self.assertEqual(error.status, "unfixed")
        # self.assertEqual(error.test_function, "test_something")
        # self.assertIsNotNone(error.id)
        
        # Initially, this test will fail because we have no such classes implemented.
        # We'll just write the asserts we want:
        from pathlib import Path
        from src.domain.models import TestError, ErrorDetails

        error = TestError(
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )
        
        self.assertEqual(error.status, "unfixed")
        self.assertEqual(error.test_function, "test_something")
        self.assertTrue(isinstance(error.id, UUID))
        self.assertEqual(error.error_details.error_type, "AssertionError")
        self.assertEqual(error.error_details.message, "Expected X but got Y")

    def test_start_fix_attempt(self):
        # We want to start a fix attempt with a given temperature and see that attempt recorded
        from pathlib import Path
        from src.domain.models import TestError, ErrorDetails

        error = TestError(
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )

        attempt = error.start_fix_attempt(0.4)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(attempt.temperature, 0.4)
        self.assertIn(attempt, error.fix_attempts)
        self.assertEqual(error.status, "unfixed")  # still unfixed until success

    def test_mark_fixed(self):
        # After a successful fix, error should be "fixed"
        from pathlib import Path
        from src.domain.models import TestError, ErrorDetails

        error = TestError(
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )
        attempt = error.start_fix_attempt(0.4)
        # Pseudocode for success marking:
        # error.mark_fixed(attempt)
        # self.assertEqual(error.status, "fixed")
        # self.assertEqual(attempt.status, "success")

        error.mark_fixed(attempt)
        self.assertEqual(error.status, "fixed")
        self.assertEqual(attempt.status, "success")

    def test_mark_attempt_failed(self):
        from pathlib import Path
        from src.domain.models import TestError, ErrorDetails

        error = TestError(
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )
        attempt = error.start_fix_attempt(0.4)
        
        # If the attempt fails:
        error.mark_attempt_failed(attempt)
        self.assertEqual(attempt.status, "failed")
        self.assertEqual(error.status, "unfixed")  # still unfixed after a failed attempt

Result: Running these tests now would fail since src.domain.models doesn’t exist.

Step 2: Error Analysis Service Tests

We want a service that, given pytest output, returns a list of TestError objects. Let’s define a minimal test to ensure we can parse a known failing test from a snippet of pytest output.

tests/test_error_analysis_service.py:

import unittest

class TestErrorAnalysisService(unittest.TestCase):
    def test_analyze_simple_failure(self):
        # Given a simplified pytest output snippet:
        pytest_output = """
        tests/test_example.py::test_something FAILED AssertionError: Expected X but got Y
        -----------------------------
        stack trace details here
        """

        # We expect the service to return a list with one TestError
        from src.domain.services import ErrorAnalysisService
        from pathlib import Path
        service = ErrorAnalysisService()

        errors = service.analyze_errors(pytest_output)
        self.assertIsNotNone(errors)
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.test_file, Path("tests/test_example.py"))
        self.assertEqual(error.test_function, "test_something")
        self.assertEqual(error.error_details.error_type, "AssertionError:")
        self.assertIn("Expected X but got Y", error.error_details.message)

This test defines what we expect from ErrorAnalysisService, no code for it yet.

Step 3: Application Use Cases Tests

Now we define a test for the main use case: attempting to fix an unfixed error using a TestFixingService in the application layer. This service will:
	•	Retrieve an error by ID.
	•	Attempt to generate a fix using AIManager.
	•	Apply changes, verify fix using TestRunner.
	•	If success, mark fixed and commit with VCSManager. If fail, revert changes and retry until max_retries is reached.

We mock dependencies (AIManager, TestRunner, VCSManager, ChangeApplier) since we focus on logic rather than actual integration.

tests/test_application_usecases.py:

import unittest
from unittest.mock import MagicMock
from uuid import uuid4

class TestApplicationUseCases(unittest.TestCase):
    def test_attempt_fix_success_on_first_try(self):
        # Setup a mock error repository with one unfixed error
        from src.domain.models import TestError, ErrorDetails
        from pathlib import Path
        error_id = uuid4()
        test_error = TestError(
            id=error_id,
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = test_error
        mock_repo.get_unfixed_errors.return_value = [test_error]

        # Mock AIManager to always return a CodeChanges object:
        from src.domain.models import CodeChanges
        mock_ai = MagicMock()
        mock_ai.generate_fix.return_value = CodeChanges(original="bug", modified="fix")

        # Mock TestRunner: run_test_and_check returns True on first attempt
        mock_test_runner = MagicMock()
        mock_test_runner.run_test_and_check.return_value = True

        # Mock VCSManager: just commit without error
        mock_vcs = MagicMock()

        # Mock ChangeApplier: apply and revert do nothing
        mock_applier = MagicMock()

        # Now test the service
        from src.application.usecases import TestFixingService
        service = TestFixingService(
            error_repo=mock_repo,
            ai_manager=mock_ai,
            test_runner=mock_test_runner,
            vcs_manager=mock_vcs,
            change_applier=mock_applier,
            initial_temp=0.4,
            temp_increment=0.1,
            max_retries=3
        )

        # Attempt fix
        success = service.attempt_fix(error_id)
        self.assertTrue(success)
        self.assertEqual(test_error.status, "fixed")
        # ensure commit was called
        mock_vcs.commit_changes.assert_called_once()
        # ensure test was run
        mock_test_runner.run_test_and_check.assert_called_once_with(test_error.test_file, test_error.test_function)
        # ensure AI fix generated
        mock_ai.generate_fix.assert_called_once_with(test_error, 0.4)

    def test_attempt_fix_failure_all_retries(self):
        # If the fix never passes verification, we end up returning False
        from src.domain.models import TestError, ErrorDetails
        from pathlib import Path
        error_id = uuid4()
        test_error = TestError(
            id=error_id,
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = test_error

        # AI returns changes each time, but test never passes:
        from src.domain.models import CodeChanges
        mock_ai = MagicMock()
        mock_ai.generate_fix.return_value = CodeChanges(original="bug", modified="fix")

        mock_test_runner = MagicMock()
        mock_test_runner.run_test_and_check.return_value = False  # never passes

        mock_vcs = MagicMock()
        mock_applier = MagicMock()

        from src.application.usecases import TestFixingService
        service = TestFixingService(
            error_repo=mock_repo,
            ai_manager=mock_ai,
            test_runner=mock_test_runner,
            vcs_manager=mock_vcs,
            change_applier=mock_applier,
            initial_temp=0.4,
            temp_increment=0.1,
            max_retries=2
        )

        success = service.attempt_fix(error_id)
        self.assertFalse(success)
        self.assertEqual(test_error.status, "unfixed")
        # Verifications:
        # AI generate fix should be called twice (max_retries=2)
        self.assertEqual(mock_ai.generate_fix.call_count, 2)
        # test_runner also called twice
        self.assertEqual(mock_test_runner.run_test_and_check.call_count, 2)
        # vcs commit never called
        mock_vcs.commit_changes.assert_not_called()
        # after each failure revert should be called
        self.assertEqual(mock_applier.revert.call_count, 2)

Step 4: Integration Test (Optional at this Stage)

We could write a high-level test simulating the whole pipeline once we have some code, but for now, these unit tests are enough to guide our initial implementation.

Summary of Next Steps

We have defined tests that describe the desired behavior of our domain models, error analysis, and core application use cases. According to TDD, our next step would be:
	1.	Run these tests now: They will fail because none of the referenced classes or logic exists.
	2.	Implement the minimal code in src/ needed to make these tests pass, step by step.
	3.	Refactor the code once tests are passing.

We have a clear contract defined by tests, ensuring we only build what’s required and verifying functionality as we proceed.

This test suite and approach should serve as a strong starting point for a TDD-driven rewrite of the pytest-fixer tool’s core functionality.
==========