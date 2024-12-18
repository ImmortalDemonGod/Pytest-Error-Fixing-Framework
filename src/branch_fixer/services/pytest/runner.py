# branch_fixer/services/pytest/runner.py
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import pytest
from _pytest.reports import TestReport, CollectReport
from _pytest.config import Config
from _pytest.main import ExitCode
from _pytest.nodes import Item

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Detailed test execution result"""
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
    """Complete test session results"""
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

class PytestRunner:
    """Pytest execution manager with comprehensive result capture"""

    def __init__(self, working_dir: Optional[Path] = None):
        """Initialize runner with optional working directory"""
        self.working_dir = working_dir
        self._current_session: Optional[SessionResult] = None

    def pytest_runtest_logreport(self, report: TestReport):
        """Hook to capture comprehensive test information"""
        if not self._current_session:
            return

        result = self._current_session.test_results.get(report.nodeid)
        if not result:
            result = TestResult(
                nodeid=report.nodeid,
                test_file=Path(report.fspath) if report.fspath else None,
                test_function=report.function.__name__ if hasattr(report, 'function') else None
            )
            self._current_session.test_results[report.nodeid] = result

        # Update phase results
        if report.when == 'setup':
            result.setup_outcome = report.outcome
        elif report.when == 'call':
            result.call_outcome = report.outcome
        elif report.when == 'teardown':
            result.teardown_outcome = report.outcome

        # Capture outputs
        if report.capstdout:
            result.stdout = report.capstdout
        if report.capstderr:
            result.stderr = report.capstderr
        if hasattr(report, 'caplog'):
            result.log_output = report.caplog

        # Capture error information
        if report.longrepr:
            result.longrepr = str(report.longrepr)
            crash = getattr(report.longrepr, 'reprcrash', None)
            if crash:
                result.error_message = str(crash)

        # Update execution info
        result.duration = report.duration

        # Update outcome flags
        result.passed = report.passed
        result.failed = report.failed
        result.skipped = report.skipped
        if hasattr(report, 'wasxfail'):
            result.xfailed = True
        if hasattr(report, 'wasxpassed'):
            result.xpassed = True

        # Capture test metadata
        if hasattr(report, 'keywords'):
            result.markers = [
                name for name, marker in report.keywords.items()
                if isinstance(marker, pytest.Mark)
            ]

    def pytest_collectreport(self, report: CollectReport):
        """Hook to capture collection information"""
        if not self._current_session:
            return

        if report.outcome == 'failed':
            self._current_session.collection_errors.append(str(report.longrepr))

    def pytest_warning_recorded(self, warning_message: Warning):
        """Hook to capture test warnings"""
        if self._current_session:
            self._current_session.warnings.append(str(warning_message))

    async def run_test(self,
                      test_path: Optional[Path] = None,
                      test_function: Optional[str] = None) -> SessionResult:
        """Run pytest with detailed result capture"""
        start_time = datetime.now()
        
        # Initialize session
        self._current_session = SessionResult(
            start_time=start_time,
            end_time=start_time,
            duration=0.0,
            exit_code=ExitCode.OK
        )

        try:
            # Register hooks
            pytest.hookimpl(hookwrapper=True)(self.pytest_runtest_logreport)
            pytest.hookimpl(hookwrapper=True)(self.pytest_collectreport)
            pytest.hookimpl(hookwrapper=True)(self.pytest_warning_recorded)

            # Build pytest args
            args = []
            if self.working_dir:
                args.extend(["--rootdir", str(self.working_dir)])
            if test_path:
                if test_function:
                    args.append(f"{test_path}::{test_function}")
                else:
                    args.append(str(test_path))

            # Run pytest
            exit_code = pytest.main(args)
            
            # Update session info
            end_time = datetime.now()
            self._current_session.end_time = end_time
            self._current_session.duration = (end_time - start_time).total_seconds()
            self._current_session.exit_code = ExitCode(exit_code)

            # Update result counts
            for result in self._current_session.test_results.values():
                if result.passed:
                    self._current_session.passed += 1
                elif result.failed:
                    self._current_session.failed += 1
                elif result.skipped:
                    self._current_session.skipped += 1
                if result.xfailed:
                    self._current_session.xfailed += 1
                if result.xpassed:
                    self._current_session.xpassed += 1

            self._current_session.total_collected = len(self._current_session.test_results)
            self._current_session.errors = len(self._current_session.collection_errors)

            return self._current_session

        finally:
            # Clean up
            session = self._current_session
            self._current_session = None
            return session

    async def verify_fix(self,
                        test_file: Path,
                        test_function: str) -> bool:
        """Verify if a specific test passes"""
        session = await self.run_test(test_file, test_function)
        return session.passed == session.total_collected

    def format_report(self, session: SessionResult) -> str:
        """Format session results into detailed report"""
        lines = [
            "Test Execution Report",
            "====================",
            f"Duration: {session.duration:.2f}s",
            f"Status: {session.exit_code.name}",
            "",
            f"Total Tests: {session.total_collected}",
            f"Passed: {session.passed}",
            f"Failed: {session.failed}",
            f"Skipped: {session.skipped}",
            f"XFailed: {session.xfailed}",
            f"XPassed: {session.xpassed}",
            f"Errors: {session.errors}",
            ""
        ]

        if session.collection_errors:
            lines.extend(["Collection Errors:", "-" * 16, ""])
            lines.extend(session.collection_errors)
            lines.append("")

        if session.warnings:
            lines.extend(["Warnings:", "-" * 8, ""])
            lines.extend(session.warnings)
            lines.append("")

        for nodeid, result in session.test_results.items():
            if result.failed:
                lines.extend([
                    f"FAILED {nodeid}",
                    "=" * (7 + len(nodeid)),
                    result.error_message or "",
                    result.longrepr or "",
                    ""
                ])

        return "\n".join(lines)