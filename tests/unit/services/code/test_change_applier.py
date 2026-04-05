from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from branch_fixer.services.code.change_applier import (
    ChangeApplier,
    ChangeApplicationError,
    BackupError,
)


@pytest.fixture
def change_applier():
    return ChangeApplier()


@pytest.fixture
def file_factory(tmp_path):
    def _create(name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p
    return _create


class TestChangeApplicationError:
    def test_is_exception(self):
        assert issubclass(ChangeApplicationError, Exception)


class TestBackupError:
    def test_is_subclass_of_change_application_error(self):
        assert issubclass(BackupError, ChangeApplicationError)


class TestChangeApplier:
    # _backup_file happy path
    def test__backup_file_creates_backup_and_returns_path(self, change_applier, file_factory, tmp_path):
        src = file_factory("module.py", "x = 1\n")
        backup_path = change_applier._backup_file(src)
        assert backup_path.exists()
        assert backup_path.parent.name == ChangeApplier.BACKUP_DIRNAME
        assert backup_path != src
        assert backup_path.read_text(encoding="utf-8") == "x = 1\n"

    # _backup_file error: missing source
    def test__backup_file_raises_FileNotFoundError_for_missing_file(self, change_applier, tmp_path):
        missing = tmp_path / "nope.py"
        with pytest.raises(FileNotFoundError):
            change_applier._backup_file(missing)

    # _backup_file error: shutil.copy2 raises -> BackupError
    def test__backup_file_wraps_copy_errors_in_BackupError(self, change_applier, file_factory):
        src = file_factory("module2.py", "y = 2\n")
        with patch("branch_fixer.services.code.change_applier.shutil.copy2", side_effect=OSError("copy fail")):
            with pytest.raises(BackupError):
                change_applier._backup_file(src)

    # _restore_backup happy path
    def test__restore_backup_copies_and_returns_true(self, change_applier, file_factory, tmp_path):
        target = file_factory("target.py", "orig = True\n")
        backup = tmp_path / "somebackup.bak"
        backup.write_text("restored = True\n", encoding="utf-8")
        result = change_applier._restore_backup(target, backup)
        assert result is True
        assert target.read_text(encoding="utf-8") == "restored = True\n"

    # _restore_backup error: missing backup
    def test__restore_backup_raises_BackupError_if_backup_missing(self, change_applier, tmp_path):
        target = tmp_path / "t.py"
        target.write_text("a=1\n", encoding="utf-8")
        missing = tmp_path / "missing.bak"
        with pytest.raises(BackupError):
            change_applier._restore_backup(target, missing)

    # _restore_backup error: shutil.copy2 raises -> BackupError
    def test__restore_backup_wraps_copy_errors_in_BackupError(self, change_applier, file_factory, tmp_path):
        target = file_factory("t2.py", "a=1\n")
        backup = tmp_path / "b2.bak"
        backup.write_text("b=2\n", encoding="utf-8")
        with patch("branch_fixer.services.code.change_applier.shutil.copy2", side_effect=OSError("copy fail")):
            with pytest.raises(BackupError):
                change_applier._restore_backup(target, backup)

    # _verify_changes happy path
    def test__verify_changes_returns_true_for_valid_python(self, change_applier, file_factory):
        f = file_factory("good.py", "x = 1\n\ndef fn():\n    return x\n")
        assert change_applier._verify_changes(f) is True

    # _verify_changes syntax error path
    def test__verify_changes_returns_false_for_syntax_error(self, change_applier, file_factory):
        f = file_factory("bad.py", "x = )\n")
        assert change_applier._verify_changes(f) is False

    # _verify_changes other read error
    def test__verify_changes_returns_false_on_read_error(self, change_applier, file_factory):
        f = file_factory("some.py", "ok = True\n")
        with patch("pathlib.Path.read_text", side_effect=Exception("read fail")):
            assert change_applier._verify_changes(f) is False

    # _apply_changes_core happy path with both ```python and ``` fences
    @pytest.mark.parametrize("fence", ("```python\nx=1\n```", "```\nx=1\n```"))
    def test__apply_changes_core_writes_cleaned_code_and_returns_true(self, change_applier, file_factory, tmp_path, fence):
        original = "orig = 0\n"
        test_file = file_factory("fenced.py", original)
        # create a backup to restore from if needed
        backup = change_applier._backup_file(test_file)
        changes = SimpleNamespace(original_code=original, modified_code=fence)
        result = change_applier._apply_changes_core(test_file, changes, backup)
        assert result is True
        assert test_file.read_text(encoding="utf-8") == "x=1"

    # _apply_changes_core detects syntax error and restores backup
    def test__apply_changes_core_detects_syntax_error_and_restores_backup(self, change_applier, file_factory):
        original = "a = 1\n"
        test_file = file_factory("syntax_fail.py", original)
        backup = change_applier._backup_file(test_file)
        changes = SimpleNamespace(original_code=original, modified_code="x = )")
        result = change_applier._apply_changes_core(test_file, changes, backup)
        assert result is False
        # content restored from backup
        assert test_file.read_text(encoding="utf-8") == original

    # _apply_changes_core: write raises, but restore via shutil.copy2 succeeds
    def test__apply_changes_core_if_write_raises_attempts_restore_and_returns_false(self, change_applier, file_factory):
        original = "orig_w = 1\n"
        test_file = file_factory("write_err.py", original)
        backup = change_applier._backup_file(test_file)
        changes = SimpleNamespace(original_code=original, modified_code="valid = 2\n")
        def raise_on_write(self, *args, **kwargs):
            raise Exception("disk full")
        with patch("pathlib.Path.write_text", side_effect=raise_on_write):
            result = change_applier._apply_changes_core(test_file, changes, backup)
        assert result is False
        # restore should have succeeded (copied backup content back)
        assert test_file.read_text(encoding="utf-8") == original

    # _apply_changes_core: both write and restore raise, swallowed and returns False
    def test__apply_changes_core_restore_failure_is_swallowed_and_returns_false(self, change_applier, file_factory):
        original = "orig_w2 = 3\n"
        test_file = file_factory("write_err2.py", original)
        backup = change_applier._backup_file(test_file)
        changes = SimpleNamespace(original_code=original, modified_code="valid2 = 4\n")
        def raise_on_write(self, *args, **kwargs):
            raise Exception("write fail")
        def raise_on_restore(*args, **kwargs):
            raise BackupError("restore fail")
        with patch("pathlib.Path.write_text", side_effect=raise_on_write):
            with patch.object(ChangeApplier, "_restore_backup", side_effect=raise_on_restore):
                result = change_applier._apply_changes_core(test_file, changes, backup)
        assert result is False

    # apply_changes_with_backup happy path
    @pytest.mark.parametrize("modified", ("```python\nz=9\n```", "z=9\n"))
    def test_apply_changes_with_backup_success_applies_and_returns_backup(self, change_applier, file_factory, tmp_path, modified):
        original = "before = 1\n"
        test_file = file_factory("apply_ok.py", original)
        changes = SimpleNamespace(original_code=original, modified_code=modified)
        success, backup_path = change_applier.apply_changes_with_backup(test_file, changes)
        assert success is True
        assert isinstance(backup_path, Path)
        assert backup_path.exists()
        # file now contains cleaned code
        assert test_file.read_text(encoding="utf-8") == "z=9"

        # backup still has original content
        assert backup_path.read_text(encoding="utf-8") == original

    # apply_changes_with_backup: non-existent source returns (False, None)
    def test_apply_changes_with_backup_nonexistent_source_returns_false_and_none(self, change_applier, tmp_path):
        missing = tmp_path / "no_file.py"
        changes = SimpleNamespace(original_code="", modified_code="x=1\n")
        result = change_applier.apply_changes_with_backup(missing, changes)
        assert result == (False, None)

    # apply_changes_with_backup: when apply core returns False (syntax error), returns False and backup exists and file restored
    def test_apply_changes_with_backup_when_apply_core_returns_false_restores_original(self, change_applier, file_factory):
        original = "orig_apply = 5\n"
        test_file = file_factory("apply_fail.py", original)
        changes = SimpleNamespace(original_code=original, modified_code="x = )")
        success, backup_path = change_applier.apply_changes_with_backup(test_file, changes)
        assert success is False
        assert isinstance(backup_path, Path)
        assert backup_path.exists()
        # file content restored
        assert test_file.read_text(encoding="utf-8") == original

    # apply_changes_with_backup: if _backup_file returns None, it's handled and returns (False, None)
    def test_apply_changes_with_backup_when_backup_returns_none_is_handled(self, file_factory, tmp_path):
        ca = ChangeApplier()
        test_file = file_factory("some_none.py", "a=1\n")
        changes = SimpleNamespace(original_code="a=1\n", modified_code="b=2\n")
        with patch.object(ChangeApplier, "_backup_file", return_value=None):
            result = ca.apply_changes_with_backup(test_file, changes)
        assert result == (False, None)

    # apply_changes_with_backup: if _apply_changes_core raises, method catches and returns (False, backup)
    def test_apply_changes_with_backup_when_apply_core_raises_exception_returns_false(self, change_applier, file_factory):
        original = "orig_raise = 7\n"
        test_file = file_factory("apply_raise.py", original)
        backup_path = change_applier._backup_file(test_file)
        changes = SimpleNamespace(original_code=original, modified_code="x=1\n")
        with patch.object(ChangeApplier, "_apply_changes_core", side_effect=Exception("boom")):
            success, bp = change_applier.apply_changes_with_backup(test_file, changes)
        assert success is False
        assert isinstance(bp, Path)
        assert bp.exists()

    # restore_backup public wrapper: success
    def test_restore_backup_success_restores_file(self, change_applier, file_factory, tmp_path):
        target = file_factory("restore_target.py", "old = True\n")
        backup = tmp_path / "mybackup.bak"
        backup.write_text("new = True\n", encoding="utf-8")
        result = change_applier.restore_backup(target, backup)
        assert result is True
        assert target.read_text(encoding="utf-8") == "new = True\n"

    # restore_backup public wrapper: missing backup raises BackupError
    def test_restore_backup_missing_backup_raises_BackupError(self, change_applier, tmp_path):
        target = tmp_path / "restore_target2.py"
        target.write_text("x=1\n", encoding="utf-8")
        missing = tmp_path / "no.bak"
        with pytest.raises(BackupError):
            change_applier.restore_backup(target, missing)