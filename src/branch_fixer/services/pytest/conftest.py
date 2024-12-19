import pytest
import pytest_asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock
from textwrap import dedent

from _pytest.reports import TestReport
from _pytest.main import ExitCode

# Configure pytest-asyncio
pytest_plugins = ['pytest_asyncio']

@pytest.fixture
def mock_test_report():
    """Create a mock TestReport for testing."""
    report = Mock(spec=TestReport)
    report.nodeid = "test_file.py::test_function"
    report.fspath = "test_file.py"
    report.function = Mock(__name__="test_function")
    report.when = "call"
    report.outcome = "passed"
    report.passed = True
    report.failed = False
    report.skipped = False
    report.capstdout = "Test output"
    report.capstderr = ""
    report.duration = 0.1
    report.longrepr = None
    report.keywords = {}
    return report

@pytest.fixture
async def test_suite_dir(tmp_path_factory):
    """Create a directory with real test scenarios."""
    # Use tmp_path_factory instead of tmp_path for better async support
    tmp_path = tmp_path_factory.mktemp("test_suite")
    
    # Basic passing test
    passing = tmp_path / "test_passing.py"
    passing.write_text(dedent("""
        def test_simple_pass():
            assert 1 + 1 == 2
            print("stdout capture")
    """))

    # Test with setup/teardown
    setup = tmp_path / "test_setup.py"
    setup.write_text(dedent("""
        import pytest

        @pytest.fixture
        def setup_data():
            print("Setting up")
            yield "test data"
            print("Tearing down")

        def test_with_fixture(setup_data):
            assert setup_data == "test data"
    """))

    # Parameterized test
    params = tmp_path / "test_params.py"
    params.write_text(dedent("""
        import pytest

        @pytest.mark.parametrize("input,expected", [
            (1, 2),
            (2, 3),
            pytest.param(3, 5, marks=pytest.mark.xfail),
        ])
        def test_increment(input, expected):
            assert input + 1 == expected
    """))

    return tmp_path

@pytest_asyncio.fixture
async def runner(test_suite_dir):
    """Create PytestRunner instance with test directory."""
    from branch_fixer.services.pytest.runner import PytestRunner
    return PytestRunner(working_dir=test_suite_dir)

# Add cleanup fixture to handle directory removal issues
@pytest.fixture(autouse=True)
async def cleanup(request):
    """Clean up test directories after each test."""
    yield
    # Clean up temp directories explicitly
    if hasattr(request, 'node'):
        test_dir = getattr(request.node, 'test_dir', None)
        if test_dir and test_dir.exists():
            try:
                for item in test_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    else:
                        for subitem in item.iterdir():
                            subitem.unlink()
                        item.rmdir()
                test_dir.rmdir()
            except OSError:
                pass  # Ignore cleanup errors