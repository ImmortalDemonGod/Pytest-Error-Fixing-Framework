# branch_fixer/services/pytest/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from _pytest.main import ExitCode

@dataclass
class TestResult:
    """Detailed test execution result."""

    # Test identification
    nodeid: str
    test_file: Optional[Path] = None
    test_function: Optional[str] = None

    # Execution info
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0

    # Outcomes for each phase
    setup_outcome: Optional[str] = None
    call_outcome: Optional[str] = None
    teardown_outcome: Optional[str] = None

    # Outputs
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    log_output: Optional[str] = None

    # Error details
    error_message: Optional[str] = None
    longrepr: Optional[str] = None
    traceback: Optional[str] = None

    # Test metadata
    markers: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Summary flags
    passed: bool = False
    failed: bool = False
    skipped: bool = False
    xfailed: bool = False
    xpassed: bool = False


@dataclass
class SessionResult:
    """Complete test session results."""

    # Session info
    start_time: datetime
    end_time: datetime
    duration: float
    exit_code: ExitCode

    # Result counts
    total_collected: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    xfailed: int = 0
    xpassed: int = 0
    errors: int = 0

    # Detailed results
    test_results: Dict[str, TestResult] = field(default_factory=dict)
    collection_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)