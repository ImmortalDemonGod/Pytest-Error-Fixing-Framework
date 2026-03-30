"""Tests for RecoveryPoint and RecoveryManager — checkpoint storage and retrieval."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from branch_fixer.storage.recovery import (
    CheckpointError,
    RecoveryManager,
    RecoveryPoint,
    RestoreError,
)


# ---------------------------------------------------------------------------
# RecoveryPoint
# ---------------------------------------------------------------------------

class TestRecoveryPointCreate:
    def test_create_returns_recovery_point(self):
        sid = uuid4()
        rp = RecoveryPoint.create(sid, "main", [], {})
        assert isinstance(rp, RecoveryPoint)

    def test_create_sets_session_id(self):
        sid = uuid4()
        rp = RecoveryPoint.create(sid, "main", [], {})
        assert rp.session_id == sid

    def test_create_sets_git_branch(self):
        sid = uuid4()
        rp = RecoveryPoint.create(sid, "fix/my-branch", [], {})
        assert rp.git_branch == "fix/my-branch"

    def test_create_sets_modified_files(self):
        sid = uuid4()
        files = [Path("tests/test_foo.py")]
        rp = RecoveryPoint.create(sid, "main", files, {})
        assert rp.modified_files == files

    def test_create_sets_metadata(self):
        sid = uuid4()
        rp = RecoveryPoint.create(sid, "main", [], {"reason": "test"})
        assert rp.metadata == {"reason": "test"}

    def test_create_id_is_12_chars(self):
        rp = RecoveryPoint.create(uuid4(), "main", [], {})
        assert len(rp.id) == 12

    def test_create_id_is_hex(self):
        rp = RecoveryPoint.create(uuid4(), "main", [], {})
        int(rp.id, 16)  # Should not raise


class TestRecoveryPointSerialization:
    def test_to_json_round_trip(self):
        sid = uuid4()
        original = RecoveryPoint.create(sid, "main", [Path("tests/foo.py")], {"k": "v"})
        restored = RecoveryPoint.from_json(original.to_json())
        assert restored.id == original.id
        assert restored.session_id == original.session_id
        assert restored.git_branch == original.git_branch
        assert restored.modified_files == original.modified_files
        assert restored.metadata == original.metadata

    def test_to_json_has_required_keys(self):
        rp = RecoveryPoint.create(uuid4(), "main", [], {})
        data = rp.to_json()
        for key in ("id", "session_id", "timestamp", "git_branch", "modified_files", "metadata"):
            assert key in data

    def test_session_id_is_string_in_json(self):
        rp = RecoveryPoint.create(uuid4(), "main", [], {})
        data = rp.to_json()
        assert isinstance(data["session_id"], str)

    def test_modified_files_are_strings_in_json(self):
        rp = RecoveryPoint.create(uuid4(), "main", [Path("a/b.py")], {})
        data = rp.to_json()
        assert all(isinstance(f, str) for f in data["modified_files"])


# ---------------------------------------------------------------------------
# RecoveryManager — init
# ---------------------------------------------------------------------------

class TestRecoveryManagerInit:
    def test_creates_backup_dir(self, tmp_path):
        backup = tmp_path / "backups"
        RecoveryManager(MagicMock(), MagicMock(), backup)
        assert backup.exists()

    def test_raises_if_parent_missing(self, tmp_path):
        with pytest.raises(ValueError):
            RecoveryManager(MagicMock(), MagicMock(), tmp_path / "ghost" / "deep" / "backups")

    def test_creates_recovery_index_file(self, tmp_path):
        backup = tmp_path / "backups"
        rm = RecoveryManager(MagicMock(), MagicMock(), backup)
        assert rm.recovery_index_file.exists()

    def test_index_file_starts_as_empty_list(self, tmp_path):
        backup = tmp_path / "backups"
        rm = RecoveryManager(MagicMock(), MagicMock(), backup)
        data = json.loads(rm.recovery_index_file.read_text())
        assert data == []


# ---------------------------------------------------------------------------
# RecoveryManager — internal helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def rm(tmp_path):
    return RecoveryManager(MagicMock(), MagicMock(), tmp_path / "backups")


def make_rp(session_id=None) -> RecoveryPoint:
    return RecoveryPoint.create(session_id or uuid4(), "main", [], {"test": True})


class TestSaveLoadRecoveryPoint:
    def test_save_then_load_by_id(self, rm):
        rp = make_rp()
        rm._save_recovery_point(rp)
        loaded = rm._load_recovery_point(rp.id)
        assert loaded is not None
        assert loaded.id == rp.id

    def test_load_returns_none_for_missing_id(self, rm):
        assert rm._load_recovery_point("nonexistent") is None

    def test_save_multiple_recoverable(self, rm):
        rp1 = make_rp()
        rp2 = make_rp()
        rm._save_recovery_point(rp1)
        rm._save_recovery_point(rp2)
        assert rm._load_recovery_point(rp1.id) is not None
        assert rm._load_recovery_point(rp2.id) is not None

    def test_index_file_is_valid_json(self, rm):
        rm._save_recovery_point(make_rp())
        data = json.loads(rm.recovery_index_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 1


class TestRemoveRecoveryPoint:
    def test_remove_existing_point(self, rm):
        rp = make_rp()
        rm._save_recovery_point(rp)
        rm._remove_recovery_point(rp.id)
        assert rm._load_recovery_point(rp.id) is None

    def test_remove_only_target_not_others(self, rm):
        rp1 = make_rp()
        rp2 = make_rp()
        rm._save_recovery_point(rp1)
        rm._save_recovery_point(rp2)
        rm._remove_recovery_point(rp1.id)
        assert rm._load_recovery_point(rp2.id) is not None

    def test_remove_nonexistent_is_noop(self, rm):
        rp = make_rp()
        rm._save_recovery_point(rp)
        rm._remove_recovery_point("not-a-real-id")
        assert rm._load_recovery_point(rp.id) is not None


class TestListRecoveryPoints:
    def test_empty_for_unknown_session(self, rm):
        assert rm._list_recovery_points_for_session(uuid4()) == []

    def test_returns_only_matching_session(self, rm):
        sid1 = uuid4()
        sid2 = uuid4()
        rp1 = make_rp(sid1)
        rp2 = make_rp(sid2)
        rm._save_recovery_point(rp1)
        rm._save_recovery_point(rp2)
        result = rm._list_recovery_points_for_session(sid1)
        assert len(result) == 1
        assert result[0].session_id == sid1

    def test_returns_multiple_for_same_session(self, rm):
        sid = uuid4()
        rm._save_recovery_point(make_rp(sid))
        rm._save_recovery_point(make_rp(sid))
        result = rm._list_recovery_points_for_session(sid)
        assert len(result) == 2
