import pytest
from unittest.mock import patch

import branch_fixer.services.git.repository as repository_module
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.git.models import CommandResult
from branch_fixer.services.git.exceptions import GitError


class TestPush:
    def test_push_raises_giterror_on_command_failure(self):
        gr = repository_module.GitRepository.__new__(GitRepository)

        failing_result = CommandResult(
            returncode=1,
            stdout="",
            stderr="remote: rejected",
            command=["git", "push", "origin", "mybranch"],
        )
        # Patch at the subprocess boundary (not run_command itself) so the
        # real run_command -> _check_command_error GitError-raising path executes.
        with patch.object(GitRepository, "_execute_subprocess", return_value=failing_result):
            with pytest.raises(GitError):
                gr.push(branch="mybranch")


class TestSyncAndMerge:
    def test_merge_branch_merge_failure_raises_giterror(self):
        gr = repository_module.GitRepository.__new__(GitRepository)

        failing_result = CommandResult(
            returncode=1,
            stdout="",
            stderr="CONFLICT (content): Merge conflict",
            command=["git", "merge", "feature"],
        )
        with patch.object(GitRepository, "_execute_subprocess", return_value=failing_result):
            with pytest.raises(GitError):
                gr.merge_branch("feature", fast_forward=True)
