"""RED test for F49 (+ F60, F61) — see tests/pef-p24-implement-update-pr-mutation.bug-catalog.md.

Exercises the real PRManager/PRDetails/PRStatus from
src/branch_fixer/services/git/pr_manager.py against the CORRECT expected behavior. Currently
FAILS because update_pr is a no-op stub (F49), create_pr drops modified_files (F61), and
create_pr's id generation collides after a deletion (F60).
"""

from pathlib import Path

from branch_fixer.services.git.pr_manager import PRManager
from branch_fixer.services.git.models import PRStatus


def _make_manager():
    return PRManager(repository=object())


async def test_update_pr_mutates_status_metadata_and_appends_history():
    manager = _make_manager()
    created = manager.create_pr("Title", "Desc", "branch", [], {"existing": "value"})
    assert created.change_history == []

    result = await manager.update_pr(
        created.id,
        status=PRStatus.MERGED,
        metadata={"new": "field"},
        reason="merged after review",
    )

    assert result.status == PRStatus.MERGED
    assert result.metadata == {"existing": "value", "new": "field"}
    assert len(result.change_history) == 1


def test_create_pr_stores_modified_files():
    manager = _make_manager()
    files = [Path("a.py"), Path("b.py")]

    details = manager.create_pr("Title", "Desc", "branch", files)

    assert details.modified_files == files


def test_create_pr_id_does_not_collide_after_deletion():
    manager = _make_manager()
    first = manager.create_pr("T1", "D1", "b1", [])
    second = manager.create_pr("T2", "D2", "b2", [])

    del manager.prs[second.id]

    third = manager.create_pr("T3", "D3", "b3", [])

    assert third.id not in (first.id, second.id)
