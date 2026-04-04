import asyncio
import json
import uuid
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

import branch_fixer.storage.recovery as recovery_module
from branch_fixer.storage.recovery import (
    RecoveryPoint,
    RecoveryManager,
    RecoveryError,
    CheckpointError,
    RestoreError,
)


# Module-level fixtures
@pytest.fixture
def session_store():
    """
    Provide a Mock acting as a session store with a `save_session` method.
    
    Returns:
        Mock: a unittest.mock.Mock configured to represent a session store, intended to receive `save_session(session)` calls in tests.
    """
    return Mock()


@pytest.fixture
def git_repo():
    """
    Simple mock git repository stub.
    get_current_branch returns 'main' by default.
    run_command returns an object with attributes `failed` and `stderr`.
    """
    m = Mock()
    m.get_current_branch.return_value = "main"
    m.run_command.return_value = SimpleNamespace(failed=False, stderr="")
    return m


class TestRecoveryPoint:
    def test_create_basic_and_id_length_and_timestamp(self, monkeypatch):
        fixed_time = 1_625_000_000.0
        monkeypatch.setattr(recovery_module.time, "time", lambda: fixed_time)
        sid = uuid.uuid4()
        files = [Path("a.py"), Path("dir/b.txt")]
        metadata = {"k": "v"}

        rp = RecoveryPoint.create(session_id=sid, git_branch="feature/x", modified_files=files, metadata=metadata)

        assert isinstance(rp, RecoveryPoint)
        assert rp.session_id == sid
        assert rp.git_branch == "feature/x"
        assert rp.modified_files == files
        assert rp.metadata == metadata
        # id is first 12 hex chars
        assert isinstance(rp.id, str) and len(rp.id) == 12
        # timestamp matches patched time
        assert rp.timestamp == fixed_time

    def test_to_json_and_from_json_roundtrip(self, monkeypatch):
        fixed_time = 1_600_000_000.0
        monkeypatch.setattr(recovery_module.time, "time", lambda: fixed_time)
        sid = uuid.uuid4()
        files = [Path("c.py")]
        metadata = {"m": 1}

        rp = RecoveryPoint.create(session_id=sid, git_branch="main", modified_files=files, metadata=metadata)
        j = rp.to_json()
        # JSON has stringified session_id and file paths
        assert j["session_id"] == str(sid)
        assert j["modified_files"] == [str(files[0])]
        assert j["metadata"] == metadata

        rp2 = RecoveryPoint.from_json(j)
        assert isinstance(rp2, RecoveryPoint)
        assert rp2.id == rp.id
        assert rp2.session_id == rp.session_id
        assert rp2.timestamp == rp.timestamp
        assert rp2.git_branch == rp.git_branch
        assert rp2.modified_files == rp.modified_files
        assert rp2.metadata == rp.metadata

    @pytest.mark.parametrize(
        "bad_data, expected_exception",
        [
            ({"id": "x", "session_id": "not-a-uuid", "timestamp": 1.0, "git_branch": "b", "modified_files": [], "metadata": {}}, ValueError),
            ({"session_id": str(uuid.uuid4()), "timestamp": 1.0}, KeyError),
        ],
    )
    def test_from_json_invalid_inputs_raise(self, bad_data, expected_exception):
        with pytest.raises(expected_exception):
            RecoveryPoint.from_json(bad_data)


class TestExceptions:
    def test_custom_exceptions_are_subclasses(self):
        assert isinstance(CheckpointError("e"), RecoveryError)
        assert isinstance(RestoreError("e"), RecoveryError)
        assert isinstance(RecoveryError("e"), Exception)


class TestRecoveryManager:
    def test_init_creates_backup_dir_and_index(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "backups"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        assert backup_dir.exists() and backup_dir.is_dir()
        idx = backup_dir / "recovery_points.json"
        assert idx.exists()
        content = idx.read_text(encoding="utf-8")
        assert content == "[]"
        # attributes set
        assert manager.session_store is session_store
        assert manager.git_repo is git_repo
        assert manager.backup_dir == backup_dir

    def test_init_raises_value_error_when_parent_missing(self, tmp_path, session_store, git_repo):
        # parent of backup_dir does not exist
        nonexisting_parent = tmp_path / "no_such_parent"
        backup_dir = nonexisting_parent / "subdir"
        # Ensure parent truly does not exist
        if nonexisting_parent.exists():
            nonexisting_parent.unlink()
        with pytest.raises(ValueError):
            RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

    def test_init_raises_permission_error_when_not_writable(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bd"
        # Patch os.access within the recovery module to simulate not writable
        with patch("branch_fixer.storage.recovery.os.access", return_value=False):
            with pytest.raises(PermissionError):
                RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

    @pytest.mark.asyncio
    async def test_create_checkpoint_saves_rp_and_calls_session_store(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        # Prepare a simple session-like object
        sid = uuid.uuid4()
        session = SimpleNamespace(id=sid, modified_files=[backup_dir / "file1.txt"])
        # ensure file exists per rule about file operations
        (backup_dir / "file1.txt").write_text("content", encoding="utf-8")

        rp = await manager.create_checkpoint(session, metadata={"a": 1})

        # check returned rp
        assert isinstance(rp, RecoveryPoint)
        assert rp.session_id == sid
        assert rp.metadata == {"a": 1}

        # session_store.save_session should have been called with the session
        session_store.save_session.assert_called_once_with(session)

        # index file should contain the rp
        idx = backup_dir / "recovery_points.json"
        data = json.loads(idx.read_text(encoding="utf-8"))
        assert any(entry["id"] == rp.id for entry in data)

    @pytest.mark.asyncio
    async def test_create_checkpoint_propagates_as_checkpoint_error_on_inner_exception(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk2"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        # make session_store.save_session raise
        session_store.save_session.side_effect = RuntimeError("boom")
        session = SimpleNamespace(id=uuid.uuid4(), modified_files=[])

        with pytest.raises(CheckpointError) as excinfo:
            await manager.create_checkpoint(session, metadata=None)
        assert "boom" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_checkpoint_metadata_defaults_to_empty_dict(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk3"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        session = SimpleNamespace(id=uuid.uuid4(), modified_files=[])
        rp = await manager.create_checkpoint(session, metadata=None)
        assert rp.metadata == {}

    @pytest.mark.asyncio
    async def test_restore_checkpoint_not_found_raises_restore_error(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk4"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        with pytest.raises(RestoreError) as excinfo:
            await manager.restore_checkpoint("no-such-id")
        # message should mention checkpoint id or not found
        assert "no-such-id" in str(excinfo.value) or "not found" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_restore_checkpoint_branch_matches_removes_checkpoint_when_cleanup_true(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk5"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[Path("f")], metadata={})
        manager._save_recovery_point(rp)

        # current branch from git_repo is "main" by fixture default
        result = await manager.restore_checkpoint(rp.id, cleanup=True)
        assert result is True

        # ensure removed
        assert manager._load_recovery_point(rp.id) is None

    @pytest.mark.asyncio
    async def test_restore_checkpoint_branch_mismatch_checkout_success(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk6"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="feature/1", modified_files=[Path("f")], metadata={})
        manager._save_recovery_point(rp)

        # simulate current branch different
        git_repo.get_current_branch.return_value = "main"

        # simulate successful checkout
        git_repo.run_command.return_value = SimpleNamespace(failed=False, stderr="")
        result = await manager.restore_checkpoint(rp.id, cleanup=True)
        assert result is True
        # run_command called to checkout the rp.git_branch
        git_repo.run_command.assert_called_with(["checkout", rp.git_branch])
        # entry removed
        assert manager._load_recovery_point(rp.id) is None

    @pytest.mark.asyncio
    async def test_restore_checkpoint_checkout_failure_raises_restore_error_and_keeps_checkpoint(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk7"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="feature/bad", modified_files=[Path("f")], metadata={})
        manager._save_recovery_point(rp)

        git_repo.get_current_branch.return_value = "main"
        git_repo.run_command.return_value = SimpleNamespace(failed=True, stderr="conflict occurred")

        with pytest.raises(RestoreError) as excinfo:
            await manager.restore_checkpoint(rp.id, cleanup=True)
        assert "conflict occurred" in str(excinfo.value)
        # ensure checkpoint still exists (cleanup should not have been performed)
        assert manager._load_recovery_point(rp.id) is not None

    @pytest.mark.asyncio
    async def test_restore_checkpoint_cleanup_false_keeps_checkpoint(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk8"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[Path("f")], metadata={})
        manager._save_recovery_point(rp)

        result = await manager.restore_checkpoint(rp.id, cleanup=False)
        assert result is True
        # checkpoint should still be present
        assert manager._load_recovery_point(rp.id) is not None

    @pytest.mark.asyncio
    async def test_handle_failure_no_checkpoints_returns_false(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk9"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        session = SimpleNamespace(id=uuid.uuid4(), modified_files=[])
        result = await manager.handle_failure(Exception("x"), session, context={})
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_failure_calls_restore_with_cleanup_false_and_returns_true(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk10"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        # create two recovery points with different timestamps
        rp_old = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[], metadata={})
        # slightly later timestamp
        with patch("branch_fixer.storage.recovery.time.time", lambda: rp_old.timestamp + 10):
            rp_new = RecoveryPoint.create(session_id=rp_old.session_id, git_branch="main", modified_files=[], metadata={})

        # populate index manually
        manager._save_recovery_point(rp_old)
        manager._save_recovery_point(rp_new)

        # Spy on restore_checkpoint by replacing it with an async function
        called = {}

        async def fake_restore(cpid, cleanup=False):
            """
            Test helper that records the provided checkpoint id and cleanup flag, then simulates a successful restore.
            
            Parameters:
                cpid (str): Checkpoint id passed to the restore operation.
                cleanup (bool): Whether the caller requested cleanup after restore.
            
            Returns:
                bool: `True` indicating the simulated restore succeeded.
            """
            called["id"] = cpid
            called["cleanup"] = cleanup
            return True

        # patch the instance method
        manager.restore_checkpoint = fake_restore

        session = SimpleNamespace(id=rp_old.session_id, modified_files=[])
        result = await manager.handle_failure(Exception("boom"), session, context={})
        assert result is True
        # latest rp should have been used (rp_new)
        assert called["id"] == rp_new.id
        assert called["cleanup"] is False

    @pytest.mark.asyncio
    async def test_handle_failure_restore_raises_restoreerror_returns_false(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk11"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[], metadata={})
        manager._save_recovery_point(rp)

        async def raising_restore(_cid, cleanup=False):
            """
            Raises a RestoreError with the message "fail".
            
            Raises:
                RestoreError: always raised when called.
            """
            raise RestoreError("fail")

        manager.restore_checkpoint = raising_restore

        session = SimpleNamespace(id=rp.session_id, modified_files=[])
        result = await manager.handle_failure(Exception("err"), session, context={"x": 1})
        assert result is False

    def test_save_recovery_point_appends_to_index(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk12"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[Path("f")], metadata={"a": 2})
        manager._save_recovery_point(rp)

        content = json.loads((backup_dir / "recovery_points.json").read_text(encoding="utf-8"))
        assert any(entry["id"] == rp.id for entry in content)

    def test_save_recovery_point_raises_on_invalid_json(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk13"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        # write invalid JSON to index file
        idx = backup_dir / "recovery_points.json"
        idx.write_text("not a json", encoding="utf-8")

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[Path("f")], metadata={})
        with pytest.raises(json.JSONDecodeError):
            manager._save_recovery_point(rp)

    def test_load_recovery_point_returns_rp_when_present(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk14"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[Path("f")], metadata={})
        manager._save_recovery_point(rp)

        loaded = manager._load_recovery_point(rp.id)
        assert loaded is not None
        assert isinstance(loaded, RecoveryPoint)
        assert loaded.id == rp.id

    def test_load_recovery_point_returns_none_when_missing(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk15"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        assert manager._load_recovery_point("absent-id") is None

    def test_load_recovery_point_propagates_on_invalid_json(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk16"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        idx = backup_dir / "recovery_points.json"
        idx.write_text("{invalid", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            manager._load_recovery_point("any")

    def test_remove_recovery_point_deletes_entry(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk17"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp1 = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[Path("1")], metadata={})
        rp2 = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[Path("2")], metadata={})
        manager._save_recovery_point(rp1)
        manager._save_recovery_point(rp2)

        # remove rp1
        manager._remove_recovery_point(rp1.id)
        assert manager._load_recovery_point(rp1.id) is None
        # rp2 still present
        assert manager._load_recovery_point(rp2.id) is not None

    def test_remove_recovery_point_id_not_present_no_change(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk18"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        rp = RecoveryPoint.create(session_id=uuid.uuid4(), git_branch="main", modified_files=[], metadata={})
        manager._save_recovery_point(rp)

        before = json.loads((backup_dir / "recovery_points.json").read_text(encoding="utf-8"))
        manager._remove_recovery_point("no-such-id")
        after = json.loads((backup_dir / "recovery_points.json").read_text(encoding="utf-8"))
        assert before == after

    def test_list_recovery_points_returns_only_for_session(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk19"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        sid1 = uuid.uuid4()
        sid2 = uuid.uuid4()
        rp1 = RecoveryPoint.create(session_id=sid1, git_branch="main", modified_files=[], metadata={})
        rp2 = RecoveryPoint.create(session_id=sid2, git_branch="main", modified_files=[], metadata={})
        rp3 = RecoveryPoint.create(session_id=sid1, git_branch="main", modified_files=[], metadata={})
        manager._save_recovery_point(rp1)
        manager._save_recovery_point(rp2)
        manager._save_recovery_point(rp3)

        list_for_sid1 = manager._list_recovery_points_for_session(sid1)
        assert len(list_for_sid1) == 2
        assert all(r.session_id == sid1 for r in list_for_sid1)

    def test_list_recovery_points_returns_empty_when_none(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk20"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        sid = uuid.uuid4()
        assert manager._list_recovery_points_for_session(sid) == []

    def test_list_recovery_points_propagates_on_invalid_json(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk21"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        idx = backup_dir / "recovery_points.json"
        idx.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            manager._list_recovery_points_for_session(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_end_to_end_checkpoint_and_restore_cycle(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk22"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        sid = uuid.uuid4()
        session = SimpleNamespace(id=sid, modified_files=[backup_dir / "x.txt"])
        (backup_dir / "x.txt").write_text("hello", encoding="utf-8")

        rp = await manager.create_checkpoint(session, metadata={"end": True})
        assert manager._load_recovery_point(rp.id) is not None

        # restore when branch matches
        git_repo.get_current_branch.return_value = rp.git_branch
        restored = await manager.restore_checkpoint(rp.id, cleanup=True)
        assert restored is True
        assert manager._load_recovery_point(rp.id) is None

    @pytest.mark.asyncio
    async def test_restore_with_checkout_sequence(self, tmp_path, session_store, git_repo):
        backup_dir = tmp_path / "bk23"
        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)

        sid = uuid.uuid4()
        rp = RecoveryPoint.create(session_id=sid, git_branch="feature/seq", modified_files=[Path("a")], metadata={})
        manager._save_recovery_point(rp)

        # current branch different
        git_repo.get_current_branch.return_value = "develop"
        # simulate successful checkout
        git_repo.run_command.return_value = SimpleNamespace(failed=False, stderr="")
        ok = await manager.restore_checkpoint(rp.id, cleanup=True)
        assert ok is True
        git_repo.run_command.assert_called_with(["checkout", rp.git_branch])
        assert manager._load_recovery_point(rp.id) is None