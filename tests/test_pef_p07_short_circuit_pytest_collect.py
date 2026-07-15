"""RED test for F87: FixOrchestrator.fix_error() must short-circuit CollectionError-typed
TestErrors before any AI-fix call or retry-budget consumption.

audit/02-static-audit.md#L50 (F87) — see
tests/pef-p07-short-circuit-pytest-collect.bug-catalog.md for the full bug catalog.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from branch_fixer.core.models import ErrorDetails, TestError
from branch_fixer.orchestration.orchestrator import FixOrchestrator


def test_fix_error_collection_error_short_circuits_without_ai_call_or_retry():
    # Explicit, caller-supplied CollectionError TestError (per the plan's §12 test-layer
    # contract: the unit under test consumes error.error_details.error_type, so it is set
    # explicitly here rather than derived from a fixture default).
    error_details = ErrorDetails(
        error_type="CollectionError",
        message="collected boom",
        stack_trace=None,
    )
    error = TestError(
        test_file=Path("unknown_collection_file.py"),
        test_function="pytest_collection",
        error_details=error_details,
    )

    ai_manager = Mock()
    # change_applier must behave like the real ChangeApplier for a non-existent sentinel
    # path (apply_changes_with_backup returns (False, None)) so that, absent the guard under
    # test, fix_error()'s retry loop runs to completion cleanly instead of raising, and the
    # test can observe the actual bug (generate_fix IS called) via a clean AssertionError.
    change_applier = Mock()
    change_applier.apply_changes_with_backup = Mock(return_value=(False, None))
    test_runner = SimpleNamespace()
    git_repo = SimpleNamespace()

    orch = FixOrchestrator(
        ai_manager=ai_manager,
        test_runner=test_runner,
        change_applier=change_applier,
        git_repo=git_repo,
    )
    session = orch.start_session([error])

    # Uses the real FixOrchestrator -> FixService -> AIManager call chain (no
    # _inject_fake_fix_service-style monkeypatching of sys.modules) so the assertion below is
    # a genuine proof that the guard prevents the AI call, not a vacuous pass.
    # WorkspaceValidator's real git-root discovery is unrelated to the guard under test and
    # fails in a git-worktree checkout (".git" is a file, not a dir) — stub it out so the test
    # exercises fix_error()'s CollectionError handling rather than an unrelated environment
    # quirk in FixService.attempt_fix()'s workspace-validation step.
    with patch(
        "branch_fixer.utils.workspace.WorkspaceValidator.validate_workspace",
        return_value=None,
    ), patch(
        "branch_fixer.utils.workspace.WorkspaceValidator.check_dependencies",
        return_value=None,
    ):
        result = orch.fix_error(error)

    assert result is False
    ai_manager.generate_fix.assert_not_called()
    assert session.retry_count == 0
