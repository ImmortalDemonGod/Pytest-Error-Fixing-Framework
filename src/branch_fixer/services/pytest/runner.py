# branch_fixer/services/pytest/runner.py
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import snoop

import pytest
from _pytest.reports import TestReport, CollectReport
from _pytest.config import Config
from _pytest.main import ExitCode, Session
from _pytest.nodes import Item
from branch_fixer.services.pytest.models import SessionResult, TestResult

logger = logging.getLogger(__name__)


class PytestPlugin:
    """Plugin to capture pytest execution information."""
    
    def __init__(self, runner):
        self.runner = runner

    @pytest.hookimpl
    def pytest_collection_modifyitems(self, session, config, items):
        """Print information about collected tests."""
        print(f"Collected {len(items)} test items:")
        for item in items:
            print(f"  - {item.nodeid}")

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report):
        """Handle test execution reports."""
        print(f"Test report for {report.nodeid}: {report.outcome} in phase {report.when}")
        self.runner.pytest_runtest_logreport(report)

    @pytest.hookimpl
    def pytest_collectreport(self, report):
        """Handle collection reports."""
        if report.outcome == 'failed':
            print(f"Collection failed: {report.longrepr}")
        self.runner.pytest_collectreport(report)

    @pytest.hookimpl
    def pytest_warning_recorded(self, warning_message):
        """Handle warnings during test execution."""
        print(f"Warning recorded: {warning_message}")
        self.runner.pytest_warning_recorded(warning_message)


class PytestRunner:
    """Pytest execution manager with comprehensive result capture."""

    def __init__(self, working_dir: Optional[Path] = None):
        self.working_dir = working_dir
        self._current_session: Optional[SessionResult] = None

    @snoop(depth=2)
    def run_test(self,
                test_path: Optional[Path] = None,
                test_function: Optional[str] = None) -> SessionResult:
        """
        Run pytest with detailed result capture.

        Args:
            test_path (Optional[Path]): The path to the test file or directory
            test_function (Optional[str]): The specific test function to run

        Returns:
            SessionResult: The result of the test session
        """
        start_time = datetime.now()

        # Initialize session
        self._current_session = SessionResult(
            start_time=start_time,
            end_time=start_time,
            duration=0.0,
            exit_code=ExitCode.OK
        )

        try:
            # Register plugin
            plugin = PytestPlugin(self)
            
            # Create base arguments
            args = []

            # Override addopts from ini file to prevent conflicts
            args.append("--override-ini=addopts=")
            
            # Set reporting options
            args.extend(["-p", "no:terminal"])

            # Add rootdir if specified
            if self.working_dir:
                args.extend(["--rootdir", str(self.working_dir)])

            # Add test path and function if specified
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

            # Update result counts
            for result in self._current_session.test_results.values():
                if result.passed and not result.xfailed and not result.xpassed:
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
        
    def pytest_runtest_logreport(self, report: TestReport):
        """
        Hook to capture comprehensive test information during test execution.

        This method is called by pytest after each test phase (setup, call, teardown).

        Args:
            report (TestReport): The report object containing test execution details.
        """
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

        # Update outcome flags based on all phases
        # A test is only considered passed if all phases pass
        result.passed = (
            result.setup_outcome == 'passed' and
            (result.call_outcome == 'passed' or result.call_outcome == 'skipped') and
            result.teardown_outcome == 'passed'
        )
        
        # Handle xfail cases properly
        if hasattr(report, 'wasxfail'):
            if report.skipped:
                result.xfailed = True
                result.passed = False
            elif report.passed:
                result.xpassed = True
                result.passed = True

        # A test is considered failed if any phase fails
        result.failed = any(
            outcome == 'failed'
            for outcome in [result.setup_outcome, result.call_outcome, result.teardown_outcome]
            if outcome is not None
        )

        # Capture test metadata
        if hasattr(report, 'keywords'):
            result.markers = [
                name for name, marker in report.keywords.items()
                if isinstance(marker, pytest.Mark)
            ]
    
    def verify_fix(self,
                        test_file: Path,
                        test_function: str) -> bool:
        """
        Verify if a specific test passes after a fix.

        This method runs the specified test and checks if it passes successfully.

        Args:
            test_file (Path): The path to the test file.
            test_function (str): The name of the test function.

        Returns:
            bool: True if the test passes, False otherwise.
        """
        session = self.run_test(test_file, test_function)
        # A test is verified as fixed only if:
        # 1. We collected exactly the number of tests we expected
        # 2. All collected tests passed
        # 3. No tests failed
        return (
            session.total_collected > 0 and
            session.passed == session.total_collected and
            session.failed == 0
        )

    def format_report(self, session: SessionResult) -> str:
        """
        Format session results into a detailed report.

        This method generates a human-readable report summarizing the test session.

        Args:
            session (SessionResult): The test session results to format.

        Returns:
            str: The formatted report as a string.
        """
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
     

    def pytest_collectreport(self, report: CollectReport):
        """
        Hook to capture collection information during test discovery.

        This method is called by pytest after attempting to collect tests.

        Args:
            report (CollectReport): The report object containing collection details.
        """
        if not self._current_session:
            return

        if report.outcome == 'failed':
            self._current_session.collection_errors.append(str(report.longrepr))

    def pytest_warning_recorded(self, warning_message: Warning):
        """
        Hook to capture test warnings during test execution.

        This method is called by pytest when a warning is recorded.

        Args:
            warning_message (Warning): The warning message object.
        """
        if self._current_session:
            self._current_session.warnings.append(str(warning_message))
    

