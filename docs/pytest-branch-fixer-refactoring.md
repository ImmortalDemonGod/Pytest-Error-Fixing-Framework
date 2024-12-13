# Pytest Branch Fixer Refactoring Plan

## Project Structure

pytest_branch_fixer/
├── __init__.py
├── main.py
├── pytest/
│   ├── __init__.py
│   ├── error_info.py
│   ├── error_parser/
│   │   ├── __init__.py
│   │   ├── collection_parser.py
│   │   ├── failure_parser.py
│   │   └── summary_parser.py
│   └── runner.py
├── git/
│   ├── __init__.py
│   ├── repo.py
│   ├── branch_ops.py
│   └── pr_ops.py
└── utils/
    ├── __init__.py
    ├── cli.py
    ├── logging_config.py
    └── prompt_handler.py

## Component Breakdown

### 1. Main Program (main.py)
```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ProcessingConfig:
    check_all: bool = False
    skip_auth: bool = False
    auto_merge: bool = False

class ErrorProcessor:
    def process_errors(self, errors: list[ErrorInfo]) -> bool
    def handle_single_error(self, error: ErrorInfo) -> bool
    def create_fix_branch(self, error: ErrorInfo) -> tuple[GitRepo, str]
    def process_fix_result(self, result: bool) -> bool
    def cleanup(self) -> None

class PRProcessor:
    def handle_pr_creation(self, repo: GitRepo, branch: str, error: ErrorInfo) -> bool
    def wait_for_merge(self) -> bool
    def update_main_branch(self, repo: GitRepo) -> bool
    def handle_merge_failure(self, error: Exception) -> bool

def main(config: ProcessingConfig = ProcessingConfig()) -> int:
    # High-level orchestration only
    return 0
```

### 2. Error Info (pytest/error_info.py)
```python
@dataclass
class ErrorInfo:
    test_file: str
    function: str
    error_type: str
    error_details: str
    line_number: str = "0"
    code_snippet: str = ""

    @property
    def file_path(self) -> Path:
        """Returns Path object for test file"""

    @property
    def formatted_error(self) -> str:
        """Returns formatted error message"""

    @property
    def has_traceback(self) -> bool:
        """Checks if error has traceback"""

    def update_snippet(self, new_snippet: str) -> None:
        """Updates code snippet with proper formatting"""
```

### 3. Error Parser Components (pytest/error_parser/)

#### Collection Parser (collection_parser.py)
```python
class CollectionParser:
    def parse_collection_errors(self, output: str) -> list[ErrorInfo]
    def extract_collection_match(self, match: re.Match) -> ErrorInfo
    def validate_collection_error(self, error: ErrorInfo) -> bool

COLLECTION_PATTERN = r"ERROR collecting (.?)\s\n.*?"
```

#### Failure Parser (failure_parser.py)
```python
class FailureParser:
    def parse_test_failures(self, output: str) -> list[ErrorInfo]
    def process_failure_line(self, line: str) -> Optional[ErrorInfo]
    def extract_traceback(self, lines: list[str], start_idx: int) -> tuple[str, int]

    @property
    def patterns(self) -> list[str]:
        """Returns compiled regex patterns"""
```

#### Summary Parser (summary_parser.py)
python
class SummaryParser:
    def parse_summary_errors(self, output: str) -> list[ErrorInfo]
    def extract_summary_section(self, output: str) -> Optional[str]
    def process_summary_line(self, line: str) -> Optional[ErrorInfo]

### 4. Git Components

#### Core Repository (git/repo.py)
```python
class GitRepoCore:
    def init(self, root: Optional[Path] = None)
    def _initialize_repo(self) -> None
    def _setup_logging(self) -> None
    def _validate_repo(self) -> bool

class GitCommandRunner:
    def run_command(self, cmd: list[str]) -> subprocess.CompletedProcess
    def run_command_safe(self, cmd: list[str]) -> Optional[str]
    def handle_git_error(self, error: subprocess.CalledProcessError) -> None
```

#### Branch Operations (git/branch_ops.py)
```python
@dataclass
class BranchStatus:
    current_branch: str
    has_changes: bool
    changes: list[str]

class BranchManager:
    def get_branch_status(self) -> BranchStatus
    def handle_uncommitted_changes(self) -> bool
    def stash_operations(self) -> bool
    def create_branch(self, name: str) -> bool
    def handle_revert_state(self) -> bool
```

#### Pull Request Operations (git/pr_ops.py)
```python
@dataclass
class PRDetails:
    branch: str
    title: str
    body: str
    base: str

class PullRequestManager:
    def create_pr(self, details: PRDetails) -> bool
    def verify_auth(self) -> bool
    def push_branch(self, branch: str, force: bool = False) -> bool
    def get_repo_info(self) -> str
```

### 5. Test Runner (pytest/runner.py)
```python
@dataclass
class TestInfo:
    path: Optional[str]
    function: Optional[str]
    verbosity: int = 2

@dataclass
class TestResult:
    output: str
    passed: bool
    error_message: Optional[str]

class TestRunner:
    def run_test(self, test_info: TestInfo) -> TestResult
    def verify_pytest(self) -> bool
    def handle_clipboard(self, content: str) -> bool

class TestMonitor:
    def wait_for_fix(self, test_info: TestInfo) -> bool
    def check_test_status(self, result: TestResult) -> bool
```

### 6. Utilities

#### CLI Interface (utils/cli.py)
python
class UserInteraction:
    def prompt_for_choice(self, choices: list[str]) -> str
    def display_error_info(self, error: ErrorInfo) -> None
    def confirm_action(self, prompt: str) -> bool
    def get_commit_message(self) -> str
    def show_diff(self, diff: str) -> None

#### Logging Configuration (utils/logging_config.py)
python
class LogConfig:
    def setup_logging(self) -> None
    def get_logger(self, name: str) -> logging.Logger
    def configure_handlers(self) -> None

#### Prompt Handler (utils/prompt_handler.py)
python
class PromptHandler:
    def get_template(self) -> str
    def load_template_file(self) -> Optional[str]
    def get_default_template(self) -> str

## Key Improvements

    Complexity Reduction
        All methods have cyclomatic complexity ≤ 8
        Eliminated nested conditionals
        Clear separation of concerns

    Error Handling
        Consistent error handling patterns
        Proper logging at all levels
        Type hints for better IDE support

    Testing Support
        Each component is independently testable
        Clear interfaces between components
        Mockable dependencies

    Type Safety
        Full type annotations
        Dataclasses for data structures
        Optional handling

    Configuration
        Centralized configuration
        Environment-aware settings
        Flexible logging setup

## Migration Strategy

    Create new directory structure
    Move core classes (ErrorInfo, GitRepoCore)
    Implement utility modules
    Refactor parsers one at a time
    Update main program flow
    Add tests for new components
    Verify original functionality

## Dependencies
# requirements.txt
pyperclip>=1.8.2
pytest>=7.0.0
typing-extensions>=4.0.0  # For Python <3.8

## Notes

    Original functionality maintained
    Backward compatible
    Improved error handling
    Better logging
    More testable components

This refactoring improves maintainability while preserving the original functionality and adding room for future enhancements.