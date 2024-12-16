from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import subprocess

@dataclass
class TestResult:
    """Results from a test run"""
    passed: bool
    output: str
    error_message: Optional[str] = None

class TestRunnerError(Exception):
    """Base exception for test runner errors"""
    pass

class TestRunner:
    """Manages pytest execution and result parsing"""

    def run_test(self, 
                test_file: Path, 
                test_function: Optional[str] = None,
                capture_output: bool = True) -> TestResult:
        """Run pytest for specific test file/function.
        
        Args:
            test_file: Path to test file to run
            test_function: Optional specific test to run
            capture_output: Whether to capture output
            
        Returns:
            TestResult containing execution results
            
        Raises:
            FileNotFoundError: If test file missing
            TestRunnerError: If pytest execution fails
        """
        raise NotImplementedError()
    
    def _build_command(self, 
                      test_file: Path,
                      test_function: Optional[str] = None) -> List[str]:
        """Build pytest command with proper options.
        
        Args:
            test_file: Test file path
            test_function: Optional test function name
            
        Returns:
            List of command arguments
            
        Raises:
            ValueError: If invalid arguments provided
        """
        raise NotImplementedError()
    
    def _execute_test(self, command: List[str]) -> subprocess.CompletedProcess:
        """Execute pytest command.
        
        Args:
            command: Command arguments to execute
            
        Returns:
            CompletedProcess with results
            
        Raises:
            subprocess.SubprocessError: If execution fails
            TestRunnerError: For other execution errors
        """
        raise NotImplementedError()
    
    def _parse_result(self, 
                     completed: subprocess.CompletedProcess) -> TestResult:
        """Parse pytest execution results.
        
        Args:
            completed: CompletedProcess from execution
            
        Returns:
            TestResult with parsed information
        """
        raise NotImplementedError()