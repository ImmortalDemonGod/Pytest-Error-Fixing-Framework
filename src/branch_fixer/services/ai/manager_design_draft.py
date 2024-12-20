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
    file_changes: List[FileChange] = Field(default_factory=list, description="Specific line-level changes")
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
        """Apply changes atomically with backup/rollback"""
        backups = {}
        
        try:
            # Create backups
            for change in changes:
                backup_path = await self.create_backup(change.file_path)
                backups[change.file_path] = backup_path
                change.backup_path = backup_path
            
            # Apply changes in reverse line order
            for change in changes:
                await self._apply_file_changes(change)
                
        except Exception as e:
            # Rollback on error
            await self._rollback_changes(backups)
            raise FileOperationError(f"Failed to apply changes: {str(e)}")
            
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

# Test Infrastructure
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
        # Basic validation
        if not await self._validate_syntax(changes.modified_code):
            return False
            
        # Style check
        style_result = await self._check_style(changes.modified_code)
        if not style_result["passes_pep8"]:
            return False
            
        # TODO: Add test running and regression checking
        return True

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

    async def generate_fix(
        self, 
        error: TestError,
        intent: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> CodeChanges:
        """
        Generate a fix for the given test error.
        
        Makes multiple attempts with increasing temperature if needed.
        Tracks all attempts and maintains state.
        
        Args:
            error: The test error to fix
            intent: Optional user intent to guide the fix
            temperature: Optional starting temperature (uses base_temperature if not provided)
        """
        temperature = temperature or self.base_temperature
        attempt = 0
        
        while attempt < self.max_attempts:
            current_temp = temperature * (1 + attempt * 0.2)
            
            try:
                # Generate fix
                fix = await self._attempt_fix(error, current_temp, intent)
                
                # Validate fix
                is_valid = await self._validate_fix(fix, error)
                
                # Record attempt
                self.state.fix_attempts.append(
                    FixAttempt(
                        timestamp=datetime.now(),
                        error=error,
                        changes=fix,
                        temperature=current_temp,
                        success=is_valid,
                    )
                )
                
                if is_valid:
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
                            explanation=str(e),
                            confidence_score=0.0,
                        ),
                        temperature=current_temp,
                        success=False,
                        validation_errors=[str(e)],
                    )
                )
            
            attempt += 1
            
        raise AIManagerError(
            f"Failed to generate valid fix after {self.max_attempts} attempts"
        )

    async def verify_fix(self, changes: CodeChanges, error: TestError) -> bool:
        """Verify a generated fix meets all requirements"""
        return await self._validate_fix(changes, error)

    async def apply_fix(self, changes: CodeChanges) -> None:
        """Apply a validated fix to the codebase"""
        try:
            await self.file_manager.apply_changes(changes.file_changes)
        except (FileOperationError, BackupError) as e:
            raise AIManagerError(f"Failed to apply fix: {str(e)}")
            
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