"""RED test for F66: GitRepository._find_git_root raises NotAGitRepositoryError
for a subdirectory of a real git repository instead of resolving to the repo root.

Location: src/branch_fixer/services/git/repository.py:87-91
"""
from pathlib import Path

from git import Repo

from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.git.exceptions import NotAGitRepositoryError


class TestFindGitRootSubdir:
    def test_find_git_root_from_subdir_resolves_to_repo_root(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        Repo.init(repo_dir)

        subdir = repo_dir / "src"
        subdir.mkdir()

        gr = GitRepository.__new__(GitRepository)

        raised = None
        result = None
        try:
            result = gr._find_git_root(subdir)
        except NotAGitRepositoryError as e:
            raised = e

        assert raised is None, (
            f"_find_git_root raised NotAGitRepositoryError for a real repo "
            f"subdirectory ({subdir}): {raised}"
        )
        assert Path(result) == repo_dir.resolve()
