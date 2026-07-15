# RED test for the finding — import verified by the harness; expected value from the finding's own command (see FACT).
from src.branch_fixer.storage.recovery import CheckpointError, RecoveryManager, RecoveryPoint  # verified working import — do not edit


def test_checkpointerror_pins_the_finding_defect():
    # F83: RecoveryManager.create_checkpoint is `async def`, but orchestrator.py:516
    # calls it synchronously (no await): `checkpoint = self.recovery_manager.create_checkpoint(...)`.
    # The CORRECT behavior (goal of the fix) is that a synchronous call site gets back a
    # real RecoveryPoint so `checkpoint.id` works. Today it gets back an un-awaited
    # coroutine object instead, which is the bug this test pins.
    import tempfile
    import uuid
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import Mock

    with tempfile.TemporaryDirectory() as tmp:
        backup_dir = Path(tmp) / "backups"
        session_store = Mock()
        git_repo = Mock()
        git_repo.get_current_branch.return_value = "main"

        manager = RecoveryManager(session_store=session_store, git_repo=git_repo, backup_dir=backup_dir)
        session = SimpleNamespace(id=uuid.uuid4(), modified_files=[])

        # Mirrors orchestrator.py:516 exactly: no `await` at the call site.
        checkpoint = manager.create_checkpoint(session, {"label": "test"})

        assert isinstance(checkpoint, RecoveryPoint), (
            "create_checkpoint() must return a RecoveryPoint when called synchronously "
            f"(as orchestrator.py's _create_checkpoint_if_needed does); got "
            f"{type(checkpoint).__name__} instead, which has no `.id` attribute and "
            "would raise AttributeError at orchestrator.py:518"
        )
