# Bug catalog — F66 (`_find_git_root` premature `.git` check)

Location: `src/branch_fixer/services/git/repository.py:87-91` (`GitRepository._find_git_root`)

- **BUG-1 (the finding's defect):** `_find_git_root` raises `NotAGitRepositoryError` for any
  subdirectory of a real git repository (e.g. `<repo>/src`), because it checks
  `(root / ".git").exists()` at line 100 (using the caller-supplied `root` verbatim, without
  walking upward) *before* ever calling `Repo(root, search_parent_directories=True)` at line 104.
  Wrong: raises `NotAGitRepositoryError(f"Not a git repository: {root}")` for `<repo>/src`.
  Correct: returns the repo root `Path` (e.g. `<repo>`) without raising, exactly as
  `search_parent_directories=True` promises to GitPython callers.

- **BUG-2 (why the naive fix is unsafe — exception-class collision):** if the premature `.git`
  check is simply deleted without widening the surrounding `except` tuple, a genuinely non-repo
  path (no `.git` anywhere in its ancestry) would let GitPython's own
  `git.InvalidGitRepositoryError` / `git.NoSuchPathError` escape `_find_git_root` unmodified
  instead of being translated to the project's `NotAGitRepositoryError`
  (`src/branch_fixer/services/git/exceptions.py:11`), because the current `except
  (InvalidGitRepositoryError, NoSuchPathError)` clause at line 107 only catches the *project's own*
  same-named classes, not GitPython's. Wrong: a raw `git.InvalidGitRepositoryError`/
  `git.NoSuchPathError` propagates to callers of `_find_git_root`/`GitRepository.__init__`.
  Correct: callers only ever see `NotAGitRepositoryError` for any non-repo path, mocked or real.

- **BUG-3 (over-broad parent search, environment-dependent):** once the premature check is
  removed, `search_parent_directories=True` will walk *all* ancestors of a non-repo tmp path. If
  the test environment's tmp root itself sits inside a git checkout (unlike this session's
  confirmed isolated `/tmp`), a genuinely-intended-to-be-non-repo test directory could silently
  resolve to that unrelated ancestor's root instead of raising. Wrong: silent success (returns an
  unrelated ancestor `Path`) where a raise was expected. Correct: raises
  `NotAGitRepositoryError` for a path with no `.git` in its real, isolated ancestry.

- **BUG-4 (existing permission-error test goes vacuous):** `test_find_git_root_permission_error_re_raised`
  (`tests/unit/services/git/test_repository.py:136-149`) patches `pathlib.Path.exists` to raise
  `PermissionError` when the path ends in `.git`. Once the `(root / ".git").exists()` call is
  removed from `_find_git_root`, that patched call site no longer exists in the method, so the
  test's mock target stops firing. Wrong: the test either passes vacuously (no `PermissionError`
  ever actually raised inside `_find_git_root`) or fails outright once the mock target is
  corrected without updating the test. Correct: the test's mock must move to the call GitPython
  itself makes for the same underlying filesystem check (e.g. `os.path.exists`), still exercising
  a real `PermissionError` re-raise from `_find_git_root`.

- **BUG-5 (signature/return-type drift):** `_find_git_root(self, root: Optional[Path]) -> Path`
  must keep returning a `Path` and keep accepting exactly one `root` parameter; a fix that changes
  the return type (e.g. `str`) or adds/removes parameters would silently break every caller
  (`GitRepository.__init__` at line 65). Wrong: return type or signature changes. Correct: `def
  _find_git_root(self, root: Optional[Path]) -> Path` unchanged, still returning `Path`.

- **BUG-6 (regression in sibling tests):** the other 3 `TestFindGitRoot` tests
  (`test_find_git_root_success_returns_working_dir`,
  `test_find_git_root_no_dot_git_raises`,
  `test_find_git_root_repo_raises_translates_to_NotAGitRepositoryError`) and the remaining tests in
  `tests/unit/services/git/test_repository.py` must keep passing — an except-tuple or import-block
  edit that breaks unrelated tests in the same file is a regression, not a fix. Wrong: collected
  test count in that file drops below its pre-fix baseline. Correct: same or higher collected
  count, all green.
