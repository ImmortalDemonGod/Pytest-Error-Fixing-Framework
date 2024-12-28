# **Program Execution Flow Documentation (Updated)**

## **1. Program Entry Point**

### **1.1 CLI Entry (`run_cli.py`)**

- The program begins in **`run_cli.py`** where a `@click.group()` command named `fix` is defined.  
- **Command Line Arguments** are parsed for things like `--api-key`, `--max-retries`, `--test-path`, etc.  
- **Initialization Steps**:
  1. **Logging**: `setup_logging()` configures console + file logging.  
  2. **CLI instance**: `cli = CLI()` is created.  
  3. **Component setup**: `cli.setup_components(...)` creates `AIManager`, `TestRunner`, `ChangeApplier`, `GitRepository`, and the `FixService`. An optional `FixOrchestrator` is also instantiated for session-based flows.  
  4. **Signal Handlers**: For graceful exit on Ctrl-C or termination.  
  5. **Cleanup**: If `--cleanup-only` was passed, we call `cli.cleanup()` and exit. Otherwise, we proceed to discover failing tests and attempt fixes.

**Example** (from `run_cli.py`):
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
def fix(...):
    setup_logging()
    cli = CLI()
    if not cli.setup_components(...):
        return 1
    ...
```

### **1.2 Component Initialization**

Within `cli.setup_components(...)`:

```python
def setup_components(self, api_key: str, max_retries: int, 
                    initial_temp: float, temp_increment: float) -> bool:
    try:
        # 1) Instantiate AIManager, TestRunner, etc.
        # 2) Create FixService
        # 3) (Optional) Create FixOrchestrator
        # 4) Validate workspace + dependencies
        return True
    except Exception as e:
        ...
```

If successful, the user (or CLI) runs tests and attempts to fix discovered failures.

---

## **2. Test Discovery and Analysis**

### **2.1 Test Execution (`TestRunner.run_test`)**

- The CLI calls `test_runner.run_test(...)` to run `pytest` in a “headless” mode, registering a `PytestPlugin` that captures test output.  
- **SessionResult** is updated with how many tests passed/failed, plus the final `exit_code`.

**Key Steps**:
1. Create base pytest arguments (disable `addopts`, turn off terminal UI).  
2. If `--test-path` or `--test-function` was passed, append them to `args`.  
3. Invoke `pytest.main(args, plugins=[plugin])`.  
4. On completion, record the `end_time`, `duration`, and final `exit_code`.

```python
def run_test(self, test_path=None, test_function=None) -> SessionResult:
    start_time = datetime.now()
    ...
    exit_code = pytest.main(args, plugins=[plugin])
    ...
    self._current_session.exit_code = ExitCode(exit_code)
    return self._current_session
```

### **2.2 Error Processing (`parse_pytest_errors`)**

- After the test run, the CLI calls `parse_pytest_errors(session_result.output)` to convert the textual output into a list of `TestError`s.  
- Each error has fields like `test_file`, `test_function`, `error_details.error_type`, and `error_details.message`.

```python
def parse_pytest_errors(output: str) -> List[TestError]:
    # Regex to find "FAILED file::func" blocks
    # For each match, extract error type + message
    return test_errors
```

---

## **3. Fix Attempt Workflow**

### **3.1 Fix Service Implementation**

The **`FixService`** handles the actual fix logic for a single `TestError`:
1. **Validate** the workspace.  
2. **Generate** code changes via `AIManager.generate_fix`.  
3. **Apply** changes with backup (`ChangeApplier.apply_changes_with_backup`).  
4. **Verify** by re-running the test. If it fails, revert.  
5. Mark the `TestError` as fixed (or failed).

**Example**:
```python
def attempt_fix(self, error: TestError) -> bool:
    # 1) Validate workspace
    # 2) Possibly skip if dev_force_success
    # 3) Generate fix -> apply -> verify
    # 4) Revert if needed
    # 5) Return True/False
```

### **3.2 AI Manager Operation**

**`AIManager.generate_fix(...)`**:
- Optionally consult a “StateManager” or “RecoveryManager” to handle advanced flows.  
- Generate code changes via an LLM call (`litellm` or `marvin` or whichever backend).
- If certain attempts fail, it tries to adapt (temperature +0.1 or +0.2).  
- Returns `CodeChanges` on success.

```python
def generate_fix(self, error: TestError, temperature: float) -> CodeChanges:
    # Build LLM prompt
    # Post-process AI output => CodeChanges
    ...
```

If the fix is validated, we mark success. Otherwise, the fix attempt is flagged as failed and can trigger rollback or incremental changes.

---

## **4. Git Operations**

### **4.1 Branch Management**

Often, the fix is done on a new branch named `fix-{test_file_stem}-{test_function}`, so we can create a PR or revert easily:

```python
async def create_fix_branch(self, branch_name, from_branch=None) -> bool:
    # Validate name
    # if exists -> raise
    # run_command('git checkout -b ...')
    ...
```

### **4.2 Git Command Execution**

**`run_command(['git', 'checkout', ...])`** spawns an async subprocess for Git:

```python
async def run_command(self, cmd: List[str]) -> CommandResult:
    process = await asyncio.create_subprocess_exec(...)
    stdout, stderr = await process.communicate()
    return CommandResult(...)
```

---

## **5. Error Handling**

### **5.1 Error Hierarchy**

We have specialized exceptions:  
- **`FixError`** and subtypes for fix coordination or workflow issues.  
- **`GitError`** for Git-based failures.  
- **`AIManagerError`** for AI-based failures.

The CLI or orchestrator might catch these exceptions to revert or log partial success.

### **5.2 Recovery Implementation (Optional)**

**`RecoveryManager`** can do advanced rollbacks:
```python
async def handle_failure(self, error, session, context):
    # Find last checkpoint
    # Restore files
    # Reset branch
    return True/False
```

This is used if you want to revert to a known good state after a partial fix failure.

---

## **6. State Management**

### **6.1 State Transition Validation**

If using the **Orchestrator** with session-based flows:
```python
def validate_transition(self, from_state: 'FixSessionState', to_state: 'FixSessionState'):
    # 'INITIALIZING' -> {'RUNNING','FAILED'}, etc.
```
We only allow valid transitions, e.g. `RUNNING -> COMPLETED`.

### **6.2 Progress Tracking**

**`FixProgress`** is a data class that can track how many total errors vs. how many have been fixed, the current error, etc. If integrated, it can be used to update a UI or logs as the session proceeds.

---

## **7. Orchestrator & Session Flow**

### **7.1 Orchestrator & Session**

A **`FixOrchestrator`** can manage an entire session (`FixSession`), which includes:
- `INITIALIZING`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`, or `ERROR`.  
- A list of `TestError`s to fix, plus references to a `RecoveryManager` if needed.  
- Methods like `start_session(...)` and `run_session(...)` to handle the entire multi-error fix flow.

**Example**:
```python
async def run_session(self, session_id: UUID) -> bool:
    # For each error in session.errors:
    #   fix_error()
    #   if fail -> session.state = FAILED
    # session.state = COMPLETED
    return True/False
```

### **7.2 Resource Cleanup**

At the end (or if the user hits Ctrl-C), the CLI calls `cli.cleanup()`:
1. Remove leftover fix branches.  
2. Checkout main.  
3. Possibly revert partial changes if desired.

---

## **8. Dispatcher & Coordinator Modules**

- **`dispatcher.py`** (WorkflowDispatcher) and **`coordinator.py`** (SessionCoordinator) exist as **placeholders** for more advanced or parallel fix flows.  
- They are **not** actively used in the standard path. If you plan more sophisticated multi-session coordination or specialized component error handling, you would finish and call them.

---

## **9. Areas Needing Further Implementation**

1. **Session & State Persistence**  
   - If you want to track and resume fix sessions across runs, complete `SessionStore` usage in the orchestrator or `FixService`.

2. **Recovery Mechanisms**  
   - Decide how thoroughly you want to roll back partial fixes (entire Git branch or just a file’s changes).

3. **PR Management**  
   - Code for creating a PR is partial (`create_pull_request_sync`). Could integrate with GitHub/GitLab for a real flow.

4. **Testing Infrastructure**  
   - Expand coverage for fix attempts, partial reverts, concurrency, and performance.

---

## **Conclusion**

This updated **Program Execution Flow** outlines how:

1. **`run_cli.py`** sets up the CLI,  
2. **`CLI.setup_components()`** builds the essential services,  
3. **`TestRunner`** discovers failing tests,  
4. **`FixService`** attempts to fix them (with optional `AIManager`, `ChangeApplier`, and **`RecoveryManager`**),  
5. **`Orchestrator`** optionally manages session states,  
6. And we finalize with cleanup, removing branches and checking out the main branch again.

Unused modules like **`dispatcher.py`** and **`coordinator.py`** remain for future advanced workflows.  