import logging
from pathlib import Path

from branch_fixer.services.git.pr_manager import PRManager
from branch_fixer.config.logging_config import setup_logging


def test_create_pr_propagates_modified_files_and_metadata_into_pr_details():
    """F11: create_pr must forward modified_files/metadata into the returned PRDetails,
    not silently discard them (src/branch_fixer/services/git/pr_manager.py:102-110)."""
    manager = PRManager(repository=object())
    modified_files = [Path("file1.py"), Path("dir/file2.py")]
    metadata = {"reviewer": "alice", "priority": 5}

    details = manager.create_pr(
        title="Title",
        description="Desc",
        branch_name="branch",
        modified_files=modified_files,
        metadata=metadata,
    )

    assert details.modified_files == modified_files
    assert details.metadata == metadata


def test_repeated_setup_logging_calls_keep_snoop_handler_count_stable(monkeypatch, tmp_path):
    """F12: repeated setup_logging() calls must not keep appending new FileHandlers to the
    'snoop' logger (src/branch_fixer/config/logging_config.py:30-37)."""
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))

    for h in list(logging.root.handlers):
        logging.root.removeHandler(h)
        h.close()
    snoop_logger = logging.getLogger("snoop")
    for h in list(snoop_logger.handlers):
        snoop_logger.removeHandler(h)
        h.close()

    try:
        setup_logging()
        snoop_handlers_before = list(snoop_logger.handlers)

        setup_logging()
        snoop_handlers_after = list(snoop_logger.handlers)

        assert len(snoop_handlers_after) == len(snoop_handlers_before)
    finally:
        for h in list(logging.root.handlers):
            logging.root.removeHandler(h)
            h.close()
        for h in list(snoop_logger.handlers):
            snoop_logger.removeHandler(h)
            h.close()
