"""RED test for F7/F8: BranchManager.get_branch_metadata and is_branch_merged
unconditionally raise NotImplementedError (src/branch_fixer/services/git/branch_manager.py:169,225).

Exercises the real BranchManager wired to a real GitRepository over an actual git
repo built in tmp_path (per plan §12: caller-supplied values are set explicitly),
so the assertions describe observable behavior, not a mocked git call sequence.
"""
import pytest
from git import Repo

from branch_fixer.services.git.branch_manager import BranchManager
from branch_fixer.services.git.models import BranchMetadata
from branch_fixer.services.git.repository import GitRepository


@pytest.fixture
def git_repo(tmp_path):
    repo = Repo.init(tmp_path)
    (tmp_path / "README.md").write_text("hello\n")
    repo.index.add(["README.md"])
    commit = repo.index.commit("Initial commit")
    return tmp_path, repo, commit.hexsha


def test_get_branch_metadata_returns_populated_metadata_for_known_branch(git_repo):
    tmp_path, repo, commit_sha = git_repo
    branch_name = repo.active_branch.name

    git_repository = GitRepository(root=tmp_path)
    manager: BranchManager = git_repository.branch_manager

    metadata = manager.get_branch_metadata(branch_name)

    assert isinstance(metadata, BranchMetadata)
    assert metadata.name == branch_name
    assert metadata.current is True
    assert metadata.last_commit == commit_sha
    assert metadata.modified_files == []


def test_is_branch_merged_true_for_merged_branch(git_repo):
    tmp_path, repo, _ = git_repo
    main_branch = repo.active_branch.name

    feature = repo.create_head("feature/merged")
    feature.checkout()
    (tmp_path / "feature.txt").write_text("feature work\n")
    repo.index.add(["feature.txt"])
    repo.index.commit("feature commit")

    repo.heads[main_branch].checkout()
    repo.git.merge("feature/merged", "--no-ff", "-m", "merge feature")

    git_repository = GitRepository(root=tmp_path)
    manager: BranchManager = git_repository.branch_manager

    assert manager.is_branch_merged("feature/merged", target_branch=main_branch) is True


def test_is_branch_merged_false_for_unmerged_branch(git_repo):
    tmp_path, repo, _ = git_repo
    main_branch = repo.active_branch.name

    feature = repo.create_head("feature/unmerged")
    feature.checkout()
    (tmp_path / "unmerged.txt").write_text("unmerged work\n")
    repo.index.add(["unmerged.txt"])
    repo.index.commit("unmerged commit")

    repo.heads[main_branch].checkout()

    git_repository = GitRepository(root=tmp_path)
    manager: BranchManager = git_repository.branch_manager

    assert manager.is_branch_merged("feature/unmerged", target_branch=main_branch) is False
