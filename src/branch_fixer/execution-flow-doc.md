# Program Execution Flow Documentation

## 1. Program Entry Point

### 1.1 CLI Entry (`run_cli.py`)
The program begins execution in `run_cli.py` through the `@click.command()` decorated function, which processes:

Command Line Arguments:
```python
@click.command()
@click.option('--api-key', envvar='OPENAI_API_KEY', required=True)
@click.option('--max-retries', default=3)
@click.option('--initial-temp', default=0.4)
@click.option('--temp-increment', default=0.1)
@click.option('--non-interactive', is_flag=True)
@click.option('--test-path', type=click.Path(exists=True, path_type=Path))
@click.option('--test-function')
@click.option('--cleanup-only', is_flag=True)
```

Initialization Steps:
1. Sets up logging configuration via `setup_logging()`
2. Creates CLI instance
3. Initializes components through `setup_components()`
4. Sets up signal handlers for graceful exit
5. Optionally performs cleanup-only mode

### 1.2 Component Initialization
```python
def setup_components(self, api_key: str, max_retries: int, 
                    initial_temp: float, temp_increment: float) -> bool:
    try:
        # Initialize core components
        ai_manager = AIManager(api_key)
        test_runner = TestRunner()
        change_applier = ChangeApplier()
        git_repo = GitRepository()
        
        # Create service
        self.service = FixService(
            ai_manager=ai_manager,
            test_runner=test_runner,
            change_applier=change_applier,
            git_repo=git_repo,
            max_retries=max_retries,
            initial_temp=initial_temp,
            temp_increment=temp_increment
        )
        
        # Validate workspace
        asyncio.get_event_loop().run_until_complete(
            self.service.validator.validate_workspace(Path.cwd())
        )
        
        # Check dependencies
        asyncio.get_event_loop().run_until_complete(
            self.service.validator.check_dependencies()
        )
        
        return True
    except Exception as e:
        logger.error(f"Component initialization failed: {str(e)}")
        return False
```

## 2. Test Discovery and Analysis

### 2.1 Test Execution
Implemented in TestRunner:
```python
def run_test(self, test_path: Optional[Path] = None,
            test_function: Optional[str] = None) -> SessionResult:
    # Initialize session
    self._current_session = SessionResult(
        start_time=datetime.now(),
        end_time=datetime.now(),
        duration=0.0,
        exit_code=ExitCode.OK
    )

    try:
        # Register plugin
        plugin = PytestPlugin(self)

        # Create base arguments
        args = ["--override-ini=addopts=", "-p", "no:terminal"]
        
        # Add path/function if specified
        if test_path:
            if test_function:
                args.append(f"{str(test_path)}::{test_function}")
            else:
                args.append(str(test_path))

        # Run pytest
        exit_code = pytest.main(args, plugins=[plugin])
        
        # Update session info
        end_time = datetime.now()
        self._current_session.end_time = end_time
        self._current_session.duration = (end_time - start_time).total_seconds()
        self._current_session.exit_code = ExitCode(exit_code)
```

### 2.2 Error Processing
```python
def parse_pytest_errors(output: str) -> List[TestError]:
    # Extract test results using regex
    failed_test_pattern = r'FAILED (.*?)::(.+?)\n((?:.*?\n)*?(?=FAILED|\Z))'
    matches = re.finditer(failed_test_pattern, output, re.MULTILINE)
    
    test_errors = []
    for match in matches:
        test_file, test_function = match.group(1), match.group(2)
        error_block = match.group(3)
        
        # Extract error type and message
        error_match = re.search(r'E\s+([\w\.]+Error):\s+(.+)', error_block)
        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)
            
            test_errors.append(TestError(
                test_file=Path(test_file.strip()),
                test_function=test_function.strip(),
                error_details=ErrorDetails(
                    error_type=error_type,
                    message=error_message,
                    stack_trace=error_block.strip() if error_block else None
                )
            ))
```

## 3. Fix Attempt Workflow

### 3.1 Fix Service Implementation
```python
async def attempt_fix(self, error: TestError) -> bool:
    try:
        # Validate workspace
        await self.validator.validate_workspace(error.test_file.parent)
        await self.validator.check_dependencies()

        # Start fix attempt
        attempt = error.start_fix_attempt(self.initial_temp)
        
        try:
            # Generate and apply fix
            changes = await self.ai_manager.generate_fix(error, attempt.temperature)
            
            # Apply changes
            if not self.change_applier.apply_changes(error.test_file, changes):
                self._handle_failed_attempt(error, attempt)
                return False
                
            # Verify fix
            if not await self._verify_fix(error, attempt):
                self._handle_failed_attempt(error, attempt)
                return False
                
            # Mark as fixed
            error.mark_fixed(attempt)
            return True
            
        except Exception as e:
            self._handle_failed_attempt(error, attempt)
            raise FixServiceError(str(e)) from e
    finally:
        # Clean up
        try:
            branch_name = f"fix-{error.test_file.stem}-{error.test_function}"
            await self.git_repo.branch_manager.cleanup_fix_branch(branch_name)
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup branch {branch_name}: {cleanup_error}")
```

### 3.2 AI Manager Operation
```python
async def generate_fix(self, error: TestError, temperature: float) -> CodeChanges:
    session = await self.state_manager.create_session(error)
    
    try:
        await self.state_manager.transition_state(session, "INITIALIZING")
        recovery_point = await self.recovery_manager.create_checkpoint(session)
        
        for attempt in range(self.max_attempts):
            temperature = await self._adapt_strategy(
                error,
                self.state.fix_attempts[-1] if self.state.fix_attempts else None,
                temperature
            )
            
            fix = await self._attempt_fix(error, temperature)
            is_valid = await self._validate_fix(fix, error)
            
            if is_valid:
                return fix
```

Temperature Adaptation Strategy:
```python
async def _adapt_strategy(self, error: TestError,
                         previous_attempt: Optional[FixAttempt],
                         current_temp: float) -> float:
    if not previous_attempt:
        return self.base_temperature
        
    # Syntax/style failures -> small bump
    if any('syntax' in err or 'style' in err 
           for err in previous_attempt.validation_errors):
        return current_temp + 0.1
        
    # Test failures -> larger bump    
    if any('test' in err for err in previous_attempt.validation_errors):
        return current_temp + 0.2
```

## 4. Git Operations

### 4.1 Branch Management
```python
async def create_fix_branch(self, 
                         branch_name: str,
                         from_branch: Optional[str] = None) -> bool:
    try:
        # Validate branch name
        if not await self.validate_branch_name(branch_name):
            raise BranchNameError(f"Invalid branch name: {branch_name}")

        # Check if branch exists
        if await self.repository.branch_exists(branch_name):
            raise BranchCreationError(f"Branch {branch_name} already exists")
            
        # Create branch
        result = await self.repository.run_command(
            ['checkout', '-b', branch_name, from_branch or self.repository.main_branch]
        )
        
        return result.returncode == 0
    except Exception as e:
        # Preserve specific error types
        if isinstance(e, (BranchNameError, BranchCreationError)):
            raise
        raise GitError(f"Failed to create branch {branch_name}: {str(e)}")
```

### 4.2 Git Command Execution
```python
async def run_command(self, cmd: List[str]) -> CommandResult:
    try:
        # First element should be 'git', remove if present
        if cmd[0] == 'git':
            cmd = cmd[1:]
        
        # Prepare full command
        full_cmd = ['git'] + cmd
        
        # Create and run process
        process = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.root)
        )
        
        stdout, stderr = await process.communicate()
        
        return CommandResult(
            returncode=process.returncode,
            stdout=stdout.decode('utf-8') if stdout else '',
            stderr=stderr.decode('utf-8') if stderr else '',
            command=full_cmd
        )
    except Exception as e:
        raise GitError(f"Git command failed: {str(e)}")
```

## 5. Error Handling

### 5.1 Error Hierarchy
```python
class FixError(Exception):
    """Base exception for fix operations"""
    pass

class CoordinationError(FixError):
    """Errors related to coordination"""
    pass

class WorkflowError(FixError):
    """Errors related to workflow dispatching"""
    pass

class ComponentError(FixError):
    """Errors related to specific components"""
    pass

class InteractionError(FixError):
    """Errors related to component interactions"""
    pass

class GitError(Exception):
    """Base class for Git-related exceptions"""
    pass

class AIManagerError(Exception):
    """Base exception for AI manager errors"""
    pass
```

### 5.2 Recovery Implementation
```python
class RecoveryManager:
    async def handle_failure(self, 
                           error: Exception,
                           session: 'FixSession',
                           context: Dict[str, Any]) -> bool:
        try:
            # Load recovery point
            recovery_point = await self.load_latest_recovery_point(session.id)
            if not recovery_point:
                return False

            # Restore files
            await self._restore_files(recovery_point)
            
            # Reset Git state
            await self._reset_git_state(recovery_point)
            
            return True
        except Exception as e:
            logger.error(f"Recovery failed: {str(e)}")
            return False
```

## 6. State Management

### 6.1 State Transition Validation
```python
def validate_transition(self, from_state: 'FixSessionState',
                       to_state: 'FixSessionState') -> bool:
    valid_transitions = {
        'INITIALIZING': {'RUNNING', 'FAILED'},
        'RUNNING': {'PAUSED', 'COMPLETED', 'FAILED', 'ERROR'},
        'PAUSED': {'RUNNING', 'FAILED'},
        'ERROR': {'RUNNING', 'FAILED'},
        'FAILED': set(),
        'COMPLETED': set()
    }
    return to_state in valid_transitions.get(from_state, set())
```

### 6.2 Progress Tracking
```python
@dataclass
class FixProgress:
    """Tracks progress of fix operations"""
    total_errors: int
    fixed_count: int
    current_error: Optional[str]
    retry_count: int
    current_temperature: float
    last_error: Optional[str] = None
```

## 7. Resource Management

### 7.1 Cleanup Process
```python
async def cleanup(self):
    """Cleanup resources before exit"""
    if not self.service:
        return
        
    print("\nCleaning up resources...")
    errors = []
    
    # Cleanup branches
    for branch in self.created_branches:
        try:
            print(f"Cleaning up branch: {branch}")
            await self.service.git_repo.branch_manager.cleanup_fix_branch(
                branch, force=True
            )
        except Exception as e:
            errors.append(f"Failed to cleanup branch {branch}: {str(e)}")
            logger.error(f"Cleanup error for branch {branch}: {str(e)}")
```

## Areas Needing Implementation

1. Storage Layer:
   - SessionStore needs implementation
   - State persistence needs completion
   - Recovery point storage needs implementation

2. Git Operations:
   - Some Git operations remain unimplemented
   - PR management needs completion
   - Branch cleanup could be more robust

3. Error Recovery:
   - Some recovery scenarios need implementation
   - Better handling of partial failures
   - More sophisticated rollback mechanisms

4. Testing Infrastructure:
   - More comprehensive test suite needed
   - Better coverage of error scenarios
   - Performance testing framework

This comprehensive documentation reflects the actual implementation while highlighting areas that need completion or improvement.