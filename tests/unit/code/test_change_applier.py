"""Tests for ChangeApplier — backup/restore transaction and syntax verification."""
import pytest
from pathlib import Path

from branch_fixer.core.models import CodeChanges
from branch_fixer.services.code.change_applier import (
    BackupError,
    ChangeApplier,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def applier():
    """
    Provide a fresh ChangeApplier instance for tests.
    
    Returns:
        ChangeApplier: a new, ready-to-use ChangeApplier instance (pytest fixture).
    """
    return ChangeApplier()


@pytest.fixture
def valid_py(tmp_path) -> Path:
    """
    Create a file named `test_sample.py` containing a simple, syntactically valid Python test function and return its path.
    
    Parameters:
        tmp_path (Path): Directory in which to create the file (typically pytest's tmp_path fixture).
    
    Returns:
        Path: Path to the created `test_sample.py`.
    """
    f = tmp_path / "test_sample.py"
    f.write_text("def test_foo():\n    assert 1 == 1\n")
    return f


@pytest.fixture
def valid_changes(valid_py) -> CodeChanges:
    """
    Constructs a CodeChanges object representing a simple test file change that replaces an equality assertion with `assert True`.
    
    Parameters:
        valid_py (Path): Path to the valid Python test file provided by the `valid_py` fixture.
    
    Returns:
        CodeChanges: Instance whose `original_code` is a sample test function containing `assert 1 == 1` and whose `modified_code` replaces that assertion with `assert True`.
    """
    return CodeChanges(
        original_code="def test_foo():\n    assert 1 == 1\n",
        modified_code="def test_foo():\n    assert True\n",
    )


# ---------------------------------------------------------------------------
# apply_changes_with_backup — happy path
# ---------------------------------------------------------------------------

class TestApplyChangesHappyPath:
    def test_returns_true_and_backup_path_on_success(self, applier, valid_py, valid_changes):
        success, backup_path = applier.apply_changes_with_backup(valid_py, valid_changes)
        assert success is True
        assert backup_path is not None
        assert backup_path.exists()

    def test_modified_code_is_written_to_file(self, applier, valid_py, valid_changes):
        applier.apply_changes_with_backup(valid_py, valid_changes)
        assert "assert True" in valid_py.read_text()

    def test_backup_contains_original_content(self, applier, valid_py, valid_changes):
        original = valid_py.read_text()
        _, backup_path = applier.apply_changes_with_backup(valid_py, valid_changes)
        assert backup_path.read_text() == original

    def test_backup_is_in_backups_subdir(self, applier, valid_py, valid_changes):
        _, backup_path = applier.apply_changes_with_backup(valid_py, valid_changes)
        assert backup_path.parent.name == ".backups"

    def test_strips_markdown_code_fences(self, applier, valid_py):
        changes = CodeChanges(
            original_code="def test_foo():\n    assert 1 == 1\n",
            modified_code="```python\ndef test_foo():\n    assert True\n```",
        )
        success, _ = applier.apply_changes_with_backup(valid_py, changes)
        assert success is True
        assert "```" not in valid_py.read_text()

    def test_strips_backtick_fence_no_stray_n(self, applier, valid_py):
        """Regression: off-by-one on ```python strip left a stray 'n' at start of file."""
        changes = CodeChanges(
            original_code="def test_foo():\n    assert 1 == 1\n",
            modified_code="```python\ndef test_foo():\n    assert True\n```",
        )
        _, _ = applier.apply_changes_with_backup(valid_py, changes)
        content = valid_py.read_text()
        assert not content.startswith("n"), f"Stray 'n' at start: {content[:20]!r}"
        assert content.startswith("def"), f"Expected 'def', got: {content[:20]!r}"

    def test_strips_plain_backtick_fence(self, applier, valid_py):
        changes = CodeChanges(
            original_code="def test_foo():\n    assert 1 == 1\n",
            modified_code="```\ndef test_foo():\n    assert True\n```",
        )
        success, _ = applier.apply_changes_with_backup(valid_py, changes)
        assert success is True
        assert "```" not in valid_py.read_text()


# ---------------------------------------------------------------------------
# apply_changes_with_backup — syntax failure reverts automatically
# ---------------------------------------------------------------------------

class TestApplyChangesSyntaxFailure:
    def test_returns_false_on_syntax_error(self, applier, valid_py):
        original = valid_py.read_text()
        bad_changes = CodeChanges(
            original_code=original,
            modified_code="def test_foo(:\n    pass\n",  # syntax error
        )
        success, backup_path = applier.apply_changes_with_backup(valid_py, bad_changes)
        assert success is False

    def test_original_restored_after_syntax_failure(self, applier, valid_py):
        original = valid_py.read_text()
        bad_changes = CodeChanges(
            original_code=original,
            modified_code="def test_foo(:\n    pass\n",
        )
        applier.apply_changes_with_backup(valid_py, bad_changes)
        assert valid_py.read_text() == original

    def test_backup_still_returned_after_syntax_failure(self, applier, valid_py):
        bad_changes = CodeChanges(
            original_code=valid_py.read_text(),
            modified_code="def test_foo(:\n    pass\n",
        )
        _, backup_path = applier.apply_changes_with_backup(valid_py, bad_changes)
        assert backup_path is not None


# ---------------------------------------------------------------------------
# apply_changes_with_backup — missing file
# ---------------------------------------------------------------------------

class TestApplyChangesMissingFile:
    def test_returns_false_for_nonexistent_file(self, applier, tmp_path):
        ghost = tmp_path / "ghost.py"
        changes = CodeChanges(original_code="x", modified_code="y")
        success, backup_path = applier.apply_changes_with_backup(ghost, changes)
        assert success is False


# ---------------------------------------------------------------------------
# restore_backup
# ---------------------------------------------------------------------------

class TestRestoreBackup:
    def test_restores_file_from_backup(self, applier, valid_py, valid_changes):
        original = valid_py.read_text()
        _, backup_path = applier.apply_changes_with_backup(valid_py, valid_changes)
        # File now has modified content; restore it
        applier.restore_backup(valid_py, backup_path)
        assert valid_py.read_text() == original

    def test_raises_if_backup_missing(self, applier, valid_py, tmp_path):
        nonexistent = tmp_path / "no.bak"
        with pytest.raises(BackupError):
            applier.restore_backup(valid_py, nonexistent)


# ---------------------------------------------------------------------------
# _backup_file
# ---------------------------------------------------------------------------

class TestBackupFile:
    def test_raises_for_nonexistent_source(self, applier, tmp_path):
        with pytest.raises(FileNotFoundError):
            applier._backup_file(tmp_path / "missing.py")

    def test_backup_path_has_bak_extension(self, applier, valid_py):
        backup = applier._backup_file(valid_py)
        assert backup.suffix == ".bak"

    def test_backup_name_includes_original_stem(self, applier, valid_py):
        backup = applier._backup_file(valid_py)
        assert "test_sample" in backup.name


# ---------------------------------------------------------------------------
# _verify_changes
# ---------------------------------------------------------------------------

class TestVerifyChanges:
    def test_valid_python_returns_true(self, applier, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text("x = 1\n")
        assert applier._verify_changes(f) is True

    def test_invalid_python_returns_false(self, applier, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def foo(:\n    pass\n")
        assert applier._verify_changes(f) is False

    def test_empty_file_returns_true(self, applier, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        assert applier._verify_changes(f) is True
