# Domain-Driven Design Concepts Guide for pytest-fixer

## Introduction

This guide explains the Domain-Driven Design (DDD) concepts used in `pytest-fixer`, which combines test generation and test fixing capabilities. Each concept is illustrated with concrete examples from our domains.

## Table of Contents

1. [Core DDD Concepts](#core-ddd-concepts)
   - [Ubiquitous Language](#ubiquitous-language)
   - [Bounded Contexts](#bounded-contexts)
   - [Aggregates](#aggregates)
   - [Entities](#entities)
   - [Value Objects](#value-objects)
   - [Domain Services](#domain-services)
   - [Repositories](#repositories)
   - [Domain Events](#domain-events)
   - [Application Services](#application-services)
2. [Common DDD Patterns](#common-ddd-patterns)
3. [Best Practices](#best-practices)

## Core DDD Concepts

### Ubiquitous Language

The shared language includes terms from both test generation and fixing:

**Test Generation Domain:**
- **Test Case**: A generated test function/method
- **Generation Strategy**: Method for creating tests (Hypothesis, Fabric, Pynguin)
- **Test Coverage**: Percentage of code covered by tests
- **Property Test**: Test that verifies properties/invariants

**Branch Fixing Domain:**
- **Test Error**: A failing pytest test that needs fixing
- **Fix Attempt**: A single try at fixing a test error
- **Fix Branch**: Git branch containing test fixes
- **Verification**: Checking if a fix works

### Bounded Contexts

We have two primary bounded contexts with shared infrastructure:

1. **Test Generation Context**
   ```python
   class TestGenerationContext:
       """Handles test creation and coverage analysis"""
       def generate_tests(self, source_code: Path) -> List[TestCase]:
           pass
       
       def measure_coverage(self, tests: List[TestCase]) -> float:
           pass
   ```

2. **Branch Fixing Context**
   ```python
   class BranchFixingContext:
       """Handles fixing failing tests through branches"""
       def fix_error(self, error: TestError) -> bool:
           pass
           
       def create_fix_branch(self, error: TestError) -> str:
           pass
   ```

3. **Shared Infrastructure**
   ```python
   class SharedInfrastructure:
       """Components used by both contexts"""
       test_runner: TestRunner
       git_manager: GitManager
       ai_service: AIService
   ```

### Aggregates

#### Test Generation Aggregates:
```python
@dataclass
class TestSuite:  # Aggregate Root
    id: UUID
    source_file: Path
    test_cases: List[TestCase]
    coverage: float
    generation_attempts: List[GenerationAttempt]
    
    def add_test_case(self, test: TestCase) -> None:
        self.test_cases.append(test)
        self.update_coverage()
```

#### Branch Fixing Aggregates:
```python
@dataclass
class FixSession:  # Aggregate Root
    id: UUID
    error: TestError
    fix_branch: str
    attempts: List[FixAttempt]
    status: str
    
    def attempt_fix(self, temperature: float) -> FixAttempt:
        attempt = FixAttempt(error_id=self.error.id, temperature=temperature)
        self.attempts.append(attempt)
        return attempt
```

### Entities

#### Test Generation Entities:
```python
@dataclass
class TestCase:
    id: UUID
    name: str
    source_code: str
    coverage_contribution: float
    generation_strategy: str

@dataclass
class GenerationAttempt:
    id: UUID
    strategy: str
    result: Optional[TestCase]
```

#### Branch Fixing Entities:
```python
@dataclass
class FixAttempt:
    id: UUID
    error_id: UUID
    temperature: float
    changes: Optional[CodeChanges]
    status: str
```

### Value Objects

```python
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

@dataclass(frozen=True)
class CodeChanges:
    original: str
    modified: str
    description: str
```

### Domain Services

#### Test Generation Services:
```python
class TestGenerationService:
    """Coordinates test generation strategies"""
    def generate_suite(self, source: Path) -> TestSuite:
        pass

class CoverageAnalysisService:
    """Analyzes test coverage"""
    def analyze_coverage(self, tests: List[TestCase]) -> float:
        pass
```

#### Branch Fixing Services:
```python
class ErrorAnalysisService:
    """Analyzes test failures"""
    def analyze_error(self, test_output: str) -> TestError:
        pass

class FixGenerationService:
    """Generates fixes using AI"""
    def generate_fix(self, error: TestError) -> Optional[CodeChanges]:
        pass
```

### Repositories

```python
class TestSuiteRepository(Protocol):
    """Stores generated test suites"""
    def save(self, suite: TestSuite) -> None:
        pass
    
    def get_by_file(self, file_path: Path) -> Optional[TestSuite]:
        pass

class FixSessionRepository(Protocol):
    """Stores fix sessions"""
    def save(self, session: FixSession) -> None:
        pass
    
    def get_active_sessions(self) -> List[FixSession]:
        pass
```

### Domain Events

```python
@dataclass
class TestGenerationCompleted:
    suite_id: UUID
    coverage: float
    timestamp: datetime

@dataclass
class FixAttemptStarted:
    session_id: UUID
    attempt_id: UUID
    timestamp: datetime

@dataclass
class FixVerified:
    session_id: UUID
    attempt_id: UUID
    success: bool
```

### Application Services

```python
class TestGenerationApplicationService:
    """Coordinates test generation workflow"""
    def __init__(
        self,
        test_gen: TestGenerationService,
        coverage: CoverageAnalysisService,
        repo: TestSuiteRepository,
        event_pub: EventPublisher
    ):
        pass

class FixingApplicationService:
    """Coordinates test fixing workflow"""
    def __init__(
        self,
        error_analysis: ErrorAnalysisService,
        fix_gen: FixGenerationService,
        repo: FixSessionRepository,
        event_pub: EventPublisher
    ):
        pass
```

## Integration Points

The contexts interact through:

1. **Shared Infrastructure**
   - Test running capabilities
   - Git operations
   - AI services

2. **Event Communication**
   - Test generation events can trigger fix attempts
   - Fix verification can trigger new test generation

3. **Common Value Objects**
   - Code locations
   - File paths
   - Error details

## Best Practices

1. **Keep Contexts Separate**
   - Clear boundaries between generation and fixing
   - Shared infrastructure through interfaces
   - Independent deployability

2. **Rich Domain Models**
   - Business logic in entities/aggregates
   - Immutable value objects
   - Clear lifecycle management

3. **Event-Driven Integration**
   - Loose coupling between contexts
   - Async operations where possible
   - Clear event documentation

4. **Testing Strategies**
   - Unit tests per context
   - Integration tests for workflows
   - System tests for end-to-end scenarios