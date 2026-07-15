"""RED test for finding F23/F85/F29 (pef-p11-remove-dev-force-success-byp).

PRD Phase 2 (.taskmaster/docs/prd.txt L179-184) and
audit/02-static-audit.md L24 mandate: FixService must always call the AI
service to generate a fix. There must be no `dev_force_success` short-circuit
that marks an error "fixed" without invoking AIManager.generate_fix.

Currently src/branch_fixer/orchestration/fix_service.py:116-122 skips
generate_fix entirely and marks the error fixed when dev_force_success is
True. This test asserts the CORRECT behavior (generate_fix is always
called) and therefore fails against the current, buggy code.
"""

from unittest.mock import Mock

import pytest

from branch_fixer.core.models import CodeChanges, ErrorDetails, TestError
from branch_fixer.orchestration.fix_service import FixService


@pytest.fixture
def tmp_file(tmp_path):
    p = tmp_path / "test_sample.py"
    p.write_text("def test_example():\n    assert 1 == 1\n", encoding="utf-8")
    return p


@pytest.fixture
def fake_ai_manager():
    m = Mock()
    m.generate_fix = Mock(
        return_value=CodeChanges(original_code="", modified_code="print('fixed')\n")
    )
    return m


@pytest.fixture
def fake_change_applier(tmp_path):
    m = Mock()
    backup_dir = tmp_path / ".backups"
    backup_dir.mkdir(exist_ok=True)
    fake_backup = backup_dir / "test_sample.py-backup.bak"
    fake_backup.write_text("original", encoding="utf-8")
    m.apply_changes_with_backup = Mock(return_value=(True, fake_backup))
    m.restore_backup = Mock(return_value=True)
    return m


@pytest.fixture
def fake_test_runner():
    m = Mock()
    m.verify_fix = Mock(return_value=True)
    return m


@pytest.fixture
def workspace_validator_ok():
    """No-op validator so the test exercises attempt_fix's dev_force_success
    branch logic without depending on a real git repo existing at tmp_path."""

    class V:
        def validate_workspace(self, path):
            return None

        def check_dependencies(self):
            return None

    return V()


def test_attempt_fix_always_calls_generate_fix_no_dev_force_shortcut(
    tmp_file, fake_ai_manager, fake_change_applier, fake_test_runner, workspace_validator_ok
):
    """attempt_fix must always invoke AIManager.generate_fix — no
    dev_force_success short-circuit is allowed, even when a caller
    explicitly sets dev_force_success=True."""
    svc = FixService(
        ai_manager=fake_ai_manager,
        test_runner=fake_test_runner,
        change_applier=fake_change_applier,
        git_repo=Mock(),
        max_retries=2,
        initial_temp=0.2,
        temp_increment=0.1,
        dev_force_success=True,
    )
    svc.validator = workspace_validator_ok

    error_details = ErrorDetails(error_type="AssertionError", message="fail")
    error = TestError(
        test_file=tmp_file, test_function="test_example", error_details=error_details
    )

    result = svc.attempt_fix(error, temperature=0.2)

    assert result is True
    fake_ai_manager.generate_fix.assert_called_once()
