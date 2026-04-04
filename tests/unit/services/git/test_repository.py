import os
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

import pytest

import branch_fixer.services.git.repository as repository_module
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.git.models import CommandResult, GitErrorDetails, ErrorDetails
from branch_fixer.services.git.exceptions import (
    NotAGitRepositoryError,
    GitError,
    BranchNameError,
    BranchCreationError,
    InvalidGitRepositoryError,
    NoSuchPathError,
)
from git import GitCommandError


# Module-level fixtures
@pytest.fixture
def tmp_repo_path(tmp_path):
    # Create a fake repository directory with .git
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    git_dir = repo_dir / ".git"
    git_dir.mkdir()
    return repo_dir


@pytest.fixture
def fake_repo_obj(tmp_repo_path):
    # Simple fake repo object used by patched Repo
    fake = SimpleNamespace()
    fake.working_dir = str(tmp_repo_path)
    # attributes used in other tests
    fake.index = SimpleNamespace(diff=lambda _: [])
    fake.is_dirty = lambda untracked_files=True: False
    fake.active_branch = SimpleNamespace(name="main")
    fake.heads = [SimpleNamespace(name="main"), SimpleNamespace(name="feature")]
    return fake


@pytest.fixture
def simple_command_result():
    def _make(returncode=0, stdout="", stderr="", command=None):
        return CommandResult(returncode=returncode, stdout=stdout, stderr=stderr, command=command or [])
    return _make


class TestGitRepositoryInit:
    def test_init_success_creates_components(self, tmp_repo_path, fake_repo_obj):
        # Patch _find_git_root to return tmp_repo_path, Repo to return fake_repo_obj,
        # and _get_main_branch to return 'main'. Also patch PRManager and BranchManager
        # to simple classes to avoid heavier constructors.
        class DummyPR:
            def __init__(self, repo):
                self.repository = repo

        class DummyBranchMgr:
            def __init__(self, repo):
                self.repository = repo

        with patch.object(repository_module.GitRepository, "_find_git_root", return_value=tmp_repo_path), \
             patch.object(repository_module, "Repo", side_effect=lambda *a, **k: fake_repo_obj), \
             patch.object(repository_module.GitRepository, "_get_main_branch", return_value="main"), \
             patch.object(repository_module, "PRManager", DummyPR), \
             patch.object(repository_module, "BranchManager", DummyBranchMgr):
            repo = GitRepository(root=tmp_repo_path)
            assert repo.root == tmp_repo_path
            assert repo.repo is fake_repo_obj
            assert repo.main_branch == "main"
            assert isinstance(repo.pr_manager, DummyPR)
            assert isinstance(repo.branch_manager, DummyBranchMgr)

    def test_init_not_a_git_repo_raises_NotAGitRepositoryError(self, tmp_repo_path):
        # Simulate _find_git_root raising InvalidGitRepositoryError
        with patch.object(repository_module.GitRepository, "_find_git_root", side_effect=InvalidGitRepositoryError("bad")), \
             patch.object(repository_module, "Repo", side_effect=Exception("should not be called")):
            with pytest.raises(NotAGitRepositoryError):
                GitRepository(root=tmp_repo_path)

    def test_init_gitcommanderror_rewrapped_as_GitError(self, tmp_repo_path, fake_repo_obj):
        # Patch Repo to raise GitCommandError
        git_exc = GitCommandError("git", 1, stderr="git failed")
        with patch.object(repository_module.GitRepository, "_find_git_root", return_value=tmp_repo_path), \
             patch.object(repository_module, "Repo", side_effect=git_exc):
            with pytest.raises(GitError) as excinfo:
                GitRepository(root=tmp_repo_path)
            assert "git failed" in str(excinfo.value)

    def test_init_unexpected_exception_wrapped_as_GitError(self, tmp_repo_path):
        # Patch Repo to raise ValueError; should be wrapped in GitError
        with patch.object(repository_module.GitRepository, "_find_git_root", return_value=tmp_repo_path), \
             patch.object(repository_module, "Repo", side_effect=ValueError("boom")):
            with pytest.raises(GitError) as excinfo:
                GitRepository(root=tmp_repo_path)
            assert "boom" in str(excinfo.value)


class TestFindGitRoot:
    def test_find_git_root_success_returns_working_dir(self, tmp_repo_path, fake_repo_obj):
        # Create a HEAD file to make it more realistic
        head_file = tmp_repo_path / ".git" / "HEAD"
        head_file.write_text("ref: refs/heads/main\n")

        def fake_repo(*args, **kwargs):
            return fake_repo_obj

        with patch.object(repository_module, "Repo", side_effect=fake_repo):
            gr = repository_module.GitRepository.__new__(GitRepository)
            result = gr._find_git_root(tmp_repo_path)
            assert Path(result) == Path(fake_repo_obj.working_dir)

    def test_find_git_root_no_dot_git_raises(self, tmp_path):
        dir_no_git = tmp_path / "no_git"
        dir_no_git.mkdir()
        gr = repository_module.GitRepository.__new__(GitRepository)
        with pytest.raises(NotAGitRepositoryError):
            gr._find_git_root(dir_no_git)

    def test_find_git_root_repo_raises_translates_to_NotAGitRepositoryError(self, tmp_repo_path):
        # Ensure .git exists
        (tmp_repo_path / ".git").mkdir(exist_ok=True)

        def raise_invalid(*a, **k):
            raise InvalidGitRepositoryError("invalid")

        with patch.object(repository_module, "Repo", side_effect=raise_invalid):
            gr = repository_module.GitRepository.__new__(GitRepository)
            with pytest.raises(NotAGitRepositoryError):
                gr._find_git_root(tmp_repo_path)

    def test_find_git_root_permission_error_re_raised(self, tmp_repo_path):
        # Simulate PermissionError when checking .git exists by patching Path.exists
        original_exists = Path.exists

        def raise_perm(self):
            if str(self).endswith(".git"):
                raise PermissionError("denied")
            return original_exists(self)

        with patch("pathlib.Path.exists", raise_perm):
            gr = repository_module.GitRepository.__new__(GitRepository)
            with pytest.raises(PermissionError) as excinfo:
                gr._find_git_root(tmp_repo_path)
            assert "Permission denied" in str(excinfo.value) or "denied" in str(excinfo.value)


class TestGetMainBranch:
    def test_get_main_branch_valid_head(self, tmp_repo_path):
        head_file = tmp_repo_path / ".git" / "HEAD"
        head_file.write_text("ref: refs/heads/main\n")
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path
        assert gr._get_main_branch() == "main"

    def test_get_main_branch_invalid_format_raises_GitError(self, tmp_repo_path):
        head_file = tmp_repo_path / ".git" / "HEAD"
        head_file.write_text("commit 12345\n")
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path
        with pytest.raises(GitError) as excinfo:
            gr._get_main_branch()
        assert "Invalid HEAD file format" in str(excinfo.value)

    def test_get_main_branch_io_error_raised_as_GitError(self, tmp_repo_path):
        # Create .git but patch read_text to raise OSError
        head_path = tmp_repo_path / ".git" / "HEAD"
        head_path.write_text("ref: refs/heads/main\n")
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path

        def raise_io(*args, **kwargs):
            raise OSError("io problem")

        with patch.object(Path, "read_text", raise_io):
            with pytest.raises(GitError) as excinfo:
                gr._get_main_branch()
            assert "Unable to read HEAD file" in str(excinfo.value)


class TestRunCommandAndHelpers:
    def test_prepare_git_command_strips_and_inserts(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        assert gr._prepare_git_command(["git", "status"]) == ["git", "status"]
        assert gr._prepare_git_command(["status", "--porcelain"]) == ["git", "status", "--porcelain"]
        assert gr._prepare_git_command([]) == ["git"]

    def test_execute_subprocess_success(self, tmp_repo_path, simple_command_result):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path

        fake_process = SimpleNamespace(returncode=0, stdout="OK", stderr="")
        with patch("subprocess.run", return_value=fake_process) as mock_run:
            result = gr._execute_subprocess(["git", "status"])
            assert result.returncode == 0
            assert result.stdout == "OK"
            assert result.stderr == ""
            assert result.command == ["git", "status"]

    def test_execute_subprocess_propagates_exceptions(self, tmp_repo_path):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                gr._execute_subprocess(["git", "status"])

    def test_check_command_error_no_raise_on_zero(self, simple_command_result):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr._check_command_error(simple_command_result(returncode=0, command=["git", "ok"]))

    def test_check_command_error_raises_on_nonzero(self, simple_command_result):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with pytest.raises(GitError) as excinfo:
            gr._check_command_error(simple_command_result(returncode=2, stderr="bad", command=["git", "fail"]))
        assert "return code 2" in str(excinfo.value) or "bad" in str(excinfo.value)

    def test_run_command_happy_path(self, tmp_repo_path, simple_command_result):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path

        with patch.object(GitRepository, "_prepare_git_command", return_value=["git", "status"]), \
             patch.object(GitRepository, "_execute_subprocess", return_value=simple_command_result(returncode=0, stdout="ok", stderr="", command=["git", "status"])):
            result = gr.run_command(["status"])
            assert isinstance(result, CommandResult)
            assert result.stdout == "ok"

    def test_run_command_nonzero_returncode_raises_GitError(self, tmp_repo_path, simple_command_result):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path

        with patch.object(GitRepository, "_prepare_git_command", return_value=["git", "status"]), \
             patch.object(GitRepository, "_execute_subprocess", return_value=simple_command_result(returncode=1, stdout="", stderr="err", command=["git", "status"])):
            with pytest.raises(GitError) as excinfo:
                gr.run_command(["status"])
            assert "err" in str(excinfo.value)

    def test_run_command_file_not_found_translated(self, tmp_repo_path):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path

        with patch.object(GitRepository, "_prepare_git_command", side_effect=FileNotFoundError()):
            with pytest.raises(GitError) as excinfo:
                gr.run_command(["status"])
            assert "Git command not found" in str(excinfo.value)

    def test_run_command_unknown_git_command_string_detected(self, tmp_repo_path):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path

        def raise_exc(*a, **k):
            raise Exception("'nonexistent' is not a git command")

        with patch.object(GitRepository, "_prepare_git_command", return_value=["git", "nonexistent"]), \
             patch.object(GitRepository, "_execute_subprocess", side_effect=raise_exc):
            with pytest.raises(GitError) as excinfo:
                gr.run_command(["nonexistent"])
            assert "unknown git command" in str(excinfo.value)

    def test_run_command_other_exception_wrapped(self, tmp_repo_path):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.root = tmp_repo_path

        def raise_val(*a, **k):
            raise ValueError("boom")

        with patch.object(GitRepository, "_prepare_git_command", return_value=["git", "boom"]), \
             patch.object(GitRepository, "_execute_subprocess", side_effect=raise_val):
            with pytest.raises(GitError) as excinfo:
                gr.run_command(["boom"])
            assert "boom" in str(excinfo.value)


class TestRepoStateHelpers:
    def test_is_clean_true_and_false(self):
        gr = repository_module.GitRepository.__new__(GitRepository)

        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="", stderr="", command=["git", "status"])):
            assert gr.is_clean() is True

        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout=" M file\n", stderr="", command=["git", "status"])):
            assert gr.is_clean() is False

    def test_is_clean_run_command_raises_wrapped(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with patch.object(GitRepository, "run_command", side_effect=ValueError("boom")):
            with pytest.raises(GitError) as excinfo:
                gr.is_clean()
            assert "Unable to determine repository state" in str(excinfo.value)

    def test_branch_exists_true_and_false(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="  feature\n", stderr="", command=["git", "branch", "--list"])):
            assert gr.branch_exists("feature") is True

        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="", stderr="", command=["git", "branch", "--list"])):
            assert gr.branch_exists("nope") is False

    def test_branch_exists_raises_wrapped(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with patch.object(GitRepository, "run_command", side_effect=RuntimeError("err")):
            with pytest.raises(GitError) as excinfo:
                gr.branch_exists("x")
            assert "Unable to check branch existence" in str(excinfo.value)

    def test_get_current_branch_happy_and_error(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="feature-1\n", stderr="", command=["git", "branch", "--show-current"])):
            assert gr.get_current_branch() == "feature-1"

        with patch.object(GitRepository, "run_command", side_effect=RuntimeError("err")):
            with pytest.raises(GitError):
                gr.get_current_branch()


class TestNotImplementedPlaceholders:
    def test_clone_not_implemented(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with pytest.raises(NotImplementedError):
            gr.clone("url", None)

    def test_commit_not_implemented(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with pytest.raises(NotImplementedError):
            gr.commit("msg")

    def test_pull_not_implemented(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with pytest.raises(NotImplementedError):
            gr.pull(None)

    def test_create_pull_request_not_implemented(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with pytest.raises(NotImplementedError):
            gr.create_pull_request("t", "d")


class TestPush:
    def test_push_with_branch_success_and_failure(self):
        gr = repository_module.GitRepository.__new__(GitRepository)

        # success
        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="", stderr="", command=["git", "push"])):
            assert gr.push("mybranch") is True

        # failure returncode
        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=1, stdout="", stderr="err", command=["git", "push"])):
            assert gr.push("mybranch") is False

    def test_push_without_branch_uses_get_current_branch(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.get_current_branch = lambda: "cur"
        called = {}

        def fake_run(cmd):
            called['cmd'] = cmd
            return CommandResult(returncode=0, stdout="", stderr="", command=cmd)

        with patch.object(GitRepository, "run_command", side_effect=fake_run):
            assert gr.push(None) is True
            assert called['cmd'] == ["push", "origin", "cur"]

    def test_push_exceptions_caught_and_return_false(self):
        gr = repository_module.GitRepository.__new__(GitRepository)

        with patch.object(GitRepository, "run_command", side_effect=RuntimeError("boom")):
            assert gr.push("b") is False

        gr.get_current_branch = lambda: (_ for _ in ()).throw(RuntimeError("no branch"))
        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="", stderr="", command=["git", "push"])):
            assert gr.push(None) is False


class TestVersionControlAndSync:
    def test_has_version_control_true_false(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.repo = SimpleNamespace()
        assert gr.has_version_control() is True
        delattr(gr, "repo")
        assert gr.has_version_control() is False

    def test_is_clean_sync_true_false_and_error(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.repo = SimpleNamespace(is_dirty=lambda untracked_files=True: False)
        assert gr.is_clean_sync() is True
        gr.repo.is_dirty = lambda untracked_files=True: True
        assert gr.is_clean_sync() is False
        gr.repo.is_dirty = lambda untracked_files=True: (_ for _ in ()).throw(RuntimeError("err"))
        with pytest.raises(GitError):
            gr.is_clean_sync()

    def test_get_current_branch_sync_happy_detached_and_error(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.repo = SimpleNamespace(active_branch=SimpleNamespace(name="feature"))
        assert gr.get_current_branch_sync() == "feature"

        def raise_type(*a, **k):
            raise TypeError("detached")

        # Simulate attribute access raising TypeError for detached head by using a class-level property
        class FakeRepoDetached:
            @property
            def active_branch(self):
                raise TypeError("detached")

        gr.repo = FakeRepoDetached()
        # Accessing repo.active_branch will raise TypeError -> method should return None
        with patch.object(gr, "repo", gr.repo, create=True):
            assert gr.get_current_branch_sync() is None

        # Simulate GitCommandError raising
        def raise_gitcmd(*a, **k):
            raise GitCommandError("git", 1, stderr="err")

        class FakeRepo2:
            @property
            def active_branch(self):
                raise GitCommandError("git", 1, stderr="err")

        gr.repo = FakeRepo2()
        with pytest.raises(GitError):
            gr.get_current_branch_sync()

    def test_branch_exists_sync_true_false_and_error(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.repo = SimpleNamespace(heads=[SimpleNamespace(name="a"), SimpleNamespace(name="b")])
        assert gr.branch_exists_sync("a") is True
        assert gr.branch_exists_sync("x") is False
        # Make heads access raise — use a class with a real property descriptor
        class BrokenRepo:
            @property
            def heads(self):
                raise RuntimeError("boom")
        gr.repo = BrokenRepo()
        with pytest.raises(GitError):
            gr.branch_exists_sync("a")


class TestFixBranchCreation:
    def test_validate_branch_name_various(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        valid = ["feature/foo", "bugfix-123", "hotfix_1"]
        invalid = ["bad name", "tilde~", "colon:", "star*", "open[", "back\\slash", "/start", "end/", "a..b", "@"]
        for v in valid:
            assert gr.validate_branch_name(v) is True
        for iv in invalid:
            assert gr.validate_branch_name(iv) is False

    @pytest.mark.parametrize("branch_name", ["fix/1", "fix-2"])
    def test_validate_fix_branch_request_valid(self, branch_name):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with patch.object(GitRepository, "validate_branch_name", return_value=True), \
             patch.object(GitRepository, "branch_exists", return_value=False):
            # Should not raise
            gr._validate_fix_branch_request(branch_name)

    def test_validate_fix_branch_request_invalid_name_raises(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with patch.object(GitRepository, "validate_branch_name", return_value=False):
            with pytest.raises(BranchNameError):
                gr._validate_fix_branch_request("bad name")

    def test_validate_fix_branch_request_branch_exists_raises(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with patch.object(GitRepository, "validate_branch_name", return_value=True), \
             patch.object(GitRepository, "branch_exists", return_value=True):
            with pytest.raises(BranchCreationError):
                gr._validate_fix_branch_request("exists")

    def test_create_fix_branch_success_and_with_from_branch(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        gr.main_branch = "main"
        # Happy path default base
        with patch.object(GitRepository, "_validate_fix_branch_request", return_value=None) as vld, \
             patch.object(GitRepository, "_create_fix_branch_from_base", return_value=None) as create:
            assert gr.create_fix_branch("fix1") is True
            vld.assert_called_once_with("fix1")
            create.assert_called_once_with("fix1", "main")

        # With explicit from_branch
        with patch.object(GitRepository, "_validate_fix_branch_request", return_value=None), \
             patch.object(GitRepository, "_create_fix_branch_from_base", return_value=None) as create2:
            assert gr.create_fix_branch("fix2", from_branch="develop") is True
            create2.assert_called_once_with("fix2", "develop")

    def test_create_fix_branch_propagates_known_errors(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        # BranchNameError
        with patch.object(GitRepository, "_validate_fix_branch_request", side_effect=BranchNameError("bad")):
            with pytest.raises(BranchNameError):
                gr.create_fix_branch("bad")

        # BranchCreationError from create
        gr.main_branch = "main"
        with patch.object(GitRepository, "_validate_fix_branch_request", return_value=None), \
             patch.object(GitRepository, "_create_fix_branch_from_base", side_effect=BranchCreationError("fail")):
            with pytest.raises(BranchCreationError):
                gr.create_fix_branch("fail")

    def test_create_fix_branch_unexpected_exception_wrapped(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        with patch.object(GitRepository, "_validate_fix_branch_request", side_effect=ValueError("boom")):
            with pytest.raises(GitError) as excinfo:
                gr.create_fix_branch("x")
            assert "Unexpected error creating branch x" in str(excinfo.value)

    def test_create_fix_branch_from_base_success_and_failure(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        # success
        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="", stderr="", command=["git", "checkout"])):
            gr._create_fix_branch_from_base("b", "main")

        # failure
        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=1, stdout="", stderr="err", command=["git", "checkout"])):
            with pytest.raises(BranchCreationError) as excinfo:
                gr._create_fix_branch_from_base("b", "main")
            assert "err" in str(excinfo.value)


class TestCleanupAndPRCreation:
    def test_cleanup_fix_branch_delegates_and_wrapping(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        fake_mgr = SimpleNamespace()
        fake_mgr.cleanup_fix_branch = lambda name, force=False: True
        gr.branch_manager = fake_mgr
        assert gr.cleanup_fix_branch("b", force=False) is True

        fake_mgr.cleanup_fix_branch = lambda name, force=False: False
        assert gr.cleanup_fix_branch("b", force=True) is False

        def raise_err(name, force=False):
            raise ValueError("boom")
        fake_mgr.cleanup_fix_branch = raise_err
        with pytest.raises(GitError) as excinfo:
            gr.cleanup_fix_branch("b")
        assert "Failed to cleanup branch b" in str(excinfo.value)

    def test_create_pull_request_sync_success_and_failure(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        # Create a simple GitErrorDetails-like object
        err_details = SimpleNamespace(error_type="TypeError")
        error = SimpleNamespace(test_function="test_fn", test_file=Path("tests/test_file.py"), error_details=err_details)

        fake_pr_manager = SimpleNamespace()
        fake_pr_manager.create_pr = lambda title, desc, branch, files: True
        gr.pr_manager = fake_pr_manager

        assert gr.create_pull_request_sync("fix-1", error) is True

        fake_pr_manager.create_pr = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        with pytest.raises(GitError) as excinfo:
            gr.create_pull_request_sync("fix-1", error)
        assert "Failed to create pull request" in str(excinfo.value)


class TestSyncAndMerge:
    def test_sync_with_remote_success_and_giterror(self):
        gr = repository_module.GitRepository.__new__(GitRepository)
        # Both pull and push succeed (no exceptions)
        gr.pull = lambda *a, **k: None
        gr.push = lambda *a, **k: None
        assert gr.sync_with_remote() is True

        # pull raises GitError -> should return False
        gr.pull = lambda *a, **k: (_ for _ in ()).throw(GitError("pull fail"))
        gr.push = lambda *a, **k: None
        assert gr.sync_with_remote() is False

        # Non-GitError (NotImplementedError) should propagate
        gr.pull = lambda *a, **k: (_ for _ in ()).throw(NotImplementedError("not"))
        with pytest.raises(NotImplementedError):
            gr.sync_with_remote()

    def test_merge_branch_forms_command_and_returns(self):
        gr = repository_module.GitRepository.__new__(GitRepository)

        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="", stderr="", command=["git", "merge", "b"])) as run:
            assert gr.merge_branch("b", fast_forward=True) is True
            run.assert_called_once_with(["merge", "b"])

        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=0, stdout="", stderr="", command=["git", "merge", "b", "--no-ff"])) as run2:
            assert gr.merge_branch("b", fast_forward=False) is True
            run2.assert_called_once_with(["merge", "b", "--no-ff"])

        with patch.object(GitRepository, "run_command", return_value=CommandResult(returncode=1, stdout="", stderr="err", command=["git", "merge", "b"])) as run3:
            assert gr.merge_branch("b", fast_forward=True) is False

        # run_command raising should propagate
        with patch.object(GitRepository, "run_command", side_effect=GitError("boom")):
            with pytest.raises(GitError):
                gr.merge_branch("b", True)