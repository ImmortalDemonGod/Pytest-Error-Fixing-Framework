"""RED tests for the bundled finding (F65, F79, F10): a zero-coverage test
file, a duplicated/misplaced git fixture block, and duplicate
UnifiedErrorParser test modules.
"""
import importlib
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent


def test_math_operations_file_is_removed():
    """F65: tests/test_math_operations.py tests a locally-defined add() and
    imports nothing from src/, so it contributes no coverage and should not
    exist in the suite."""
    assert not (TESTS_ROOT / "test_math_operations.py").exists(), (
        "tests/test_math_operations.py contributes no coverage of src/ and "
        "should have been removed"
    )


def test_integration_pytest_conftest_does_not_define_git_fixtures():
    """F79: tests/integration/pytest/conftest.py must only define
    integration-scope PytestRunner fixtures. clean_repo/branch_manager are
    unit-git fixtures that belong exclusively in tests/unit/git/conftest.py;
    the duplicated copy here references GitRepository.create_branch, which
    does not exist (only create_fix_branch does), so it raises AttributeError
    the moment it is actually used."""
    mod = importlib.import_module("tests.integration.pytest.conftest")

    assert not hasattr(mod, "clean_repo"), (
        "clean_repo is misplaced in tests/integration/pytest/conftest.py; "
        "it belongs only in tests/unit/git/conftest.py"
    )
    assert not hasattr(mod, "branch_manager"), (
        "branch_manager is misplaced in tests/integration/pytest/conftest.py; "
        "it belongs only in tests/unit/git/conftest.py"
    )


def test_only_one_unified_error_parser_test_module_exists():
    """F10: two test files cover the same production class
    (UnifiedErrorParser); only the more comprehensive module should remain."""
    duplicate = TESTS_ROOT / "unit" / "pytest" / "parsers" / "test_unified_error_parser.py"
    canonical = TESTS_ROOT / "unit" / "services" / "pytest" / "test_unified_error_parser.py"

    assert canonical.exists()
    assert not duplicate.exists(), (
        f"{duplicate} duplicates coverage already provided by {canonical}"
    )
