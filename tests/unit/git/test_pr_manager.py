import pytest
import types
import datetime as real_datetime
from pathlib import Path

import branch_fixer.services.git.pr_manager as pr_manager_module
from branch_fixer.services.git.pr_manager import PRManager


@pytest.fixture
def fake_repo():
    """A simple fake repository object to pass into PRManager."""
    return object()


@pytest.fixture
def patched_types(monkeypatch):
    """
    Patch PRDetails, PRStatus, PRUpdateError, and the module-level datetime.now()
    so tests can assert deterministic behavior and control exception types.
    """
    # Fake PRDetails that stores attributes provided by create_pr
    class FakePRDetails:
        def __init__(self, *, id, title, description, branch_name, status, created_at, url=None):
            self.id = id
            self.title = title
            self.description = description
            self.branch_name = branch_name
            self.status = status
            self.created_at = created_at
            self.url = url

        def __repr__(self):
            return f"<FakePRDetails id={self.id} title={self.title!r}>"

    # Fake PRStatus with OPEN sentinel
    class FakePRStatus:
        OPEN = object()
        MERGED = object()
        CLOSED = object()

    # Fake PRUpdateError exception type
    class FakePRUpdateError(Exception):
        pass

    # Dummy datetime replacement with deterministic now()
    class DummyDateTime:
        @classmethod
        def now(cls):
            return real_datetime.datetime(2000, 1, 1, 12, 0, 0)

    # Apply monkeypatches to the module under test
    monkeypatch.setattr(pr_manager_module, "PRDetails", FakePRDetails, raising=True)
    monkeypatch.setattr(pr_manager_module, "PRStatus", FakePRStatus, raising=True)
    monkeypatch.setattr(pr_manager_module, "PRUpdateError", FakePRUpdateError, raising=True)
    monkeypatch.setattr(pr_manager_module, "datetime", DummyDateTime, raising=True)

    # Provide the test doubles to tests if needed
    return {
        "PRDetails": FakePRDetails,
        "PRStatus": FakePRStatus,
        "PRUpdateError": FakePRUpdateError,
        "fixed_datetime": DummyDateTime.now(),
    }


@pytest.fixture
def pr_manager(fake_repo):
    """Create a PRManager instance with default settings."""
    return PRManager(repository=fake_repo)


class TestPRManager:
    # Happy path: initialization and attribute behavior
    def test___init___positive_max_files_sets_attributes(self, fake_repo):
        manager = PRManager(repository=fake_repo, max_files=5, required_checks=["ci"])
        assert manager.repository is fake_repo
        assert manager.max_files == 5
        assert manager.required_checks == ["ci"]
        assert isinstance(manager.prs, dict)
        assert manager.prs == {}

    def test___init___default_required_checks_is_empty_list_and_independent(self, fake_repo):
        m1 = PRManager(repository=fake_repo)
        m2 = PRManager(repository=fake_repo)
        # Both start with empty required_checks
        assert m1.required_checks == []
        assert m2.required_checks == []
        # Modifying one does not affect the other
        m1.required_checks.append("ci")
        assert m1.required_checks == ["ci"]
        assert m2.required_checks == []

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test___init___invalid_max_files_raises(self, fake_repo, invalid_value):
        with pytest.raises(ValueError) as exc:
            PRManager(repository=fake_repo, max_files=invalid_value)
        assert "max_files must be positive" in str(exc.value)

    # create_pr behavior
    def test_create_pr_returns_PRDetails_and_stores_it(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        title = "Add feature"
        description = "This PR adds a feature"
        branch_name = "feature/awesome"
        modified_files = [Path("a.txt")]
        metadata = {"key": "value"}

        details = manager.create_pr(
            title=title,
            description=description,
            branch_name=branch_name,
            modified_files=modified_files,
            metadata=metadata,
        )

        # PRDetails is our FakePRDetails and should be stored in prs with id 1
        assert details.id == 1
        assert details.title == title
        assert details.description == description
        assert details.branch_name == branch_name
        # status should be set to the module's PRStatus.OPEN sentinel
        assert details.status is pr_manager_module.PRStatus.OPEN
        # created_at should be the deterministic fixed datetime from patched_types
        assert details.created_at == patched_types["fixed_datetime"]
        assert manager.prs[1] is details

    def test_create_pr_increments_pr_id_on_multiple_creates(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        d1 = manager.create_pr("T1", "D1", "b1", [], None)
        d2 = manager.create_pr("T2", "D2", "b2", [], None)

        assert d1.id == 1
        assert d2.id == 2
        assert set(manager.prs.keys()) == {1, 2}
        assert manager.prs[1] is d1
        assert manager.prs[2] is d2

    def test_create_pr_accepts_modified_files_and_metadata_without_using_them(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        # Create some actual Path objects to pass in
        tmp_files = [Path("file1.py"), Path("dir/file2.py")]
        meta = {"reviewer": "alice", "priority": 5}
        details = manager.create_pr("Title", "Desc", "branch", tmp_files, meta)

        # Method doesn't raise and returns a PRDetails object stored in prs
        assert details.id == 1
        assert manager.prs[1] is details

    # update_pr (async) happy path and error
    @pytest.mark.asyncio
    async def test_update_pr_returns_existing_pr(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        created = manager.create_pr("T", "D", "b", [], None)
        # Await the async update_pr and expect the same object back
        result = await manager.update_pr(created.id, status=pr_manager_module.PRStatus.MERGED, metadata={"k": "v"}, reason="done")
        assert result is created

    @pytest.mark.asyncio
    async def test_update_pr_missing_pr_raises_PRUpdateError(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        # Attempting to update a non-existent PR should raise the module's PRUpdateError
        with pytest.raises(pr_manager_module.PRUpdateError) as exc:
            await manager.update_pr(999, status=None, metadata=None, reason=None)
        assert "PR not found" in str(exc.value)

    # validate_pr (async) behavior
    @pytest.mark.asyncio
    async def test_validate_pr_returns_true_for_existing_pr(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        created = manager.create_pr("T", "D", "b", [], None)
        is_valid = await manager.validate_pr(created.id)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_pr_returns_false_for_missing_pr(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        result = await manager.validate_pr(1)
        assert result is False

    # get_pr_history should raise NotImplementedError
    @pytest.mark.asyncio
    async def test_get_pr_history_raises_not_implemented(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        with pytest.raises(NotImplementedError):
            await manager.get_pr_history(1)

    # close_pr should raise NotImplementedError
    @pytest.mark.asyncio
    async def test_close_pr_raises_not_implemented(self, patched_types, fake_repo):
        manager = PRManager(repository=fake_repo)
        # Pass a PRStatus sentinel as required by signature
        status = pr_manager_module.PRStatus.CLOSED
        with pytest.raises(NotImplementedError):
            await manager.close_pr(1, status=status, reason="closing")