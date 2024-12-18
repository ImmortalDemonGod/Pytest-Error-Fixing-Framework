# Program Execution Flow Documentation

## 1. Program Initialization

### 1.1 Entry Point (`cli.py`)
The program begins execution in `cli.py` through the `run_cli` function, which:
1. Processes command line arguments (API key, max retries, temperature settings)
2. Sets up logging configuration
3. Creates a CLI instance
4. Initializes core components

### 1.2 Component Initialization (`CLI.setup_components`)
```
CLI.setup_components
├── Initialize AIManager
├── Initialize TestRunner
├── Initialize ChangeApplier
├── Initialize GitRepository
└── Create FixService instance
    ├── Validate workspace
    └── Check dependencies
```

## 2. Main Execution Flow

### 2.1 Test Discovery and Error Collection
1. TestRunner executes initial pytest run
2. Output is parsed for test failures
3. TestError objects are created for each failure
4. Errors are filtered and validated

### 2.2 Fix Session Creation
```
FixOrchestrator.start_session
├── Create new FixSession
├── Initialize state management
│   └── Set initial state to INITIALIZING
├── Create recovery point
└── Transition to RUNNING state
```

### 2.3 Fix Attempt Workflow
For each TestError:
```
FixOrchestrator.fix_error
├── Create fix branch (GitRepository)
├── Generate fix attempt (AIManager)
│   ├── Construct prompt
│   └── Get AI completion
├── Apply changes (ChangeApplier)
│   ├── Backup original file
│   ├── Apply modifications
│   └── Verify syntax
├── Verify fix (TestRunner)
│   ├── Run specific test
│   └── Validate results
└── Create pull request if successful
```

## 3. Component Interactions

### 3.1 Orchestration Layer
```
FixOrchestrator
├── Coordinates with SessionCoordinator
│   ├── Manages state transitions
│   └── Handles component coordination
├── Uses WorkflowDispatcher
│   ├── Manages fix workflows
│   └── Handles component errors
└── Updates ProgressReporter
    └── Streams progress updates
```

### 3.2 Storage Layer
```
SessionStore
├── Manages session persistence
├── Interfaces with StateManager
│   ├── Validates state transitions
│   └── Maintains state history
└── Uses RecoveryManager
    ├── Creates recovery points
    └── Handles failure recovery
```

### 3.3 Git Operations
```
GitRepository
├── BranchManager
│   ├── Creates fix branches
│   └── Manages branch cleanup
├── PRManager
│   ├── Creates pull requests
│   └── Updates PR status
└── SafetyManager
    ├── Creates backups
    └── Handles restore operations
```

## 4. Error Handling and Recovery

### 4.1 Error Flow
```
Error occurs
├── Component catches error
├── Propagates to FixOrchestrator
├── Orchestrator.handle_error
│   ├── Logs error details
│   ├── Attempts recovery
│   └── Updates session state
└── Notifies user of outcome
```

### 4.2 Recovery Process
```
RecoveryManager.handle_failure
├── Identify error type
├── Load recovery point
├── Restore files if needed
├── Reset Git state
└── Resume or fail session
```

## 5. State Management

### 5.1 Session States
```
State Transitions
├── INITIALIZING
│   └── → RUNNING
├── RUNNING
│   ├── → PAUSED
│   ├── → COMPLETED
│   └── → FAILED
├── PAUSED
│   ├── → RUNNING
│   └── → FAILED
└── ERROR
    ├── → RUNNING
    └── → FAILED
```

### 5.2 State Validation
- StateManager validates all transitions
- Maintains transition history
- Ensures state consistency

## 6. Progress Tracking

### 6.1 Progress Updates
```
ProgressReporter
├── Tracks total errors
├── Monitors fix attempts
├── Updates current status
└── Generates summaries
```

## 7. Session Completion

### 7.1 Successful Completion
```
Session completes
├── Verify all fixes
├── Create pull requests
├── Clean up branches
├── Generate final report
└── Transition to COMPLETED
```

### 7.2 Failed Completion
```
Session fails
├── Restore safe state
├── Clean up artifacts
├── Log failure details
└── Transition to FAILED
```

## 8. Resource Cleanup

### 8.1 Cleanup Process
```
Final cleanup
├── Remove temporary files
├── Delete old backups
├── Clean Git branches
└── Close session
```

## 9. Exit Points

The program can exit through several paths:
1. Successful completion - all tests fixed
2. Partial completion - some tests fixed
3. Failure - no tests fixed
4. Error - program terminated due to error
5. User interruption - manual termination

Each exit point ensures:
- Proper state cleanup
- Resource release
- Git repository stability
- Data persistence
- Appropriate exit code

## 10. Logging and Monitoring

Throughout execution:
- Operations are logged
- Errors are captured
- Progress is reported
- State changes are recorded
- Git operations are tracked

This comprehensive flow ensures:
- Reliable execution
- Error recovery
- Data consistency
- Progress tracking
- Resource management
# Pytest Error Fixing Framework - Program Execution Flow Documentation

## 1. Program Entry Point

### 1.1 CLI Initialization
The program begins execution in `cli.py` through the `run_cli` function, which:
1. Processes command line arguments including:
   - OpenAI API key
   - Maximum retry attempts
   - Initial temperature
   - Temperature increment
   - Interactive mode flag
   - Test path and function specifications

2. Sets up logging configuration using `setup_logging()` from `config/logging_config.py`

### 1.2 Component Initialization
The CLI's `setup_components()` method initializes core services:
```python
# Initialization sequence
ai_manager = AIManager(api_key)
test_runner = TestRunner()
change_applier = ChangeApplier()
git_repo = GitRepository()

fix_service = FixService(
    ai_manager=ai_manager,
    test_runner=test_runner,
    change_applier=change_applier,
    git_repo=git_repo,
    max_retries=max_retries,
    initial_temp=initial_temp,
    temp_increment=temp_increment
)
```

## 2. Test Discovery and Error Analysis

### 2.1 Initial Test Run
1. TestRunner executes pytest to discover failing tests:
   ```python
   test_result = test_runner.run_test(
       test_file=test_path,
       test_function=test_function
   )
   ```

### 2.2 Error Parsing
1. Output is parsed to identify fixable errors using failure and collection parsers
2. Each error is converted into a TestError model with:
   - Test file path
   - Test function name
   - Error details
   - Stack trace

## 3. Fix Session Management

### 3.1 Session Initialization
The FixOrchestrator creates a new fix session:
1. Generates unique session ID
2. Initializes session state
3. Records start time and error list
4. Creates Git branch for fixes

### 3.2 State Management
StateManager tracks session state transitions:
1. INITIALIZING → RUNNING
2. RUNNING → PAUSED/COMPLETED/FAILED/ERROR
3. PAUSED → RUNNING
4. ERROR → RUNNING/FAILED

## 4. Fix Attempt Workflow

### 4.1 Preparation Phase
For each error, the FixService:
1. Validates workspace
2. Checks dependencies
3. Creates backup through SafetyManager
4. Initializes new fix attempt with current temperature

### 4.2 AI Generation Phase
AIManager generates fix:
1. Constructs prompt from error details
2. Makes API request with current temperature
3. Parses response into code changes
4. Validates generated changes

### 4.3 Change Application Phase
ChangeApplier implements fixes:
1. Creates backup of original file
2. Applies generated changes
3. Verifies file validity
4. Handles rollback if needed

### 4.4 Verification Phase
TestRunner verifies fix:
1. Runs affected test
2. Checks for new failures
3. Validates overall test suite
4. Reports success/failure

## 5. Git Operations

### 5.1 Branch Management
BranchManager handles version control:
1. Creates fix branches
2. Tracks modified files
3. Manages commits
4. Handles branch cleanup

### 5.2 Pull Request Creation
PRManager handles code review:
1. Creates pull request
2. Adds description and context
3. Links related issues
4. Handles PR updates

## 6. Error Recovery

### 6.1 Recovery Points
RecoveryManager creates safety nets:
1. Creates recovery checkpoints
2. Tracks modified files
3. Stores metadata
4. Manages cleanup

### 6.2 Failure Handling
On errors, the system:
1. Captures error context
2. Attempts automatic recovery
3. Restores from checkpoint if needed
4. Updates session state

## 7. Session Completion

### 7.1 Success Path
On successful fix:
1. Marks attempt as successful
2. Updates test status
3. Creates pull request
4. Cleans up temporary files

### 7.2 Failure Path
On fix failure:
1. Marks attempt as failed
2. Increments temperature
3. Tries again if retries remain
4. Records failure details

## 8. Progress Reporting

ProgressReporter provides updates:
1. Tracks overall progress
2. Reports current status
3. Shows error counts
4. Generates summary

## 9. Data Persistence

### 9.1 Session Storage
SessionStore manages persistence:
1. Saves session state
2. Tracks progress
3. Handles recovery data
4. Manages cleanup

### 9.2 State History
StateManager maintains:
1. State transition history
2. Validation results
3. Error context
4. Recovery points

## 10. Program Termination

### 10.1 Normal Termination
On completion:
1. Generates final report
2. Cleans up resources
3. Updates repository state
4. Exits with status code

### 10.2 Error Termination
On critical failure:
1. Logs error details
2. Attempts cleanup
3. Restores safe state
4. Exits with error code

## Error Handling Throughout Flow

Each component implements specific error handling:

1. **AIManager**:
   - Handles API failures
   - Manages retry logic
   - Validates responses

2. **TestRunner**:
   - Handles test failures
   - Manages timeouts
   - Tracks execution errors

3. **ChangeApplier**:
   - Handles parsing errors
   - Manages file operations
   - Implements rollback

4. **GitRepository**:
   - Handles command failures
   - Manages merge conflicts
   - Implements safe operations

5. **SessionStore**:
   - Handles corruption
   - Manages concurrent access
   - Implements recovery

This comprehensive error handling ensures the system remains stable and recoverable throughout the execution flow.