import os
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, call, patch

import pytest

from branch_fixer.orchestration.fix_service import FixService, FixServiceError
from branch_fixer.orchestration.orchestrator import FixSession, FixSessionState
from branch_fixer.core.models import TestError, ErrorDetails, CodeChanges
from branch_fixer.storage.state_manager import StateTransitionError, StateValidationError


# Module-level fixtures
@pytest.fixture
def tmp_file(tmp_path):
    """
    Create a real Python test file named `test_sample.py` in the given temporary directory.
    
    Parameters:
        tmp_path (pathlib.Path): Temporary directory path provided by pytest.
    
    Returns:
        pathlib.Path: Path to the created test file containing a simple passing test.
    """
    p = tmp_path / "test_sample.py"
    p.write_text("def test_example():\n    assert 1 == 1\n", encoding="utf-8")
    return p


@pytest.fixture
def fake_ai_manager():
    """
    Create a mock AI manager whose `generate_fix` returns a default `CodeChanges`.
    
    The mock's `generate_fix` method returns a `CodeChanges` instance with `original_code` set to an empty string and `modified_code` set to "print('fixed')\n".
    
    Returns:
        Mock: A mock object with a `generate_fix` method that returns the default `CodeChanges`.
    """
    m = Mock()
    # Default: return a simple CodeChanges
    m.generate_fix = Mock(return_value=CodeChanges(original_code="", modified_code="print('fixed')\n"))
    return m


@pytest.fixture
def fake_change_applier(tmp_path):
    """
    Create a mocked change applier that simulates a successful apply with an existing backup file.
    
    Parameters:
        tmp_path (Path): Temporary directory in which a fake backup file will be created.
    
    Returns:
        Mock: A Mock object with:
            - apply_changes_with_backup returning (True, Path) where Path points to an existing backup file.
            - restore_backup returning True.
    """
    m = Mock()
    # Simulate a successful apply by default returning (True, backup_path)
    backup_dir = tmp_path / ".backups"
    backup_dir.mkdir(exist_ok=True)
    fake_backup = backup_dir / "test_sample.py-backup.bak"
    fake_backup.write_text("original", encoding="utf-8")
    m.apply_changes_with_backup = Mock(return_value=(True, fake_backup))
    m.restore_backup = Mock(return_value=True)
    return m


@pytest.fixture
def fake_test_runner():
    """
    Create a test double for a test runner whose verification succeeds by default.
    
    Returns:
        Mock: A Mock object with a `verify_fix` method that returns `True` by default.
    """
    m = Mock()
    # Default verification success
    m.verify_fix = Mock(return_value=True)
    return m


@pytest.fixture
def session_store_mock():
    """
    Create a mock session store with a `save_session` stub.
    
    Returns:
        Mock: A mock object representing a session store; its `save_session` attribute is a `Mock` for asserting calls.
    """
    m = Mock()
    m.save_session = Mock()
    return m


@pytest.fixture
def state_manager_mock():
    """
    Create a mock state manager whose `transition_state` method succeeds.
    
    The returned Mock has a `transition_state` attribute that returns `True` when called.
    
    Returns:
        Mock: A mock object representing a state manager with `transition_state` stubbed to return `True`.
    """
    m = Mock()
    m.transition_state = Mock(return_value=True)
    return m


@pytest.fixture
def workspace_validator_ok():
    """
    Create a simple workspace validator stub used in tests.
    
    This returns an object exposing two no-op methods used to simulate workspace validation:
    - `validate_workspace(path)`: accepts a path and performs no validation (returns None).
    - `check_dependencies()`: performs no dependency checks (returns None).
    
    Returns:
        validator (object): An instance with `validate_workspace(path)` and `check_dependencies()` methods that always return None.
    """
    class V:
        def validate_workspace(self, path):
            """
            Validate that the workspace at `path` is ready for applying fixes.
            
            Parameters:
                path (str | pathlib.Path): Filesystem path to the workspace to validate.
            
            Raises:
                OSError, PermissionError, or other exceptions when the workspace is invalid or inaccessible.
            """
            return None

        def check_dependencies(self):
            """
            Performs checks that required external dependencies for the workspace are available and usable.
            
            Raises:
                Exception: If one or more required dependencies are missing or incompatible.
            """
            return None

    return V()


class TestFixService:
    """Tests for branch_fixer.orchestration.fix_service.FixService"""

    # Happy path: constructor valid parameters
    def test_init_valid_params_sets_attributes(self, fake_ai_manager, fake_test_runner, fake_change_applier):
        svc = FixService(
            ai_manager=fake_ai_manager,
            test_runner=fake_test_runner,
            change_applier=fake_change_applier,
            git_repo=Mock(),
            max_retries=2,
            initial_temp=0.2,
            temp_increment=0.1,
            dev_force_success=False,
            session_store=None,
            state_manager=None,
            session=None,
        )
        assert svc.ai_manager is fake_ai_manager
        assert svc.test_runner is fake_test_runner
        assert svc.change_applier is fake_change_applier
        assert svc.max_retries == 2
        assert svc.initial_temp == pytest.approx(0.2)
        assert svc.temp_increment == pytest.approx(0.1)
        assert svc.dev_force_success is False

    # Edge cases: invalid constructor parameters
    @pytest.mark.parametrize(
        "max_retries,initial_temp,temp_increment,err_msg",
        [
            (0, 0.4, 0.1, "max_retries must be positive"),
            (3, -0.1, 0.1, "initial_temp must be between 0 and 1"),
            (3, 0.4, 0.0, "temp_increment must be positive"),
            (3, 1.1, 0.1, "initial_temp must be between 0 and 1"),
        ],
    )
    def test_init_invalid_params_raise_value_error(
        self, max_retries, initial_temp, temp_increment, err_msg, fake_ai_manager, fake_test_runner, fake_change_applier
    ):
        """
        Verifies that constructing FixService with invalid retry/temperature parameters raises ValueError containing the expected message fragment.
        
        Parameters:
            max_retries (int): The max_retries value passed to the constructor (tested invalid values).
            initial_temp (float): The initial temperature passed to the constructor (tested out-of-range values).
            temp_increment (float): The temperature increment passed to the constructor (tested invalid values).
            err_msg (str): Substring expected to appear in the raised ValueError message.
        """
        with pytest.raises(ValueError) as exc:
            FixService(
                ai_manager=fake_ai_manager,
                test_runner=fake_test_runner,
                change_applier=fake_change_applier,
                git_repo=Mock(),
                max_retries=max_retries,
                initial_temp=initial_temp,
                temp_increment=temp_increment,
            )
        assert err_msg in str(exc.value)

    # attempt_fix happy path when dev_force_success True
    def test_attempt_fix_dev_force_success_marks_fixed_and_updates_session(
        self, tmp_file, fake_ai_manager, fake_change_applier, fake_test_runner, session_store_mock, state_manager_mock, workspace_validator_ok
    ):
        error_details = ErrorDetails(error_type="AssertionError", message="fail")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)
        session = FixSession()
        session.errors = [error]
        session.completed_errors = []

        svc = FixService(
            ai_manager=fake_ai_manager,
            test_runner=fake_test_runner,
            change_applier=fake_change_applier,
            git_repo=Mock(),
            dev_force_success=True,
            session_store=session_store_mock,
            state_manager=state_manager_mock,
            session=session,
        )
        # Override validator with no-op
        svc.validator = workspace_validator_ok

        result = svc.attempt_fix(error, temperature=0.3)
        assert result is True
        assert error.status == "fixed"
        # There should be a successful attempt recorded
        assert any(attempt.status == "success" for attempt in error.fix_attempts)
        # Session should have been updated
        assert error in session.completed_errors
        session_store_mock.save_session.assert_called_once_with(session)

    # attempt_fix workspace validation failure should raise FixServiceError
    def test_attempt_fix_workspace_validation_failure_raises_fixserviceerror(
        self, tmp_file, fake_ai_manager, fake_change_applier, fake_test_runner
    ):
        error_details = ErrorDetails(error_type="ImportError", message="missing")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)

        svc = FixService(
            ai_manager=fake_ai_manager,
            test_runner=fake_test_runner,
            change_applier=fake_change_applier,
            git_repo=Mock(),
        )
        # Make validator raise
        svc.validator.validate_workspace = Mock(side_effect=OSError("no access"))
        svc.validator.check_dependencies = Mock()  # not reached

        with pytest.raises(FixServiceError) as exc:
            svc.attempt_fix(error, temperature=0.2)
        # Accept either the contextual message or the original OSError message
        msg = str(exc.value)
        assert "Workspace validation failed" in msg or "no access" in msg

    # attempt_fix where AI returns changes but apply_changes_with_backup returns (False, None)
    def test_attempt_fix_apply_returns_false_marks_attempt_failed(
        self, tmp_file, fake_ai_manager, fake_change_applier, fake_test_runner, workspace_validator_ok, session_store_mock
    ):
        error_details = ErrorDetails(error_type="AssertionError", message="fail")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)
        session = FixSession()
        session.errors = [error]
        session.completed_errors = []

        svc = FixService(
            ai_manager=fake_ai_manager,
            test_runner=fake_test_runner,
            change_applier=fake_change_applier,
            git_repo=Mock(),
            session_store=session_store_mock,
            session=session,
        )
        svc.validator = workspace_validator_ok

        # Simulate apply failing (no backup created)
        fake_change_applier.apply_changes_with_backup.return_value = (False, None)

        result = svc.attempt_fix(error, temperature=0.4)
        assert result is False
        # latest attempt should be present and marked failed
        assert error.fix_attempts, "No attempt recorded"
        assert error.fix_attempts[-1].status == "failed"
        # restore_backup should not have been called since backup_path is None
        fake_change_applier.restore_backup.assert_not_called()
        # session store should have been called via _update_session_if_present
        session_store_mock.save_session.assert_called_once_with(session)

    # attempt_fix where apply succeeds but verification fails: should restore backup and return False
    def test_attempt_fix_apply_success_but_verification_fails_restores_and_returns_false(
        self, tmp_file, fake_ai_manager, fake_change_applier, fake_test_runner, workspace_validator_ok
    ):
        # Write original content to file
        original = "def test_example():\n    assert 1 == 1\n"
        tmp_file.write_text(original, encoding="utf-8")

        error_details = ErrorDetails(error_type="AssertionError", message="fail")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)

        svc = FixService(
            ai_manager=fake_ai_manager,
            test_runner=fake_test_runner,
            change_applier=fake_change_applier,
            git_repo=Mock(),
        )
        svc.validator = workspace_validator_ok

        # apply changes returns success with a real-looking backup path
        # Create a backup file so restore_backup has a path that exists
        backup_dir = tmp_file.parent / ".backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / "backup.bak"
        backup_path.write_text(original, encoding="utf-8")
        fake_change_applier.apply_changes_with_backup.return_value = (True, backup_path)

        # test_runner.verify_fix returns False (functional tests still fail)
        svc.test_runner.verify_fix = Mock(return_value=False)

        result = svc.attempt_fix(error, temperature=0.5)
        assert result is False
        # restore_backup should have been called with the same backup_path
        fake_change_applier.restore_backup.assert_called_once_with(tmp_file, backup_path)
        # file content should have been restored
        assert tmp_file.read_text(encoding="utf-8") == original
        # attempt should be marked failed
        assert error.fix_attempts[-1].status == "failed"

    # attempt_fix where apply and verify succeed: marks fixed and updates session/state
    def test_attempt_fix_apply_and_verify_success_marks_fixed_and_updates_session_and_state_manager(
        self, tmp_file, fake_ai_manager, fake_change_applier, fake_test_runner, workspace_validator_ok, session_store_mock, state_manager_mock
    ):
        error_details = ErrorDetails(error_type="AssertionError", message="fail")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)
        session = FixSession()
        session.errors = [error]
        session.completed_errors = []

        svc = FixService(
            ai_manager=fake_ai_manager,
            test_runner=fake_test_runner,
            change_applier=fake_change_applier,
            git_repo=Mock(),
            session_store=session_store_mock,
            state_manager=state_manager_mock,
            session=session,
        )
        svc.validator = workspace_validator_ok

        # apply and verify succeed
        fake_change_applier.apply_changes_with_backup.return_value = (True, Path("/tmp/some.bak"))
        svc.test_runner.verify_fix.return_value = True

        result = svc.attempt_fix(error, temperature=0.2)
        assert result is True
        assert error.status == "fixed"
        assert any(attempt.status == "success" for attempt in error.fix_attempts)
        # session updated
        assert error in session.completed_errors
        # state_manager.transition_state should have been called because completed == errors
        state_manager_mock.transition_state.assert_called()
        session_store_mock.save_session.assert_called_once_with(session)

    # attempt_fix inner exception after applying changes: should call handle_failed_attempt, restore backup, and raise FixServiceError
    def test_attempt_fix_inner_exception_after_applying_raises_and_restores_backup(
        self, tmp_file, fake_ai_manager, fake_change_applier, workspace_validator_ok
    ):
        error_details = ErrorDetails(error_type="RuntimeError", message="boom")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)

        svc = FixService(
            ai_manager=fake_ai_manager,
            test_runner=Mock(),  # will raise
            change_applier=fake_change_applier,
            git_repo=Mock(),
        )
        svc.validator = workspace_validator_ok

        # apply returns success and a backup
        backup_dir = tmp_file.parent / ".backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / "b.bak"
        backup_path.write_text("orig", encoding="utf-8")
        fake_change_applier.apply_changes_with_backup.return_value = (True, backup_path)

        # test_runner.verify_fix will raise an unexpected error
        svc.test_runner.verify_fix = Mock(side_effect=RuntimeError("subprocess fail"))

        with pytest.raises(FixServiceError):
            svc.attempt_fix(error, temperature=0.3)

        # restore_backup should have been attempted despite the exception
        fake_change_applier.restore_backup.assert_called_once_with(tmp_file, backup_path)
        # attempt should be recorded and marked failed
        assert error.fix_attempts[-1].status == "failed"

    # attempt_manual_fix happy path: verification True leads to mark_fixed and session update
    def test_attempt_manual_fix_verification_passes_marks_fixed_and_updates_session(
        self, tmp_file, fake_test_runner, session_store_mock, state_manager_mock, workspace_validator_ok
    ):
        error_details = ErrorDetails(error_type="AssertionError", message="fail")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)
        session = FixSession()
        session.errors = [error]
        session.completed_errors = []

        svc = FixService(
            ai_manager=Mock(),
            test_runner=fake_test_runner,
            change_applier=Mock(),
            git_repo=Mock(),
            session_store=session_store_mock,
            state_manager=state_manager_mock,
            session=session,
        )
        svc.validator = workspace_validator_ok

        # verify_fix returns True
        fake_test_runner.verify_fix.return_value = True

        result = svc.attempt_manual_fix(error)
        assert result is True
        assert error.status == "fixed"
        assert error in session.completed_errors
        session_store_mock.save_session.assert_called_once_with(session)

    # attempt_manual_fix when verification fails returns False and does not mark fixed
    def test_attempt_manual_fix_verification_fails_returns_false_and_no_mark(
        self, tmp_file, fake_test_runner, workspace_validator_ok
    ):
        error_details = ErrorDetails(error_type="AssertionError", message="fail")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)
        svc = FixService(
            ai_manager=Mock(),
            test_runner=fake_test_runner,
            change_applier=Mock(),
            git_repo=Mock(),
        )
        svc.validator = workspace_validator_ok

        fake_test_runner.verify_fix.return_value = False

        result = svc.attempt_manual_fix(error)
        assert result is False
        # No attempts started, status remains unfixed
        assert error.status != "fixed"
        assert not error.fix_attempts or error.fix_attempts[-1].status != "success"

    # attempt_manual_fix workspace validation failure raises FixServiceError
    def test_attempt_manual_fix_workspace_validation_failure_raises(
        self, tmp_file, fake_test_runner
    ):
        error_details = ErrorDetails(error_type="ImportError", message="missing")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)

        svc = FixService(
            ai_manager=Mock(),
            test_runner=fake_test_runner,
            change_applier=Mock(),
            git_repo=Mock(),
        )
        svc.validator.validate_workspace = Mock(side_effect=PermissionError("nope"))
        svc.validator.check_dependencies = Mock()

        with pytest.raises(FixServiceError):
            svc.attempt_manual_fix(error)

    # _handle_failed_attempt should raise FixServiceError if update_session raises
    def test_handle_failed_attempt_propagates_update_errors_as_fixserviceerror(
        self, tmp_file, workspace_validator_ok
    ):
        error_details = ErrorDetails(error_type="ValueError", message="bad")
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=error_details)

        svc = FixService(
            ai_manager=Mock(),
            test_runner=Mock(),
            change_applier=Mock(),
            git_repo=Mock(),
        )
        svc.validator = workspace_validator_ok

        # Make _update_session_if_present raise an exception
        svc._update_session_if_present = Mock(side_effect=RuntimeError("save failed"))

        attempt = error.start_fix_attempt(0.1)
        with pytest.raises(FixServiceError) as exc:
            svc._handle_failed_attempt(error, attempt)
        assert "Failed to handle failed attempt" in str(exc.value)

    # _verify_fix returns boolean on success and raises FixServiceError on underlying exception
    def test_verify_fix_behavior(self, tmp_file):
        svc = FixService(ai_manager=Mock(), test_runner=Mock(), change_applier=Mock(), git_repo=Mock())
        # Happy path: test_runner.verify_fix returns True
        svc.test_runner.verify_fix = Mock(return_value=True)
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=ErrorDetails(error_type="", message=""))
        attempt = error.start_fix_attempt(0.2)
        assert svc._verify_fix(error, attempt) is True

        # Error path: test_runner.verify_fix raises -> _verify_fix should raise FixServiceError
        svc.test_runner.verify_fix = Mock(side_effect=RuntimeError("boom"))
        with pytest.raises(FixServiceError) as exc:
            svc._verify_fix(error, attempt)
        assert "Fix verification failed" in str(exc.value)

    # _update_session_if_present: no session => no-op
    def test_update_session_if_no_session_is_noop(self, tmp_file):
        svc = FixService(ai_manager=Mock(), test_runner=Mock(), change_applier=Mock(), git_repo=Mock())
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=ErrorDetails(error_type="", message=""))
        # No session attached
        svc.session = None
        # Should simply return without error
        svc._update_session_if_present(error)  # does not raise

    # _update_session_if_present: with session and state_manager raising transition errors should be caught
    def test_update_session_with_state_transition_errors_is_handled_and_session_store_still_called(
        self, tmp_file, session_store_mock
    ):
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=ErrorDetails(error_type="", message=""))
        session = FixSession()
        session.errors = [error]
        session.completed_errors = []
        svc = FixService(ai_manager=Mock(), test_runner=Mock(), change_applier=Mock(), git_repo=Mock(), session_store=session_store_mock, state_manager=Mock(), session=session)
        # Mark the error as fixed to trigger transition logic
        error.status = "fixed"
        # Make state_manager.transition_state raise StateTransitionError
        svc.state_manager.transition_state = Mock(side_effect=StateTransitionError("invalid"))
        # session_store.save_session should be called even if transition fails
        svc._update_session_if_present(error)
        session_store_mock.save_session.assert_called_once_with(session)
        # Completed errors should include the error
        assert error in session.completed_errors

    # _update_session_if_present: session_store.save_session raising should propagate
    def test_update_session_store_failure_propagates(self, tmp_file):
        error = TestError(test_file=tmp_file, test_function="test_example", error_details=ErrorDetails(error_type="", message=""))
        session = FixSession()
        session.errors = [error]
        session.completed_errors = []
        failing_store = Mock()
        failing_store.save_session = Mock(side_effect=RuntimeError("disk full"))
        svc = FixService(ai_manager=Mock(), test_runner=Mock(), change_applier=Mock(), git_repo=Mock(), session_store=failing_store, state_manager=None, session=session)
        error.status = "fixed"
        with pytest.raises(RuntimeError):
            svc._update_session_if_present(error)