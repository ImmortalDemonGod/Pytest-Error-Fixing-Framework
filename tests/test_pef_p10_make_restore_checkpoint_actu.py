import logging
import uuid
from types import SimpleNamespace
from unittest.mock import Mock

from branch_fixer.storage.recovery import RecoveryManager


def _session_store():
    return Mock()


def _git_repo():
    m = Mock()
    m.get_current_branch.return_value = "main"
    m.run_command.return_value = SimpleNamespace(failed=False, stderr="")
    return m


async def test_restore_checkpoint_restores_modified_file_content_from_backup(tmp_path):
    manager = RecoveryManager(
        session_store=_session_store(), git_repo=_git_repo(), backup_dir=tmp_path / "backups"
    )

    target_file = tmp_path / "target.py"
    target_file.write_text("content A", encoding="utf-8")

    session = SimpleNamespace(id=uuid.uuid4(), modified_files=[target_file])
    rp = await manager.create_checkpoint(session, metadata={})

    # Mutate the file after the checkpoint was taken.
    target_file.write_text("content B", encoding="utf-8")

    restored = await manager.restore_checkpoint(rp.id, cleanup=False)

    assert restored is True
    assert target_file.read_text(encoding="utf-8") == "content A"


async def test_handle_failure_reports_diagnostics_via_logger_not_stdout(tmp_path, caplog, capsys):
    manager = RecoveryManager(
        session_store=_session_store(), git_repo=_git_repo(), backup_dir=tmp_path / "backups2"
    )

    session = SimpleNamespace(id=uuid.uuid4(), modified_files=[])

    with caplog.at_level(logging.WARNING, logger="branch_fixer.storage.recovery"):
        result = await manager.handle_failure(Exception("boom"), session, context={})

    assert result is False

    captured = capsys.readouterr()
    assert captured.out == ""
    assert any(
        "No recovery points to restore" in record.message for record in caplog.records
    )
