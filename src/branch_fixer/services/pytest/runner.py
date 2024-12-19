# branch_fixer/services/pytest/runner.py

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field
import shutil
import time
import pytest
from _pytest.reports import TestReport, CollectReport
from _pytest.main import ExitCode
from branch_fixer.services.pytest.models import SessionResult, TestResult
import snoop

logger = logging.getLogger(__name__)

def force_remove(path: Path, retries: int = 5, delay: int = 2):
    """
    Forcefully remove a directory with retries.

    Args:
        path (Path): The path to the directory to remove.
        retries (int): Number of retry attempts.
        delay (int): Delay in seconds between retries.

    Raises:
        OSError: If the directory cannot be removed after retries.
    """
    for attempt in range(retries):
        try:
            shutil.rmtree(path)
            logger.debug(f"Successfully removed directory: {path}")
            break
        except OSError as e:
            logger.warning(f"Attempt {attempt + 1} failed to remove {path}: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.error(f"Failed to remove directory after {retries} attempts: {path}")
                raise e

class PytestPlugin:
    """Plugin to capture pytest execution information."""

    def __init__(self, runner):
        self.runner = runner

    @pytest.hookimpl
    def pytest_collection_modifyitems(self, session, config, items):
        """Print information about collected tests."""
        #print(f"Collected {len(items)} test items:")
        for item in items:
            print(f"  - {item.nodeid}")

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report):
        """Handle test execution reports."""
        #print(f"Test report for {report.nodeid}: {report.outcome} in phase {report.when}")
        self.runner.pytest_runtest_logreport(report)

    @pytest.hookimpl
    def pytest_collectreport(self, report):
        """Handle collection reports."""
        if report.outcome == 'failed':
            #print(f"Collection failed: {report.longrepr}")
            pass
        self.runner.pytest_collectreport(report)

    @pytest.hookimpl
    def pytest_warning_recorded(self, warning_message, when, nodeid, location):
        """Handle warnings during test execution."""
        #print(f"Warning recorded: {warning_message}")
        self.runner.pytest_warning_recorded(warning_message)

class PytestRunner:
    """Pytest execution manager with comprehensive result capture."""

    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize the PytestRunner.

        Args:
            working_dir (Optional[Path]): The working directory for pytest runs.
        """
        self.working_dir = working_dir or Path.cwd()
        self._current_session: Optional[SessionResult] = None
        self.temp_dirs: List[Path] = []  # Track temporary directories for cleanup
        logger.debug(f"PytestRunner initialized with working directory: {self.working_dir}")

    def capture_test_output(self) -> str:
        """Returns formatted test output that our parsers can handle"""
        output_lines = []
        
        # Add test collection output
        if self._current_session and self._current_session.collection_errors:
            for error in self._current_session.collection_errors:
                output_lines.append(f"COLLECTION ERROR: {error}")
                
        # Add test failures
        if self._current_session:
            for test_id, result in self._current_session.test_results.items():
                if result.failed:
                    file_path, test_name = test_id.split("::", 1)
                    output_lines.append(f"FAILED {file_path} {test_name}")
                    if result.error_message:
                        output_lines.append(f"E   {result.error_message}")
                    if result.longrepr:
                        output_lines.append(result.longrepr)
                    
        return "\n".join(output_lines)


    def run_test(self,
                test_path: Optional[Path] = None,
                test_function: Optional[str] = None) -> SessionResult:
        """
        Run pytest with detailed result capture.

        Args:
            test_path (Optional[Path]): The path to the test file or directory.
            test_function (Optional[str]): The specific test function to run.

        Returns:
            SessionResult: The result of the test session.
        """
        start_time = datetime.now()
        logger.info(f"Starting test run at {start_time}")

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
            logger.debug(f"Running pytest with arguments: {args}")
            exit_code = pytest.main(args, plugins=[plugin])

            # Update session info
            end_time = datetime.now()
            self._current_session.end_time = end_time
            self._current_session.duration = (end_time - start_time).total_seconds()
            self._current_session.exit_code = ExitCode(exit_code)

            logger.info(f"Test run completed at {end_time} with exit code {exit_code}")
            logger.debug(f"Session duration: {self._current_session.duration}s")

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

            logger.debug(f"Session results: {self._current_session}")

            # **Updated Part: Capture and format test output**
            self._current_session.output = self.capture_test_output()

            return self._current_session
        finally:
            # Clean up
            logger.debug("Cleaning up after test run.")
            self.cleanup()

    def pytest_runtest_logreport(self, report: TestReport):
        """
        Hook to capture comprehensive test information during test execution.

        This method is called by pytest after each test phase (setup, call, teardown).

        Args:
            report (TestReport): The report object containing test execution details.
        """
        if not self._current_session:
            logger.warning("No active session to log test report.")
            return

        result = self._current_session.test_results.get(report.nodeid)
        if not result:
            # Safely extract test_path and test_function with defaults
            test_path = Path(report.fspath) if report.fspath else Path("unknown")
            test_function = report.function.__name__ if hasattr(report, 'function') else "unknown"

            result = TestResult(
                nodeid=report.nodeid,
                test_file=test_path,
                test_function=test_function,
                error_message=None,
                longrepr=None
            )
            self._current_session.test_results[report.nodeid] = result
            logger.debug(f"Created TestResult for {report.nodeid}")

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
            logger.debug(f"Captured stdout for {report.nodeid}: {report.capstdout}")
        if report.capstderr:
            result.stderr = report.capstderr
            logger.debug(f"Captured stderr for {report.nodeid}: {report.capstderr}")
        if hasattr(report, 'caplog'):
            result.log_output = report.caplog
            logger.debug(f"Captured log output for {report.nodeid}: {report.caplog}")

        # Capture error information
        if report.longrepr:
            result.longrepr = str(report.longrepr)
            crash = getattr(report.longrepr, 'reprcrash', None)
            if crash:
                # Extract only the exception message without file path and line number
                full_message = crash.message if hasattr(crash, 'message') else str(crash)
                # Split on newline and take just the first line to match expected output
                result.error_message = full_message.split('\n')[0]
                logger.debug(f"Captured error message for {report.nodeid}: {result.error_message}")

        # Update execution info
        result.duration = report.duration
        logger.debug(f"Captured duration for {report.nodeid}: {result.duration}s")

        # Update outcome flags based on all phases
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
                logger.debug(f"Test {report.nodeid} was expected to fail and did fail.")
            elif report.passed:
                result.xpassed = True
                result.passed = True
                logger.debug(f"Test {report.nodeid} was expected to fail but passed.")

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
            logger.debug(f"Captured markers for {report.nodeid}: {result.markers}")
    

    def verify_fix(self, test_file: Path, test_function: str) -> bool:
        """
        Verify if a specific test passes after a fix.

        This method does not rely on self.run_test. Instead, it runs pytest as a subprocess
        to ensure a fresh environment on each invocation. It checks if the specified test
        passes successfully by inspecting the subprocess return code.

        Args:
            test_file (Path): The path to the test file.
            test_function (str): The name of the test function.

        Returns:
            bool: True if the test passes (exit code == 0), False otherwise.
        """
        import subprocess
        from _pytest.main import ExitCode

        logger.info(f"Verifying fix for {test_file}::{test_function}")

        # Build pytest arguments
        args = ["pytest", "--override-ini=addopts=", "-p", "no:terminal"]
        if self.working_dir:
            args.extend(["--rootdir", str(self.working_dir)])
        args.append(f"{str(test_file)}::{test_function}")

        # Run pytest in a subprocess to avoid shared state
        result = subprocess.run(args, capture_output=True, text=True)
        exit_code = ExitCode(result.returncode)

        # The test is considered fixed if pytest exits with code 0 (no failures)
        is_fixed = (exit_code == ExitCode.OK)

        logger.info(f"Verification result for {test_file}::{test_function}: {is_fixed}")
        if not is_fixed:
            logger.debug(f"Subprocess stdout:\n{result.stdout}")
            logger.debug(f"Subprocess stderr:\n{result.stderr}")

        return is_fixed
    
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

        report = "\n".join(lines)
        logger.debug("Formatted test report generated.")
        return report

    def pytest_collectreport(self, report: CollectReport):
        """
        Hook to capture collection information during test discovery.

        This method is called by pytest after attempting to collect tests.

        Args:
            report (CollectReport): The report object containing collection details.
        """
        if not self._current_session:
            logger.warning("No active session to log collect report.")
            return

        if report.outcome == 'failed':
            error_message = str(report.longrepr)
            self._current_session.collection_errors.append(error_message)
            logger.error(f"Collection failed: {error_message}")

    def pytest_warning_recorded(self, warning_message: Warning):
        """
        Hook to capture test warnings during test execution.

        This method is called by pytest when a warning is recorded.

        Args:
            warning_message (Warning): The warning message object.
        """
        if self._current_session:
            self._current_session.warnings.append(str(warning_message))
            logger.warning(f"Warning recorded during test execution: {warning_message}")

    def cleanup(self):
        """
        Clean up temporary directories and resources.

        This method removes all tracked temporary directories to ensure no residual files are left.
        """
        logger.info("Starting cleanup of temporary directories.")
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                try:
                    force_remove(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except OSError as e:
                    logger.error(f"Failed to remove temporary directory {temp_dir}: {e}")
        self.temp_dirs.clear()
        logger.info("Cleanup completed.")

TestRunner = PytestRunner