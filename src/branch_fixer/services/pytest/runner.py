# branch_fixer/services/pytest/runner.py

import logging
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import List, Optional

import pytest
from _pytest.main import ExitCode
from _pytest.reports import CollectReport, TestReport

from branch_fixer.services.pytest.models import SessionResult, TestResult

logger = logging.getLogger(__name__)


def force_remove(path: Path, retries: int = 5, delay: int = 2) -> None:
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
                logger.error(
                    f"Failed to remove directory after {retries} attempts: {path}"
                )
                raise e


class PytestPlugin:
    """Plugin to capture pytest execution information."""

    def __init__(self, runner: "PytestRunner"):
        self.runner = runner

    @pytest.hookimpl
    def pytest_collection_modifyitems(self, session, config, items) -> None:
        """Print information about collected tests."""
        # print(f"Collected {len(items)} test items:")
        for item in items:
            print(f"  - {item.nodeid}")

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """Handle test execution reports."""
        # print(f"Test report for {report.nodeid}: {report.outcome} in phase {report.when}")
        self.runner.pytest_runtest_logreport(report)

    @pytest.hookimpl
    def pytest_collectreport(self, report: CollectReport) -> None:
        """Handle collection reports."""
        if report.outcome == "failed":
            # print(f"Collection failed: {report.longrepr}")
            pass
        self.runner.pytest_collectreport(report)

    @pytest.hookimpl
    def pytest_warning_recorded(self, warning_message, when, nodeid, location) -> None:
        """Handle warnings during test execution."""
        # print(f"Warning recorded: {warning_message}")
        self.runner.pytest_warning_recorded(warning_message)


class PytestRunner:
    """Pytest execution manager with comprehensive result capture."""

    def __init__(self, working_dir: Optional[Path] = None) -> None:
        """
        Initialize the PytestRunner.

        Args:
            working_dir (Optional[Path]): The working directory for pytest runs.
        """
        self.working_dir: Path = working_dir or Path.cwd()
        self._current_session: Optional[SessionResult] = None
        self.temp_dirs: List[Path] = []  # Track temporary directories for cleanup
        # Added a lock to guard operations where concurrency could be an issue:
        self._lock = RLock()

        logger.debug(
            f"PytestRunner initialized with working directory: {self.working_dir}"
        )

    # ----------------------------------------------------------------------
    # HELPER METHODS (Introduced to reduce nesting/complexity)
    # ----------------------------------------------------------------------

    def build_pytest_args(
        self,
        test_path: Optional[Path] = None,
        test_function: Optional[str] = None,
    ) -> List[str]:
        """
        Build the pytest command arguments based on provided test path/function.

        Args:
            test_path (Optional[Path]): The path to the test file or directory.
            test_function (Optional[str]): The specific test function to run.

        Returns:
            List[str]: The list of arguments to pass to pytest.
        """
        args = ["--override-ini=addopts=", "-p", "no:terminal"]
        if self.working_dir:
            args.extend(["--rootdir", str(self.working_dir)])
        if test_path:
            if test_function:
                args.append(f"{str(test_path)}::{test_function}")
            else:
                args.append(str(test_path))
        return args

    def finalize_session(self, start_time: datetime, exit_code_val: int) -> None:
        """
        Finalize the session with end time and exit code.

        Args:
            start_time (datetime): When the test run began.
            exit_code_val (int): The integer exit code from pytest.
        """
        if not self._current_session:
            return
        end_time = datetime.now()
        self._current_session.end_time = end_time
        self._current_session.duration = (end_time - start_time).total_seconds()
        self._current_session.exit_code = ExitCode(exit_code_val)

        logger.info(f"Test run completed at {end_time} with exit code {exit_code_val}")
        logger.debug(f"Session duration: {self._current_session.duration}s")

    def update_session_counts(self) -> None:
        """
        Update pass/fail/skip counts on the current session based on test results.
        """
        if not self._current_session:
            return

        # Extracted smaller function to handle counting for each test result:
        for result in self._current_session.test_results.values():
            self._count_individual_result(result)

        self._current_session.total_collected = len(self._current_session.test_results)
        self._current_session.errors = len(self._current_session.collection_errors)
        logger.debug(f"Session results: {self._current_session}")

    def _count_individual_result(self, result: TestResult) -> None:
        """
        Increment the appropriate counters for a single TestResult.
        """
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

    def format_collection_errors(self) -> List[str]:
        """
        Format collection errors into lines suitable for display.

        Returns:
            List[str]: The formatted lines describing collection errors.
        """
        if not self._current_session:
            return []
        return [
            f"COLLECTION ERROR: {error}"
            for error in self._current_session.collection_errors
        ]

    def format_test_failures(self) -> List[str]:
        """
        Format test failure info into lines suitable for display.

        Returns:
            List[str]: The formatted lines describing test failures.
        """
        lines: List[str] = []
        if not self._current_session:
            return lines

        for test_id, result in self._current_session.test_results.items():
            if result.failed:
                file_path, test_name = test_id.split("::", 1)
                lines.append(f"FAILED {file_path} {test_name}")
                if result.error_message:
                    lines.append(f"E   {result.error_message}")
                if result.longrepr:
                    lines.append(result.longrepr)
        return lines

    # ----------------------------------------------------------------------
    # MAIN METHODS
    # ----------------------------------------------------------------------

    def capture_test_output(self) -> str:
        """Returns formatted test output that our parsers can handle"""
        output_lines = []
        # Add test collection output
        output_lines.extend(self.format_collection_errors())
        # Add test failures
        output_lines.extend(self.format_test_failures())
        return "\n".join(output_lines)

    def run_test(
        self, test_path: Optional[Path] = None, test_function: Optional[str] = None
    ) -> SessionResult:
        """
        Run pytest with detailed result capture.

        Args:
            test_path (Optional[Path]): The path to the test file or directory.
            test_function (Optional[str]): The specific test function to run.

        Returns:
            SessionResult: The result of the test session.
        """
        with self._lock:
            start_time = datetime.now()
            logger.info(f"Starting test run at {start_time}")

            # Initialize session
            self._current_session = SessionResult(
                start_time=start_time,
                end_time=start_time,
                duration=0.0,
                exit_code=ExitCode.OK,
            )

            try:
                # Register plugin
                plugin = PytestPlugin(self)

                # Build arguments
                args = self.build_pytest_args(test_path, test_function)
                logger.debug(f"Running pytest with arguments: {args}")

                # Run pytest
                exit_code_val = pytest.main(args, plugins=[plugin])

                # Finalize session
                self.finalize_session(start_time, exit_code_val)

                # Update session counts
                self.update_session_counts()

                # Capture and format test output
                self._current_session.output = self.capture_test_output()

                return self._current_session

            finally:
                logger.debug("Cleaning up after test run.")
                self.cleanup()

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """
        Hook to capture comprehensive test information during test execution.

        This method is called by pytest after each test phase (setup, call, teardown).
        """
        with self._lock:
            if not self._current_session:
                logger.warning("No active session to log test report.")
                return

            # Retrieve or create the TestResult object for this nodeid.
            result = self._current_session.test_results.get(report.nodeid)
            if not result:
                # Safely extract test_path and test_function with defaults
                test_path = Path(report.fspath) if report.fspath else Path("unknown")
                test_function = (
                    report.function.__name__
                    if hasattr(report, "function")
                    else "unknown"
                )

                result = TestResult(
                    nodeid=report.nodeid,
                    test_file=test_path,
                    test_function=test_function,
                    error_message=None,
                    longrepr=None,
                )
                self._current_session.test_results[report.nodeid] = result
                logger.debug(f"Created TestResult for {report.nodeid}")

            self._update_test_result_outcomes(result, report)

    def _update_test_result_outcomes(
        self, result: TestResult, report: TestReport
    ) -> None:
        """
        Smaller helper method to update the test outcomes and handle nested conditionals.
        """
        # Update phase results
        if report.when == "setup":
            result.setup_outcome = report.outcome
        elif report.when == "call":
            result.call_outcome = report.outcome
        elif report.when == "teardown":
            result.teardown_outcome = report.outcome

        # Capture outputs
        if report.capstdout:
            result.stdout = report.capstdout
            logger.debug(f"Captured stdout for {report.nodeid}: {report.capstdout}")
        if report.capstderr:
            result.stderr = report.capstderr
            logger.debug(f"Captured stderr for {report.nodeid}: {report.capstderr}")
        if hasattr(report, "caplog"):
            result.log_output = report.caplog
            logger.debug(f"Captured log output for {report.nodeid}: {report.caplog}")

        # Capture error information
        if report.longrepr:
            result.longrepr = str(report.longrepr)
            crash = getattr(report.longrepr, "reprcrash", None)
            if crash:
                # Extract only the exception message without file path and line number
                full_message = (
                    crash.message if hasattr(crash, "message") else str(crash)
                )
                result.error_message = full_message.split("\n")[0]
                logger.debug(
                    f"Captured error message for {report.nodeid}: {result.error_message}"
                )

        # Update execution info
        result.duration = report.duration
        logger.debug(f"Captured duration for {report.nodeid}: {result.duration}s")

        # Handle pass/xfail logic
        self._handle_outcome_logic(result, report)

    def _handle_outcome_logic(self, result: TestResult, report: TestReport) -> None:
        """
        Extracted method to handle all pass/fail/xfail logic for each reported outcome.
        """
        # A test is considered 'passed' if setup and teardown pass,
        # and the call is either passed or skipped.
        result.passed = (
            result.setup_outcome == "passed"
            and (result.call_outcome == "passed" or result.call_outcome == "skipped")
            and result.teardown_outcome == "passed"
        )

        # Handle xfail cases properly
        if hasattr(report, "wasxfail"):
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
            outcome == "failed"
            for outcome in [
                result.setup_outcome,
                result.call_outcome,
                result.teardown_outcome,
            ]
            if outcome is not None
        )

        # Capture test metadata
        if hasattr(report, "keywords"):
            result.markers = [
                name
                for name, marker in report.keywords.items()
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
        logger.info(f"Verifying fix for {test_file}::{test_function}")

        try:
            # Create subprocess command
            args = ["pytest", "--override-ini=addopts=", "-p", "no:terminal"]
            if self.working_dir:
                args.extend(["--rootdir", str(self.working_dir)])
            args.append(f"{str(test_file)}::{test_function}")

            # Run pytest synchronously
            result = subprocess.run(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # The test is considered fixed if pytest exits with code 0 (no failures)
            is_fixed = result.returncode == 0

            logger.info(
                f"Verification result for {test_file}::{test_function}: {is_fixed}"
            )
            if not is_fixed:
                logger.debug(f"Verification stdout:\n{result.stdout.decode()}")
                logger.debug(f"Verification stderr:\n{result.stderr.decode()}")

            return is_fixed

        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return False

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
            "",
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
                lines.extend(
                    [
                        f"FAILED {nodeid}",
                        "=" * (7 + len(nodeid)),
                        result.error_message or "",
                        result.longrepr or "",
                        "",
                    ]
                )

        report = "\n".join(lines)
        logger.debug("Formatted test report generated.")
        return report

    def pytest_collectreport(self, report: CollectReport) -> None:
        """
        Hook to capture collection information during test discovery.

        This method is called by pytest after attempting to collect tests.

        Args:
            report (CollectReport): The report object containing collection details.
        """
        with self._lock:
            if not self._current_session:
                logger.warning("No active session to log collect report.")
                return

            if report.outcome == "failed":
                error_message = str(report.longrepr)
                self._current_session.collection_errors.append(error_message)
                logger.error(f"Collection failed: {error_message}")

    def pytest_warning_recorded(self, warning_message: Warning) -> None:
        """
        Hook to capture test warnings during test execution.

        This method is called by pytest when a warning is recorded.

        Args:
            warning_message (Warning): The warning message object.
        """
        with self._lock:
            if self._current_session:
                self._current_session.warnings.append(str(warning_message))
                logger.warning(
                    f"Warning recorded during test execution: {warning_message}"
                )

    def cleanup(self) -> None:
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
                    logger.error(
                        f"Failed to remove temporary directory {temp_dir}: {e}"
                    )
        self.temp_dirs.clear()
        logger.info("Cleanup completed.")


TestRunner = PytestRunner
