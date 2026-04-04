import re
from types import SimpleNamespace
from typing import Any, Callable, List, Optional, Set
from unittest.mock import patch

import pytest

from branch_fixer.services.git.branch_manager import BranchManager
from branch_fixer.services.git.exceptions import (
    BranchCreationError,
    BranchNameError,
    GitError,
)


class FakeCommandResult:
    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        command: Optional[List[str]] = None,
    ):
        """
        Initialize a FakeCommandResult with the command's exit status and output.
        
        Parameters:
            returncode (int): Process exit code; non-zero indicates failure.
            stdout (str): Captured standard output from the command.
            stderr (str): Captured standard error from the command.
            command (Optional[List[str]]): The executed command as a list of arguments; defaults to an empty list.
        """
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command or []

    @property
    def failed(self) -> bool:
        """
        Indicates whether the command execution failed.
        
        Returns:
            bool: `True` if the command's return code is not zero, `False` otherwise.
        """
        return self.returncode != 0

    @property
    def success(self) -> bool:
        """
        Indicates whether the command completed successfully.
        
        Returns:
            True if the command's return code equals 0, False otherwise.
        """
        return self.returncode == 0

    def __str__(self) -> str:
        """
        Provide a human-readable representation of the command result.
        
        Returns:
            A string describing the command (joined args) and its return code.
        """
        return f"CommandResult(command='{' '.join(self.command)}', returncode={self.returncode})"


class FakeRepo:
    """
    Lightweight fake repository used to exercise BranchManager behavior.
    It records run_command calls and can be configured to simulate different
    repository states and command results/side-effects.
    """

    def __init__(
        self,
        main_branch: str = "main",
        current_branch: str = "main",
        is_clean: bool = True,
        existing_branches: Optional[Set[str]] = None,
        diff_items: Optional[List[SimpleNamespace]] = None,
        run_command_result: Optional[FakeCommandResult] = None,
        run_command_side_effect: Optional[Exception] = None,
        get_current_branch_side_effect: Optional[Exception] = None,
    ):
        """
        Initialize a FakeRepo used by tests to simulate repository state and command behavior.
        
        Parameters:
            main_branch (str): Name of the repository's main branch.
            current_branch (str): The branch reported by get_current_branch().
            is_clean (bool): Whether the repository is considered clean (no unstaged changes).
            existing_branches (Optional[Set[str]]): Set of branch names that exist in the fake repo.
            diff_items (Optional[List[SimpleNamespace]]): Sequence of objects with an `a_path` attribute returned by repo.index.diff(None).
            run_command_result (Optional[FakeCommandResult]): Default result returned by run_command when no side effect is set.
            run_command_side_effect (Optional[Exception]): Exception to raise when run_command is called (if set).
            get_current_branch_side_effect (Optional[Exception]): Exception to raise when get_current_branch is called (if set).
        
        After initialization:
            - self.existing_branches contains the provided branches as a set.
            - self.diff_items is the list returned by repo.index.diff(None).
            - self._run_command_result and self._run_command_side_effect control run_command behavior.
            - self._get_current_branch_side_effect controls get_current_branch behavior.
            - self.calls is an empty list that will record each run_command call (list of arg lists).
            - self.repo provides a minimal object with repo.index.diff(None) returning a copy of diff_items.
        """
        self.main_branch = main_branch
        self._current_branch = current_branch
        self._is_clean = is_clean
        self.existing_branches = set(existing_branches or set())
        self.diff_items = list(diff_items or [])
        self._run_command_result = run_command_result or FakeCommandResult(
            returncode=0, command=[]
        )
        self._run_command_side_effect = run_command_side_effect
        self._get_current_branch_side_effect = get_current_branch_side_effect

        # Record of invoked run_command arguments
        self.calls: List[List[str]] = []

        # Provide repo.index.diff(None) interface
        class Index:
            def __init__(self, items):
                """
                Initialize the instance with the provided collection of items.
                
                Parameters:
                    items: An iterable or sequence of objects to be stored as the instance's items; assigned directly to self._items.
                """
                self._items = items

            def diff(self, arg):
                # arg is expected to be None in BranchManager.get_status
                """
                Return the configured diff items; the input argument is ignored.
                
                Parameters:
                	arg: Expected to be None when called by BranchManager.get_status; any value is ignored.
                
                Returns:
                	list: A new list containing the configured diff items (items with an `a_path` attribute) representing repository changes for tests.
                """
                return list(self._items)

        class RepoObj:
            def __init__(self, index):
                """
                Initialize the wrapper with a repo index used to produce diffs.
                
                Parameters:
                    index: An index-like object whose `diff(None)` returns a list of diff items (each exposing an `a_path` attribute) used by tests to represent repository changes.
                """
                self.index = index

        self.repo = RepoObj(Index(self.diff_items))

    def get_current_branch(self) -> str:
        """
        Get the repository's current branch name or raise a configured side effect.
        
        Returns:
            str: The name of the current branch.
        
        Raises:
            Exception: The configured side-effect exception if one was set on the fake repo; the exception is raised as-is.
        """
        if self._get_current_branch_side_effect:
            raise self._get_current_branch_side_effect
        return self._current_branch

    def is_clean(self) -> bool:
        """
        Indicates whether the fake repository has no uncommitted changes.
        
        Returns:
            bool: `True` if the repository is clean (no uncommitted changes), `False` otherwise.
        """
        return self._is_clean

    def branch_exists(self, branch_name: str) -> bool:
        """
        Check whether a branch with the given name exists in the fake repository.
        
        Returns:
            True if the repository contains a branch with the given name, False otherwise.
        """
        return branch_name in self.existing_branches

    def run_command(self, args: List[str]) -> FakeCommandResult:
        # record the call
        """
        Record and simulate running a git command for tests.
        
        Parameters:
            args (List[str]): The command and its arguments to execute (e.g., ["checkout", "-b", "fix/1", "main"]).
        
        Returns:
            FakeCommandResult: A result object containing `returncode`, `stdout`, `stderr`, and the echoed `command` list.
        
        Notes:
            - The call is recorded in `self.calls`.
            - If a side effect exception has been configured via `set_run_command_side_effect`, that exception is raised instead of returning a result.
        """
        self.calls.append(list(args))
        if self._run_command_side_effect:
            raise self._run_command_side_effect
        # return a copy (so tests can mutate if needed separately)
        return FakeCommandResult(
            returncode=self._run_command_result.returncode,
            stdout=self._run_command_result.stdout,
            stderr=self._run_command_result.stderr,
            command=list(args),
        )

    # Helpers to mutate state in tests
    def set_current_branch(self, name: str):
        """
        Set the repository's current branch name.
        
        Parameters:
            name (str): Branch name to use as the repository's current branch.
        """
        self._current_branch = name

    def set_is_clean(self, clean: bool):
        """
        Set whether the fake repository is considered clean (no working-tree changes).
        
        Parameters:
            clean (bool): `True` to mark the repository as having no unstaged or uncommitted changes, `False` otherwise.
        """
        self._is_clean = clean

    def set_diff_items(self, items: List[SimpleNamespace]):
        """
        Set the repository's diff items and update the fake repo index to return them.
        
        Parameters:
            items (List[SimpleNamespace]): Ordered list of diff-like objects (expected to have an `a_path` attribute) that will be returned by `self.repo.index.diff(None)`.
        
        Description:
            Replaces the instance's `diff_items` with `items` and assigns `self.repo` a minimal object whose `index.diff(arg)` returns a list copy of `diff_items`.
        """
        self.diff_items = items
        # update repo.index to reference new items
        class Index:
            def __init__(self, items):
                """
                Initialize the instance with the provided collection of items.
                
                Parameters:
                    items: An iterable or sequence of objects to be stored as the instance's items; assigned directly to self._items.
                """
                self._items = items

            def diff(self, arg):
                """
                Return the configured index diff items.
                
                Parameters:
                    arg: Ignored; present for API compatibility.
                
                Returns:
                    list: A shallow copy of the stored diff item objects.
                """
                return list(self._items)

        class RepoObj:
            def __init__(self, index):
                """
                Initialize the wrapper with a repo index used to produce diffs.
                
                Parameters:
                    index: An index-like object whose `diff(None)` returns a list of diff items (each exposing an `a_path` attribute) used by tests to represent repository changes.
                """
                self.index = index

        self.repo = RepoObj(Index(self.diff_items))

    def set_run_command_result(self, result: FakeCommandResult):
        """
        Configure the fake repository to return a specific command result for subsequent run_command calls.
        
        Parameters:
            result (FakeCommandResult): The command result that future calls to `run_command` will return.
        """
        self._run_command_result = result

    def set_run_command_side_effect(self, exc: Exception):
        """
        Set an exception to be raised when `run_command` is invoked on this fake repository.
        
        Parameters:
            exc (Exception): Exception instance that will be raised by subsequent `run_command` calls.
        """
        self._run_command_side_effect = exc

    def set_get_current_branch_side_effect(self, exc: Exception):
        """
        Configure a side effect so subsequent calls to `get_current_branch()` raise the provided exception.
        
        Parameters:
            exc (Exception): The exception instance that `get_current_branch()` should raise when called.
        """
        self._get_current_branch_side_effect = exc


@pytest.fixture
def make_repo() -> Callable[..., FakeRepo]:
    """
    Create a factory for producing configured FakeRepo instances for tests.
    
    Returns:
        factory (Callable[..., FakeRepo]): A callable that accepts the same keyword arguments as FakeRepo.__init__ and returns a new FakeRepo configured with those values.
    """
    def _make_repo(**kwargs: Any) -> FakeRepo:
        return FakeRepo(**kwargs)

    return _make_repo


@pytest.fixture
def manager_factory(make_repo: Callable[..., FakeRepo]) -> Callable[..., BranchManager]:
    """
    Create a factory that builds BranchManager instances backed by test FakeRepo objects.
    
    Parameters:
        make_repo (Callable[..., FakeRepo]): A factory that produces FakeRepo instances from keyword arguments.
    
    Returns:
        factory (Callable[..., BranchManager]): A callable that accepts FakeRepo constructor keyword arguments and returns a new BranchManager using the produced FakeRepo.
    """
    def _factory(**repo_kwargs: Any) -> BranchManager:
        repo = make_repo(**repo_kwargs)
        return BranchManager(repo)

    return _factory


class TestBranchManager:
    # Happy path tests

    def test_init_stores_repository_and_defaults(self, make_repo):
        repo = make_repo()
        mgr = BranchManager(repo)
        assert mgr.repository is repo
        assert mgr.name_pattern == r"^[a-zA-Z0-9\-_\/]+$"
        assert mgr.forbidden_names == {"master", "main", "develop"}

        # The implementation does not raise for None repository (despite docstring)
        mgr_none = BranchManager(None)
        assert mgr_none.repository is None

    def test_get_status_clean_repo_no_changes(self, make_repo):
        repo = make_repo(current_branch="feature/one", is_clean=True, diff_items=[])
        mgr = BranchManager(repo)
        status = mgr.get_status()
        assert status.current_branch == "feature/one"
        # is_clean True -> has_changes should be not True -> False
        assert status.has_changes is False
        assert status.changes == []

    def test_get_status_dirty_repo_with_changes(self, make_repo):
        diff_items = [SimpleNamespace(a_path="file1.txt"), SimpleNamespace(a_path="src/mod.py")]
        repo = make_repo(current_branch="feature/two", is_clean=False, diff_items=diff_items)
        mgr = BranchManager(repo)
        status = mgr.get_status()
        assert status.current_branch == "feature/two"
        assert status.has_changes is True
        assert status.changes == ["file1.txt", "src/mod.py"]

    def test_create_fix_branch_success_default_base(self, make_repo):
        repo = make_repo(main_branch="main", existing_branches=set(), run_command_result=FakeCommandResult(returncode=0))
        mgr = BranchManager(repo)
        result = mgr.create_fix_branch("fix/1")
        assert result is True
        assert repo.calls == [["checkout", "-b", "fix/1", "main"]]

    def test_create_fix_branch_success_with_from_branch(self, make_repo):
        repo = make_repo(main_branch="main", existing_branches=set(), run_command_result=FakeCommandResult(returncode=0))
        mgr = BranchManager(repo)
        result = mgr.create_fix_branch("fix/2", from_branch="develop")
        assert result is True
        assert repo.calls == [["checkout", "-b", "fix/2", "develop"]]

    def test_cleanup_fix_branch_returns_true_if_branch_does_not_exist(self, make_repo):
        repo = make_repo(existing_branches=set())
        mgr = BranchManager(repo)
        result = mgr.cleanup_fix_branch("nonexistent")
        assert result is True
        # run_command should not be called
        assert repo.calls == []

    def test_cleanup_fix_branch_delete_success_nonforce(self, make_repo):
        repo = make_repo(existing_branches={"fix/5"}, current_branch="other", run_command_result=FakeCommandResult(returncode=0))
        mgr = BranchManager(repo)
        result = mgr.cleanup_fix_branch("fix/5", force=False)
        assert result is True
        assert repo.calls == [["branch", "-d", "fix/5"]]

    def test_cleanup_fix_branch_delete_success_force(self, make_repo):
        repo = make_repo(existing_branches={"fix/5"}, current_branch="other", run_command_result=FakeCommandResult(returncode=0))
        mgr = BranchManager(repo)
        result = mgr.cleanup_fix_branch("fix/5", force=True)
        assert result is True
        assert repo.calls == [["branch", "-D", "fix/5"]]

    def test_cleanup_fix_branch_switches_branch_before_delete_when_current(self, make_repo):
        repo = make_repo(existing_branches={"fix/6"}, current_branch="fix/6", main_branch="main", run_command_result=FakeCommandResult(returncode=0))
        mgr = BranchManager(repo)
        result = mgr.cleanup_fix_branch("fix/6", force=False)
        assert result is True
        # Should first checkout main, then delete branch
        assert repo.calls == [["checkout", "main"], ["branch", "-d", "fix/6"]]

    # Edge cases

    @pytest.mark.parametrize(
        "valid_name",
        [
            "feature/123-foo_bar",
            "abc",
            "A_B-1/2",
            "name-with-dash",
        ],
    )
    def test_validate_branch_name_accepts_valid_names(self, manager_factory, valid_name):
        mgr = manager_factory()
        assert mgr.validate_branch_name(valid_name) is True

    def test_validate_branch_name_rejects_empty_string(self, manager_factory):
        mgr = manager_factory()
        with pytest.raises(BranchNameError) as excinfo:
            mgr.validate_branch_name("")
        assert "cannot be empty" in str(excinfo.value).lower()

    @pytest.mark.parametrize("bad_name", ["bad name", "name!", "weird*name"])
    def test_validate_branch_name_rejects_invalid_characters(self, manager_factory, bad_name):
        mgr = manager_factory()
        with pytest.raises(BranchNameError) as excinfo:
            mgr.validate_branch_name(bad_name)
        assert "contains invalid characters" in str(excinfo.value).lower()

    @pytest.mark.parametrize("forbidden", ["MASTER", "main", "Develop"])
    def test_validate_branch_name_rejects_forbidden_names_case_insensitive(self, manager_factory, forbidden):
        mgr = manager_factory()
        with pytest.raises(BranchNameError) as excinfo:
            mgr.validate_branch_name(forbidden)
        assert "cannot use reserved name" in str(excinfo.value).lower() or "reserved name" in str(excinfo.value).lower()

    # Error handling and exception-wrapping tests

    def test_get_status_propagates_exceptions(self, make_repo):
        repo = make_repo(get_current_branch_side_effect=RuntimeError("no git here"))
        mgr = BranchManager(repo)
        with pytest.raises(RuntimeError):
            mgr.get_status()

    def test_create_fix_branch_invalid_name_raises_BranchNameError(self, make_repo):
        repo = make_repo()
        mgr = BranchManager(repo)
        # Force the internal validation check to raise BranchNameError
        with patch.object(mgr, "_check_valid_new_branch_name", side_effect=BranchNameError("bad name")):
            with pytest.raises(BranchNameError):
                mgr.create_fix_branch("bad name")

    def test_create_fix_branch_existing_branch_raises_BranchCreationError(self, make_repo):
        repo = make_repo(existing_branches={"fix/3"})
        mgr = BranchManager(repo)
        with pytest.raises(BranchCreationError) as excinfo:
            mgr.create_fix_branch("fix/3")
        assert "already exists" in str(excinfo.value).lower()

    def test_create_fix_branch_run_command_failure_raises_BranchCreationError(self, make_repo):
        repo = make_repo(existing_branches=set(), run_command_result=FakeCommandResult(returncode=1, stderr="git error"))
        mgr = BranchManager(repo)
        with pytest.raises(BranchCreationError) as excinfo:
            mgr.create_fix_branch("fix/4")
        assert "git error" in str(excinfo.value)

    def test_create_fix_branch_unexpected_exception_wrapped_in_GitError(self, make_repo):
        repo = make_repo(existing_branches=set())
        mgr = BranchManager(repo)
        # remove main_branch attribute to cause AttributeError when accessed
        delattr(repo, "main_branch")
        with pytest.raises(GitError) as excinfo:
            mgr.create_fix_branch("fix/7")
        assert "Failed to create branch fix/7" in str(excinfo.value)

    def test_cleanup_fix_branch_delete_failure_returns_false(self, make_repo):
        repo = make_repo(existing_branches={"fix/8"}, current_branch="other", run_command_result=FakeCommandResult(returncode=2, stderr="delete failed"))
        mgr = BranchManager(repo)
        result = mgr.cleanup_fix_branch("fix/8", force=False)
        assert result is False
        assert repo.calls == [["branch", "-d", "fix/8"]]

    def test_cleanup_fix_branch_repo_raises_not_found_message_suppressed(self, make_repo):
        # Simulate run_command raising an exception with "not found" message
        repo = make_repo(existing_branches={"fix/9"})
        repo.set_run_command_side_effect(Exception("Branch not found in repository"))
        mgr = BranchManager(repo)
        # The code should catch this and return True (suppress)
        result = mgr.cleanup_fix_branch("fix/9", force=False)
        assert result is True

    def test_cleanup_fix_branch_unexpected_exception_wrapped_in_GitError(self, make_repo):
        repo = make_repo(existing_branches={"fix/10"})
        repo.set_run_command_side_effect(ValueError("boom"))
        mgr = BranchManager(repo)
        with pytest.raises(GitError) as excinfo:
            mgr.cleanup_fix_branch("fix/10")
        assert "Failed to clean up branch fix/10" in str(excinfo.value)

    def test_get_branch_metadata_raises_not_implemented(self, manager_factory):
        mgr = manager_factory()
        with pytest.raises(NotImplementedError):
            mgr.get_branch_metadata("any")

    def test_is_branch_merged_raises_not_implemented(self, manager_factory):
        mgr = manager_factory()
        with pytest.raises(NotImplementedError):
            mgr.is_branch_merged("any", target_branch="main")

    def test_validate_branch_name_wraps_unexpected_exceptions_as_BranchNameError(self, manager_factory):
        mgr = manager_factory()
        # Force an unexpected exception in the internal pattern checker
        with patch.object(mgr, "_check_branch_name_pattern", side_effect=ValueError("boom")):
            with pytest.raises(BranchNameError) as excinfo:
                mgr.validate_branch_name("some-name")
            assert "Failed to validate branch name" in str(excinfo.value)
            # __cause__ should be the original ValueError due to "from e" used in code
            assert isinstance(excinfo.value.__cause__, ValueError)