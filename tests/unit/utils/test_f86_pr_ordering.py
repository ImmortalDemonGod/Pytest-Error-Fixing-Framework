# tests/unit/utils/test_f86_pr_ordering.py
#
# RED tests for F86: cli.py:220-226 invokes `gh pr create` (via
# create_pull_request_sync) BEFORE pushing the branch to the remote, causing
# GitHub to reject the PR because the head branch does not yet exist remotely.
#
# Canonical intent (Class E):
# https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/
# 697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L15
#
# Bug catalog: tests/unit/utils/test_f86_pr_ordering.bug-catalog.md

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from branch_fixer.core.models import ErrorDetails, TestError
from branch_fixer.utils.cli import CLI


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_error(tmp_path: Path) -> TestError:
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_dummy(): assert True\n")
    details = ErrorDetails(
        error_type="AssertionError",
        message="assert failed",
        stack_trace=None,
    )
    return TestError(
        test_file=test_file,
        test_function="test_dummy",
        error_details=details,
    )


@pytest.fixture()
def cli_with_mock_service(sample_error: TestError) -> CLI:
    """CLI instance whose git_repo collaborators are MagicMock stubs."""
    cli = CLI()
    svc = MagicMock()
    svc.git_repo.push.return_value = True
    svc.git_repo.create_pull_request_sync.return_value = MagicMock()  # truthy PRDetails
    cli.service = svc
    return cli


# ---------------------------------------------------------------------------
# B1 — push MUST be called before create_pull_request_sync
# (guards against 'branch not on remote' rejection by GitHub gh CLI)
# ---------------------------------------------------------------------------


class TestPushBeforePRCreation:
    def test_push_called_before_create_pull_request_sync_guards_against_branch_not_on_remote(
        self,
        cli_with_mock_service: CLI,
        sample_error: TestError,
    ) -> None:
        """B1: _create_and_push_pr must push the branch before calling gh pr create.

        Current bug: create_pull_request_sync (which runs gh pr create) is invoked
        at cli.py:220 while push is only called at cli.py:226.  GitHub rejects the
        PR because the head branch does not exist on the remote yet.

        This test records the order of collaborator calls and asserts push precedes
        create_pull_request_sync.  It will be RED against the current code because
        the actual order is ['pr', 'push'] not ['push', 'pr'].
        """
        call_order: list[str] = []

        git_repo = cli_with_mock_service.service.git_repo  # type: ignore[union-attr]
        git_repo.push.side_effect = lambda *a, **kw: call_order.append("push") or True
        git_repo.create_pull_request_sync.side_effect = (
            lambda *a, **kw: call_order.append("pr") or MagicMock()
        )

        cli_with_mock_service._create_and_push_pr("fix-branch", sample_error)

        assert call_order == ["push", "pr"], (
            f"push must precede pr creation so the branch exists on the remote "
            f"when gh pr create runs; actual order was {call_order!r}"
        )


# ---------------------------------------------------------------------------
# B2 — push failure must short-circuit and prevent pr creation
# (guards against a dangling GitHub PR with no pushable branch)
# ---------------------------------------------------------------------------


class TestPushFailurePreventsGhPRCreate:
    def test_create_pull_request_sync_not_called_when_push_fails_guards_against_ghost_pr(
        self,
        cli_with_mock_service: CLI,
        sample_error: TestError,
    ) -> None:
        """B2: if push fails, create_pull_request_sync must NOT be called.

        Current bug: create_pull_request_sync is called first (cli.py:220), so
        gh pr create is always attempted regardless of whether push will succeed.
        In the fixed ordering, a push failure must be detected first and must
        short-circuit before creating the PR.

        This test will be RED against the current code because
        create_pull_request_sync IS called (before push is even attempted).
        """
        git_repo = cli_with_mock_service.service.git_repo  # type: ignore[union-attr]
        git_repo.push.return_value = False

        result = cli_with_mock_service._create_and_push_pr("fix-branch", sample_error)

        git_repo.create_pull_request_sync.assert_not_called()
        assert result is False, (
            "push failure must propagate as False return — no PR should be created"
        )
