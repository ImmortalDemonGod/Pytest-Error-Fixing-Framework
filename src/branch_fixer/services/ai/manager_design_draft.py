from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import marvin
from marvin.beta.assistants import Assistant, Thread
from branch_fixer.services.pytest.error_processor import parse_pytest_errors
from branch_fixer.services.git.branch_manager import BranchManager
from branch_fixer.services.git.pr_manager import PRManager
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.storage.state_manager import StateManager
from branch_fixer.storage.recovery import RecoveryManager
from branch_fixer.storage.session_store import SessionStore
from pydantic import BaseModel, Field
import asyncio

# Change Operation Types
class ChangeAction(str, Enum):
    """Types of code changes at line level"""
    ADD = "add"
    EDIT = "edit"
    REMOVE = "remove"

class LineChange(BaseModel):
    """Represents a single line-level change"""
    action: ChangeAction
    line_number: int
    content: str = ""  # Empty for REMOVE
    indent_level: Optional[int] = None

class FileChange(BaseModel):
    """Represents changes to a single file"""
    file_path: str
    changes: List[LineChange]
    backup_path: Optional[str] = None

# Test Infrastructure
class TestResult(BaseModel):
    """Result of running a single test"""
    test_name: str
    passed: bool
    duration: float
    output: str
    error: Optional[str] = None

class TestSuite(BaseModel):
    """Collection of tests to run"""
    test_files: List[str]
    test_names: Optional[List[str]] = None
    timeout: int = 60
    env_vars: Dict[str, str] = Field(default_factory=dict)

# Data Models
class TestErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TestError(BaseModel):
    """Structured representation of a test error"""
    message: str = Field(..., description="The error message")
    stack_trace: str = Field(..., description="Full stack trace")
    file_path: str = Field(..., description="Path to the failing test file")
    test_name: str = Field(..., description="Name of the failing test")
    severity: TestErrorSeverity
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class CodeChanges(BaseModel):
    """Represents code changes to fix a test error.
    
    Handles both high-level code representation and specific line changes."""
    original_code: str = Field(..., description="Original failing code")
    modified_code: str = Field(..., description="Modified code that fixes the error")
    file_changes: Dict[str, List[Tuple[ChangeAction, int, str, Optional[int]]]] = Field(default_factory=dict, description="Specific line-level changes")
    explanation: str = Field(..., description="Explanation of the changes made")
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Confidence score for the fix"
    )

class FixAttempt(BaseModel):
    """Record of an attempt to fix a test error"""
    timestamp: datetime
    error: TestError
    changes: CodeChanges
    temperature: float
    success: bool = False
    validation_errors: List[str] = Field(default_factory=list)

class ManagerState(BaseModel):
    """State tracking for AIManager"""
    fix_attempts: List[FixAttempt] = Field(default_factory=list)
    current_thread_id: Optional[str] = None
    total_attempts: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of fix attempts"""
        if not self.fix_attempts:
            return 0.0
        return len([a for a in self.fix_attempts if a.success]) / len(self.fix_attempts)

# Custom Exceptions
class AIManagerError(Exception):
    """Base exception for AIManager errors"""
    pass

class FileOperationError(AIManagerError):
    """Error during file operations"""
    pass

class TestExecutionError(AIManagerError):
    """Error running tests"""
    pass

class BackupError(AIManagerError):
    """Error managing backups"""
    pass

class PromptGenerationError(AIManagerError):
    """Error generating prompt from test error"""
    pass

class CompletionError(AIManagerError):
    """Error getting completion from LLM"""
    pass

class ValidationError(AIManagerError):
    """Error validating generated fix"""
    pass

# Main Implementation
# File Operations
class FileManager:
    """Manages file operations with backup and rollback support"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.backup_dir = self.base_dir / ".ai_manager_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    async def create_backup(self, file_path: str) -> str:
        """Create backup of a file before modification"""
        src = self.base_dir / file_path
        if not src.exists():
            raise FileOperationError(f"File not found: {file_path}")
            
        backup_name = f"{src.name}.{datetime.now().isoformat()}.bak"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(src, backup_path)
            return str(backup_path)
        except Exception as e:
            raise BackupError(f"Failed to create backup: {str(e)}")
            
    async def apply_changes(self, changes: List[FileChange]) -> None:
        """Apply changes atomically with pre-validation, backup, and partial rollback"""
        successful_changes = []
        
        # Add pre-validation
        for change in changes:
            if not await self._validate_file_operation(change):
                raise ValidationError(f"Invalid change for file: {change.file_path}")
        
        try:
            for change in changes:
                backup_path = await self.create_backup(change.file_path)
                change.backup_path = backup_path
                await self._apply_file_changes(change)
                successful_changes.append(change)
                
        except Exception as e:
            # Rollback only successful changes
            if successful_changes:
                await self._rollback_changes({
                    change.file_path: change.backup_path 
                    for change in successful_changes
                })
            raise FileOperationError(f"Partial failure applying changes: {str(e)}")
                
    async def _apply_file_changes(self, change: FileChange) -> None:
        """Apply changes to a single file"""
        file_path = self.base_dir / change.file_path
        
        with open(file_path) as f:
            lines = f.readlines()
            
        # Sort changes in reverse order
        sorted_changes = sorted(
            change.changes,
            key=lambda x: x.line_number,
            reverse=True
        )
        
        # Apply changes
        for line_change in sorted_changes:
            if line_change.action == ChangeAction.REMOVE:
                del lines[line_change.line_number - 1]
            elif line_change.action == ChangeAction.EDIT:
                lines[line_change.line_number - 1] = line_change.content
            elif line_change.action == ChangeAction.ADD:
                lines.insert(line_change.line_number, line_change.content)
                
        # Write changes
        with open(file_path, 'w') as f:
            f.writelines(lines)
            
    async def _rollback_changes(self, backups: Dict[str, str]) -> None:
        """Rollback changes using backups"""
        for file_path, backup_path in backups.items():
            try:
                shutil.copy2(backup_path, self.base_dir / file_path)
            except Exception as e:
                raise BackupError(f"Failed to rollback {file_path}: {str(e)}")
                
    async def _validate_file_operation(self, change: FileChange) -> bool:
        """
        Placeholder for file operation validation logic.
        Implement necessary validation checks here.
        """
        # Example validation: Ensure that for EDIT and REMOVE, the file exists
        file_exists = (self.base_dir / change.file_path).exists()
        if not file_exists and any(
            c.action in {ChangeAction.EDIT, ChangeAction.REMOVE} for c in change.changes
        ):
            return False
        return True

# Test Infrastructure
# TODO: Intergate into our existing system
class TestRunner:
    """Manages test execution in isolated environment"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.test_env = os.environ.copy()
        
    async def setup_docker(self, image: str) -> None:
        """Setup Docker test environment"""
        cmd = ["docker", "pull", image]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise TestExecutionError(f"Failed to setup Docker: {str(e)}")
            
    async def run_tests(
        self,
        suite: TestSuite,
        timeout: Optional[int] = None
    ) -> List[TestResult]:
        """Run tests with timeout and environment isolation"""
        timeout = timeout or suite.timeout
        results = []
        
        for test_file in suite.test_files:
            cmd = ["python", "-m", "pytest", test_file, "-v"]
            if suite.test_names:
                cmd.extend(["-k", " or ".join(suite.test_names)])
                
            try:
                start_time = datetime.now()
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=suite.env_vars
                )
                
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), 
                    timeout=timeout
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                results.append(TestResult(
                    test_name=test_file,
                    passed=proc.returncode == 0,
                    duration=duration,
                    output=stdout.decode(),
                    error=stderr.decode() if stderr else None
                ))
                
            except asyncio.TimeoutError:
                results.append(TestResult(
                    test_name=test_file,
                    passed=False,
                    duration=timeout,
                    output="",
                    error="Test execution timed out"
                ))
                
            except Exception as e:
                results.append(TestResult(
                    test_name=test_file,
                    passed=False,
                    duration=0,
                    output="",
                    error=str(e)
                ))
                
        return results
        
    async def detect_flaky_tests(
        self,
        suite: TestSuite,
        runs: int = 3
    ) -> Set[str]:
        """Detect flaky tests by running multiple times"""
        flaky_tests = set()
        test_results = {test: [] for test in suite.test_names or []}
        
        for _ in range(runs):
            results = await self.run_tests(suite)
            for result in results:
                if result.test_name in test_results:
                    test_results[result.test_name].append(result.passed)
                    
        for test, outcomes in test_results.items():
            if len(set(outcomes)) > 1:  # Mix of pass/fail
                flaky_tests.add(test)
                
        return flaky_tests



class AIManager:
    """
    Manages AI interactions for generating and validating code fixes.
    
    Uses Marvin's Assistant API for high-level interactions and direct function
    calls for specialized tasks. Maintains state and history of all fix attempts.
    
    Combines:
    - Aider's test-driven approach
    - Senkovi's intent-based changes
    - Marvin's tool integration
    """
    def __init__(
        self, 
        base_dir: str,
        git_repo: GitRepository,
        state_manager: StateManager,
        recovery_manager: RecoveryManager,
        session_store: SessionStore,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        base_temperature: float = 0.4,
        max_attempts: int = 3,
        docker_image: Optional[str] = None,
    ):
        self.base_dir = Path(base_dir)
        self.model = model
        self.base_temperature = base_temperature
        self.max_attempts = max_attempts
        self.docker_image = docker_image
        self.state = ManagerState()
        
        # Initialize components
        self.file_manager = FileManager(base_dir)
        self.test_runner = TestRunner(base_dir)
        self.git_repo = git_repo
        self.state_manager = state_manager
        self.recovery_manager = recovery_manager
        self.session_store = session_store
        
        # Initialize assistant
        self.assistant = Assistant(
            name="CodeFixer",
            model=model,
            instructions="""
            You are an expert software engineer specialized in fixing test failures.
            Your role is to analyze test errors, understand the root cause, and propose
            minimal code changes that fix the issue while maintaining code quality.
            """,
            tools=[self._validate_syntax, self._check_style],
        )
        
        # Initialize thread
        self.thread = Thread()

    async def __aenter__(self):
        """Initialize resources when used as context manager"""
        if self.docker_image:
            await self.test_runner.setup_docker(self.docker_image)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources when exiting context"""
        if self.thread and self.thread.id:
            await self.thread.delete()

    @marvin.fn
    def _analyze_error(self, error: TestError) -> Dict[str, Any]:
        """
        Analyze a test error to determine root cause and potential fix strategies.
        Returns dict with analysis results including:
        - root_cause: str
        - fix_complexity: int (1-5)
        - suggested_approach: str
        """

    @marvin.fn
    def _generate_fix_prompt(self, 
        error: TestError,
        analysis: Dict[str, Any],
        intent: Optional[str] = None
    ) -> str:
        """
        Generate a detailed prompt for the LLM to fix the test error.
        Uses error details, analysis, and optional intent to create targeted instructions.
        """

    async def _validate_syntax(self, code: str) -> bool:
        """Validate Python syntax of proposed fix"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False

    @marvin.fn
    async def _check_style(self, code: str) -> Dict[str, Any]:
        """
        Check code style and quality of proposed fix.
        Returns dict with:
        - passes_pep8: bool
        - complexity_score: float
        - suggestions: List[str]
        """

    async def _validate_fix(self, changes: CodeChanges, error: TestError) -> bool:
        """
        Validate a proposed fix through multiple steps:
        1. Check syntax
        2. Verify style
        3. Run affected tests
        4. Check for regressions
        """
        # Use PytestRunner instead of custom validation
        test_suite = TestSuite(
            test_files=[error.file_path],
            test_names=[error.test_name],
            timeout=60
        )
        
        # Use existing runner
        results = await self.test_runner.run_tests(test_suite)
        
        # Parse results using error_processor
        if errors := parse_pytest_errors("\n".join([result.output for result in results])):
            # Test still failing
            return False
            
        return True

    def _get_affected_test_files(self, changes: CodeChanges) -> List[str]:
        """
        Determine which test files are affected by the given code changes.
        Implement logic to map code changes to relevant test files.
        """
        # Placeholder implementation
        # In a real scenario, this might analyze dependencies or use a test mapping
        return list(changes.file_changes.keys())

    async def _adapt_strategy(
        self,
        error: TestError,
        previous_attempt: Optional[FixAttempt],
        current_temp: float
    ) -> float:
        """Adapt strategy based on previous attempt"""
        if not previous_attempt:
            return self.base_temperature
            
        # If syntax/style failed, small temperature bump
        if any('syntax' in err or 'style' in err 
               for err in previous_attempt.validation_errors):
            return current_temp + 0.1
            
        # If tests failed, larger temperature change
        if any('test' in err for err in previous_attempt.validation_errors):
            return current_temp + 0.2
            
        # If completion error, try different strategy
        if previous_attempt.validation_errors and isinstance(previous_attempt.validation_errors[0], CompletionError):
            return self.base_temperature * 1.5

        return current_temp  # No change if none of the above conditions met

    async def _attempt_fix(
        self,
        error: TestError,
        temperature: float,
        intent: Optional[str] = None,
    ) -> CodeChanges:
        """Make a single attempt to fix the error"""
        try:
            # Analyze error
            analysis = self._analyze_error(error)
            
            # Generate targeted prompt
            prompt = self._generate_fix_prompt(error, analysis, intent)
            
            # Add to thread and run assistant
            await self.thread.add(prompt)
            await self.thread.run(self.assistant)
            
            # Get response and parse as CodeChanges
            messages = await self.thread.get_messages()
            response = messages[-1].content[0].text.value
            
            return marvin.cast(response, CodeChanges)
            
        except Exception as e:
            raise CompletionError(f"Error generating fix: {str(e)}") from e

    async def _handle_fix_attempt(self, error: TestError, attempt: int, fix: CodeChanges, changed_files: List[str]) -> bool:
        """Handle the fix attempt by managing Git operations"""
        branch_name = f"fix-{Path(error.file_path).stem}-{error.test_name}"
        await self.git_repo.branch_manager.create_fix_branch(branch_name)
        
        try:
            # Apply the fix
            await self.apply_fix(fix)
            
            # Create PR using PRManager
            await self.git_repo.pr_manager.create_pr(
                title=f"Fix {error.test_name}",
                description=f"Fixes {error.message}",
                branch_name=branch_name,
                modified_files=changed_files
            )
            return True
        except Exception as e:
            # Cleanup on failure
            await self.git_repo.branch_manager.cleanup_fix_branch(branch_name)
            raise AIManagerError(f"Failed to handle fix attempt: {str(e)}") from e

    async def generate_fix(
        self, 
        error: TestError,
        intent: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> CodeChanges:
        """
        Generate a fix for the given test error.
        
        Makes multiple attempts with adaptive temperature scaling if needed.
        Tracks all attempts and maintains state.
        
        Args:
            error: The test error to fix
            intent: Optional user intent to guide the fix
            temperature: Optional starting temperature (uses base_temperature if not provided)
        """
        # Create session state
        session = await self.state_manager.create_session(error)
        
        try:
            # Create recovery point
            recovery_point = await self.recovery_manager.create_checkpoint(
                session, 
                metadata={"temperature": temperature or self.base_temperature}
            )
            
            temperature = temperature or self.base_temperature
            attempt = 0
            
            for attempt in range(self.max_attempts):
                try:
                    # Update session state
                    await self.state_manager.transition_state(
                        session, 
                        "RUNNING"
                    )
                    
                    # Adapt temperature based on previous attempt
                    temperature = await self._adapt_strategy(
                        error,
                        self.state.fix_attempts[-1] if self.state.fix_attempts else None,
                        temperature
                    )
                    
                    # Generate fix
                    fix = await self._attempt_fix(error, temperature, intent)
                    
                    # Validate fix
                    is_valid = await self._validate_fix(fix, error)
                    
                    # Record attempt
                    self.state.fix_attempts.append(
                        FixAttempt(
                            timestamp=datetime.now(),
                            error=error,
                            changes=fix,
                            temperature=temperature,
                            success=is_valid,
                        )
                    )
                    
                    if is_valid:
                        # Handle Git operations
                        changed_files = list(fix.file_changes.keys())
                        await self._handle_fix_attempt(error, attempt, fix, changed_files)
                        return fix
                        
                except (CompletionError, ValidationError) as e:
                    # Record failed attempt
                    self.state.fix_attempts.append(
                        FixAttempt(
                            timestamp=datetime.now(),
                            error=error,
                            changes=CodeChanges(
                                original_code=error.context.get("code", ""),
                                modified_code="",
                                file_changes={},
                                explanation=str(e),
                                confidence_score=0.0,
                            ),
                            temperature=temperature,
                            success=False,
                            validation_errors=[str(e)],
                        )
                    )
                    
                    # Try to recover
                    if not await self.recovery_manager.handle_failure(e, session, {}):
                        raise
    
        finally:
            # Save session state
            await self.session_store.save_session(session)
    
        raise AIManagerError(
            f"Failed to generate valid fix after {self.max_attempts} attempts"
        )

    async def verify_fix(self, changes: CodeChanges, error: TestError) -> bool:
        """Verify a generated fix meets all requirements"""
        return await self._validate_fix(changes, error)
    
    async def apply_fix(self, changes: CodeChanges) -> None:
        """Apply a validated fix to the codebase"""
        try:
            # Convert CodeChanges to FileChange format
            file_changes = [
                FileChange(
                    file_path=file_path,
                    changes=[
                        LineChange(
                            action=action,
                            line_number=line_num,
                            content=content,
                            indent_level=indent
                        ) for action, line_num, content, indent in changes.file_changes.get(file_path, [])
                    ]
                ) for file_path in changes.file_changes
            ]
            
            # Use existing FileManager
            await self.file_manager.apply_changes(file_changes)
        except (FileOperationError, BackupError) as e:
            raise AIManagerError(f"Failed to apply fix: {str(e)}") from e
            
    async def run_tests(
        self,
        suite: TestSuite,
        check_flaky: bool = True
    ) -> Tuple[List[TestResult], Set[str]]:
        """
        Run tests and optionally detect flaky tests.
        
        Returns:
            Tuple of (test_results, flaky_tests)
        """
        flaky_tests = set()
        if check_flaky:
            flaky_tests = await self.test_runner.detect_flaky_tests(suite)
            
        results = await self.test_runner.run_tests(suite)
        return results, flaky_tests