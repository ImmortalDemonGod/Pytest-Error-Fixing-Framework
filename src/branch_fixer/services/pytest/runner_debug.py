# src/branch_fixer/services/pytest/runner_debug.py
import snoop
from pathlib import Path
from branch_fixer.services.pytest.runner import PytestRunner

@snoop(depth=2)
def run_test_and_show_results(runner, test_path, test_function=None):
    """Helper function to run a test synchronously and show results"""
    
    print(f"\nRunning test file: {test_path}")
    if test_function:
        print(f"Testing specific function: {test_function}")
        
    
    result = runner.run_test(test_path=test_path, test_function=test_function)
    
    print("\nTest Results:")
    print(runner.format_report(result))
    return result

def main():
    # Initialize with current directory
    current_dir = Path("/Volumes/Totallynotaharddrive/Pytest-Error-Fixing-Framework/src/branch_fixer/services/pytest")
    runner = PytestRunner(working_dir=current_dir)
    
    # Test 1: Simple test file
    run_test_and_show_results(
        runner,
        test_path=current_dir / "test_simple.py"
    )
    
    # Test 2: Fixtures test file
    run_test_and_show_results(
        runner,
        test_path=current_dir / "test_fixtures.py"
    )
    
    # Test 3: Specific test function
    run_test_and_show_results(
        runner,
        test_path=current_dir / "test_simple.py",
        test_function="test_add_simple"
    )

if __name__ == "__main__":
    main()