import os
from types import SimpleNamespace
from pathlib import Path
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from unittest.mock import patch

import branch_fixer.storage.session_store as ss_mod
from branch_fixer.storage.session_store import (
    SessionStore,
    StorageError,
    SessionPersistenceError,
    FixSessionState,
)


class TestStorageError:
    def test_storage_error_is_exception_subclass_and_catchable(self):
        assert issubclass(StorageError, Exception)
        try:
            raise StorageError("boom")
        except Exception as e:
            # Should be caught as a general Exception and specifically StorageError
            assert isinstance(e, StorageError)
            assert "boom" in str(e)

    def test_storage_error_message_preserved(self):
        err = StorageError("disk full")
        assert "disk full" in str(err)


class TestSessionPersistenceError:
    def test_inheritance_chain(self):
        assert issubclass(SessionPersistenceError, StorageError)
        assert issubclass(SessionPersistenceError, Exception)

    def test_message_preserved(self):
        e = SessionPersistenceError("could not persist")
        assert "could not persist" in str(e)


@pytest.fixture
def storage_dir(tmp_path):
    # Default storage directory where parent exists
    """
    Provides a default storage directory path under the pytest `tmp_path`.
    
    Returns:
        pathlib.Path: The path `tmp_path / "store"` to be used as the target storage directory for tests.
    """
    return tmp_path / "store"


@pytest.fixture
def store_instance(storage_dir):
    """
    Create a SessionStore configured to use a fake in-memory TinyDB, preventing creation of real database files during tests.
    
    Parameters:
        storage_dir (pathlib.Path): Directory path to use as the store's storage location.
    
    Returns:
        SessionStore: An instance of SessionStore whose TinyDB dependency is replaced by a fake implementation.
    """
    # Create a simple FakeTinyDB that provides a .table() method
    class FakeTinyDB:
        def __init__(self, path):
            """
            Initialize the store with a storage path and prepare an internal table cache.
            
            Parameters:
                path (str | pathlib.Path): Filesystem path to the storage directory or database file.
            """
            self.path = path
            self._tables = {}

        def table(self, name):
            """
            Return a table-like SimpleNamespace for the given table name, creating and caching a default no-op table if necessary.
            
            Returns:
                SimpleNamespace: An object with default no-op methods `get`, `insert`, `update`, `all`, `search`, and `remove`. Methods can be replaced by tests as needed.
            """
            tbl = self._tables.get(name)
            if not tbl:
                tbl = SimpleNamespace()
                # default no-op methods to be replaced by tests as needed
                tbl.get = lambda *args, **kwargs: None
                tbl.insert = lambda *args, **kwargs: None
                tbl.update = lambda *args, **kwargs: None
                tbl.all = lambda *args, **kwargs: []
                tbl.search = lambda *args, **kwargs: []
                tbl.remove = lambda *args, **kwargs: []
                self._tables[name] = tbl
            return tbl

    with patch("branch_fixer.storage.session_store.TinyDB", side_effect=lambda path: FakeTinyDB(path)):
        store = SessionStore(storage_dir)
    return store


class TestSessionStore:
    def test_init_success_creates_dir_and_sets_db_and_table(self, storage_dir):
        # Use patched TinyDB to avoid file creation
        created = {}

        class FakeTiny:
            def __init__(self, path):
                """
                Initialize the fake TinyDB used by tests.
                
                Records the provided database path for inspection and prepares a single-table stub whose `get` method always returns `None`.
                
                Parameters:
                    path (str | pathlib.Path): The path argument passed to the TinyDB constructor.
                """
                created["path"] = path
                self._table = SimpleNamespace()
                self._table.get = lambda *a, **k: None

            def table(self, name):
                """
                Retrieve a table object for the given table name (fake implementation).
                
                Parameters:
                    name (str): Requested table name; ignored by this fake implementation.
                
                Returns:
                    object: The preconfigured table instance.
                """
                return self._table

        with patch("branch_fixer.storage.session_store.TinyDB", side_effect=lambda path: FakeTiny(path)):
            store = SessionStore(storage_dir)

        # Directory should be created
        assert storage_dir.exists()
        # db attribute should be set to our fake instance (has 'table' method)
        assert hasattr(store, "db")
        assert hasattr(store, "sessions")
        # The stored db path should match
        assert created["path"] == storage_dir / "sessions.json"

    def test_init_raises_value_error_when_parent_missing(self, tmp_path):
        # Choose a storage_dir whose parent does not exist
        storage_dir = tmp_path / "no_parent" / "store"
        # Ensure parent does not exist
        assert not (tmp_path / "no_parent").exists()

        with pytest.raises(ValueError) as excinfo:
            SessionStore(storage_dir)
        assert "Parent directory does not exist" in str(excinfo.value)

    def test_init_raises_permission_error_when_not_writable(self, storage_dir):
        # storage_dir.parent exists (tmp_path), but simulate not writable
        with patch("branch_fixer.storage.session_store.TinyDB", side_effect=lambda path: SimpleNamespace(table=lambda name: SimpleNamespace())):
            with patch("branch_fixer.storage.session_store.os.access", return_value=False):
                with pytest.raises(PermissionError) as excinfo:
                    SessionStore(storage_dir)
        assert "Storage directory not writable" in str(excinfo.value)

    def test_init_propagates_tinydb_errors(self, storage_dir):
        # Patch TinyDB to raise IOError during initialization
        with patch("branch_fixer.storage.session_store.TinyDB", side_effect=IOError("db fail")):
            with pytest.raises(IOError) as excinfo:
                SessionStore(storage_dir)
        assert "db fail" in str(excinfo.value)

    def test_save_session_inserts_when_not_existing(self, store_instance):
        # Prepare a dummy session object
        sid = uuid4()

        class DummyState:
            value = "running"

        class DummyError:
            def __init__(self, name):
                """
                Initialize the instance with a given name.
                
                Parameters:
                    name (str): Identifier assigned to the instance; used as the instance's human-readable name.
                """
                self.name = name

            def to_dict(self):
                """
                Serialize the object into a plain dictionary representation for persistence.
                
                Returns:
                    dict: A mapping with the following keys:
                        - "id" (str): identifier taken from `self.name`.
                        - "test_file" (str): filename of the test (e.g., "f.py").
                        - "test_function" (str): name of the test function (e.g., "t").
                        - "error_details" (dict): contains "error_type" (str) and "message" (str).
                        - "fix_attempts" (list): list of recorded fix attempt entries.
                        - "status" (str): current status string (e.g., "unfixed").
                """
                return {"id": self.name, "test_file": "f.py", "test_function": "t", "error_details": {"error_type": "E", "message": "m"}, "fix_attempts": [], "status": "unfixed"}

        dummy = SimpleNamespace(
            id=sid,
            state=DummyState(),
            start_time=datetime(2020, 1, 1, 12, 0, 0),
            error_count=1,
            retry_count=0,
            git_branch="main",
            modified_files=[Path("a.py"), Path("b.py")],
            errors=[DummyError("err1")],
            completed_errors=[],
            current_error=None,
            total_tests=10,
            passed_tests=5,
            failed_tests=5,
            environment_info={"os": "linux"},
            warnings=["w1"],
        )

        inserted = {}

        class FakeSessions:
            def get(self, *args, **kwargs):
                """
                Act as a table lookup that always indicates no record was found.
                
                Returns:
                    None: Indicates the requested record does not exist.
                """
                return None

            def insert(self, data):
                """
                Insert the provided data into this fake table and return a placeholder insertion id.
                
                Parameters:
                    data: The record to insert.
                
                Returns:
                    int: Placeholder insertion id (always 1).
                """
                inserted["data"] = data
                return 1

            def update(self, *a, **k):
                pytest.fail("update should not be called in insert scenario")

        store_instance.sessions = FakeSessions()
        store_instance.save_session(dummy)

        assert "data" in inserted
        data = inserted["data"]
        assert data["id"] == str(sid)
        assert data["state"] == "running"
        assert data["start_time"] == datetime(2020, 1, 1, 12, 0, 0).isoformat()
        assert data["modified_files"] == ["a.py", "b.py"]
        assert isinstance(data["errors"], list) and data["errors"][0]["id"] == "err1"
        assert data["current_error"] is None
        assert data["environment_info"] == {"os": "linux"}
        assert data["warnings"] == ["w1"]

    def test_save_session_updates_when_existing(self, store_instance):
        sid = uuid4()

        class DummyState:
            value = "paused"

        class DummyError:
            def to_dict(self):
                """
                Serialize this error record into a plain dictionary for storage or transmission.
                
                Returns:
                    dict: A mapping with keys:
                        - `id` (str): Unique identifier for the error record.
                        - `test_file` (str): Path or name of the test file where the error occurred.
                        - `test_function` (str): Name of the test function that failed.
                        - `error_details` (dict): Details about the error with keys:
                            - `error_type` (str): Short code or type of the error.
                            - `message` (str): Human-readable error message.
                        - `fix_attempts` (list): List of attempted fixes (each element is serializable).
                        - `status` (str): Current status of the error (e.g., `"unfixed"`).
                """
                return {"id": "e1", "test_file": "f.py", "test_function": "t", "error_details": {"error_type": "E", "message": "m"}, "fix_attempts": [], "status": "unfixed"}

        dummy = SimpleNamespace(
            id=sid,
            state=DummyState(),
            start_time=datetime.now(),
            error_count=0,
            retry_count=0,
            git_branch=None,
            modified_files=[],
            errors=[DummyError()],
            completed_errors=[],
            current_error=DummyError(),
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            environment_info={},
            warnings=[],
        )

        calls = {"update": 0, "insert": 0}

        class FakeSessions:
            def get(self, *args, **kwargs):
                """
                Return a truthy record dictionary with an 'id' key set to str(sid).
                
                Parameters:
                    *args: Ignored.
                    **kwargs: Ignored.
                
                Returns:
                    dict: A record-like mapping containing `'id'` equal to `str(sid)`.
                """
                return {"id": str(sid)}  # truthy -> trigger update

            def insert(self, *a, **k):
                """
                Record an invocation by incrementing the shared `calls["insert"]` counter.
                """
                calls["insert"] += 1

            def update(self, data, *a, **k):
                calls["update"] += 1
                # verify id included in data
                assert data["id"] == str(sid)

        store_instance.sessions = FakeSessions()
        store_instance.save_session(dummy)

        assert calls["update"] == 1
        assert calls["insert"] == 0

    def test_save_session_raises_SessionPersistenceError_on_db_error(self, store_instance):
        sid = uuid4()

        class DummyState:
            value = "running"

        dummy = SimpleNamespace(
            id=sid,
            state=DummyState(),
            start_time=datetime.now(),
            error_count=0,
            retry_count=0,
            git_branch=None,
            modified_files=[],
            errors=[],
            completed_errors=[],
            current_error=None,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            environment_info={},
            warnings=[],
        )

        class FakeSessions:
            def get(self, *a, **k):
                """
                Always returns None regardless of arguments.
                
                Returns:
                    None: Indicates absence of a value.
                """
                return None

            def insert(self, *a, **k):
                """
                Simulated insert operation that always fails.
                
                Raises:
                    RuntimeError: Always raised with the message "insert boom".
                """
                raise RuntimeError("insert boom")

        store_instance.sessions = FakeSessions()
        with pytest.raises(SessionPersistenceError) as excinfo:
            store_instance.save_session(dummy)
        assert str(sid) in str(excinfo.value)
        assert "insert boom" in str(excinfo.value)

    def test_load_session_returns_none_when_not_found(self, store_instance):
        sid = uuid4()

        class FakeSessions:
            def get(self, *a, **k):
                """
                Always returns None regardless of arguments.
                
                Returns:
                    None: Indicates absence of a value.
                """
                return None

        store_instance.sessions = FakeSessions()
        result = store_instance.load_session(sid)
        assert result is None

    def test_load_session_deserializes_fields_and_returns_fixsession(self, store_instance):
        sid = uuid4()
        iso = datetime(2021, 6, 1, 8, 30, 0).isoformat()
        session_dict = {
            "id": str(sid),
            "state": FixSessionState.RUNNING.value,
            "start_time": iso,
            "error_count": 2,
            "retry_count": 1,
            "git_branch": "dev",
            "modified_files": ["x.py", "y.py"],
            "errors": [{"id": "e1"}],
            "completed_errors": [{"id": "e2"}],
            "current_error": {"id": "e1"},
            "total_tests": 10,
            "passed_tests": 7,
            "failed_tests": 3,
            "environment_info": {"py": "3.9"},
            "warnings": ["w"],
        }

        class FakeSessions:
            def get(self, *a, **k):
                """
                Return the stored session dictionary for any query.
                
                Returns:
                    dict: The stored session record dictionary.
                """
                return session_dict

        # Patch TestError.from_dict to return identifiable objects
        def fake_from_dict(data):
            """
            Create a simple namespace with a `from_id` attribute extracted from the given mapping.
            
            Parameters:
                data (dict): Mapping expected to contain an `"id"` key.
            
            Returns:
                types.SimpleNamespace: Object with a `from_id` attribute equal to `data.get("id")`.
            """
            return SimpleNamespace(from_id=data.get("id"))

        with patch("branch_fixer.storage.session_store.TestError.from_dict", side_effect=fake_from_dict):
            store_instance.sessions = FakeSessions()
            loaded = store_instance.load_session(sid)

        assert loaded is not None
        assert loaded.id == sid
        assert loaded.state == FixSessionState(FixSessionState.RUNNING.value)
        assert loaded.start_time == datetime.fromisoformat(iso)
        assert loaded.error_count == 2
        assert loaded.retry_count == 1
        assert loaded.git_branch == "dev"
        assert all(isinstance(p, Path) for p in loaded.modified_files)
        assert [str(p) for p in loaded.modified_files] == ["x.py", "y.py"]
        assert len(loaded.errors) == 1 and hasattr(loaded.errors[0], "from_id") and loaded.errors[0].from_id == "e1"
        assert len(loaded.completed_errors) == 1 and loaded.completed_errors[0].from_id == "e2"
        assert loaded.current_error.from_id == "e1"
        assert loaded.total_tests == 10
        assert loaded.passed_tests == 7
        assert loaded.failed_tests == 3
        assert loaded.environment_info == {"py": "3.9"}
        assert loaded.warnings == ["w"]

    def test_load_session_raises_SessionPersistenceError_on_deserialization_error(self, store_instance):
        sid = uuid4()
        iso = datetime(2021, 6, 1, 8, 30, 0).isoformat()
        session_dict = {
            "id": str(sid),
            "state": FixSessionState.RUNNING.value,
            "start_time": iso,
            "errors": [{"id": "e1"}],
        }

        class FakeSessions:
            def get(self, *a, **k):
                """
                Return the stored session dictionary for any query.
                
                Returns:
                    dict: The stored session record dictionary.
                """
                return session_dict

        # Make TestError.from_dict raise
        with patch("branch_fixer.storage.session_store.TestError.from_dict", side_effect=ValueError("bad")):
            store_instance.sessions = FakeSessions()
            with pytest.raises(SessionPersistenceError) as excinfo:
                store_instance.load_session(sid)
        assert "bad" in str(excinfo.value)

    def test_load_session_handles_missing_optional_fields(self, store_instance):
        sid = uuid4()
        iso = datetime(2022, 1, 1, 0, 0, 0).isoformat()
        minimal = {"id": str(sid), "state": FixSessionState.INITIALIZING.value, "start_time": iso}

        class FakeSessions:
            def get(self, *a, **k):
                """
                Retrieve the stored minimal value.
                
                Returns:
                    The value referred to as `minimal`.
                """
                return minimal

        store_instance.sessions = FakeSessions()
        loaded = store_instance.load_session(sid)
        assert loaded is not None
        assert loaded.error_count == 0
        assert loaded.modified_files == []
        assert loaded.errors == []
        assert loaded.completed_errors == []
        assert loaded.current_error is None
        assert loaded.environment_info == {}
        assert loaded.warnings == []

    def test_list_sessions_returns_empty_list_when_no_records(self, store_instance):
        class FakeSessions:
            def all(self):
                """
                Provide the list of all stored session records (currently returns an empty list).
                
                Returns:
                    list: An empty list.
                """
                return []

        store_instance.sessions = FakeSessions()
        res = store_instance.list_sessions()
        assert res == []

    def test_list_sessions_returns_deserialized_fixsessions_for_all(self, store_instance):
        sid = uuid4()
        iso = datetime(2021, 12, 12, 12, 12, 12).isoformat()
        data = [{
            "id": str(sid),
            "state": FixSessionState.RUNNING.value,
            "start_time": iso,
            "modified_files": ["m.py"],
            "errors": [{"id": "e1"}],
            "completed_errors": [],
            "current_error": None,
            "retry_count": 0,
            "error_count": 1,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "environment_info": {},
            "warnings": [],
        }]

        class FakeSessions:
            def all(self):
                """
                Return all records currently stored in the table.
                
                Returns:
                    list: A list of stored record objects (each typically a dict) in their raw form.
                """
                return data

        def fake_from_dict(d):
            """
            Create a SimpleNamespace with an `id` attribute extracted from a mapping.
            
            Parameters:
                d (Mapping): Mapping containing an `"id"` key.
            
            Returns:
                SimpleNamespace: Object whose `id` attribute is set to d.get("id") (or `None` if the key is missing).
            """
            return SimpleNamespace(id=d.get("id"))

        with patch("branch_fixer.storage.session_store.TestError.from_dict", side_effect=fake_from_dict):
            store_instance.sessions = FakeSessions()
            out = store_instance.list_sessions()

        assert isinstance(out, list)
        assert len(out) == 1
        s = out[0]
        assert s.id == UUID(str(sid))
        assert s.state == FixSessionState(FixSessionState.RUNNING.value)
        assert all(isinstance(p, Path) for p in s.modified_files)
        assert [str(p) for p in s.modified_files] == ["m.py"]
        assert len(s.errors) == 1 and hasattr(s.errors[0], "id")

    def test_list_sessions_filters_by_status(self, store_instance):
        sid = uuid4()
        iso = datetime.now().isoformat()
        data = [{
            "id": str(sid),
            "state": FixSessionState.COMPLETED.value,
            "start_time": iso,
            "modified_files": [],
            "errors": [],
            "completed_errors": [],
            "current_error": None,
            "retry_count": 0,
            "error_count": 0,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "environment_info": {},
            "warnings": [],
        }]

        called = {"search": 0}

        class FakeSessions:
            def search(self, *a, **k):
                """
                Increment the search invocation counter and return the stored data.
                
                Parameters:
                    *a: Ignored positional arguments kept for signature compatibility.
                    **k: Ignored keyword arguments kept for signature compatibility.
                
                Returns:
                    list: The stored records (as returned from the underlying `data` variable).
                """
                called["search"] += 1
                return data

        with patch("branch_fixer.storage.session_store.TestError.from_dict", side_effect=lambda d: SimpleNamespace()):
            store_instance.sessions = FakeSessions()
            res = store_instance.list_sessions(status=FixSessionState.COMPLETED)

        assert called["search"] == 1
        assert len(res) == 1
        assert res[0].state == FixSessionState(FixSessionState.COMPLETED.value)

    def test_list_sessions_raises_SessionPersistenceError_on_db_error(self, store_instance):
        class FakeSessions:
            def all(self):
                """
                Simulate a failing retrieval of all records by always raising a runtime error.
                
                Raises:
                    RuntimeError: Always raised with message "boom".
                """
                raise RuntimeError("boom")

        store_instance.sessions = FakeSessions()
        with pytest.raises(SessionPersistenceError) as excinfo:
            store_instance.list_sessions()
        assert "boom" in str(excinfo.value)

    @pytest.mark.parametrize("removed,expected", [([1], True), ([], False)])
    def test_delete_session_returns_expected_based_on_removed_list(self, store_instance, removed, expected):
        sid = uuid4()

        class FakeSessions:
            def remove(self, *a, **k):
                """
                Remove records matching the provided query and return the identifiers of removed records.
                
                Returns:
                    list: Identifiers for the records that were removed; an empty list if no records were removed.
                """
                return removed

        store_instance.sessions = FakeSessions()
        result = store_instance.delete_session(sid)
        assert result is expected

    def test_delete_session_raises_SessionPersistenceError_on_db_error(self, store_instance):
        sid = uuid4()

        class FakeSessions:
            def remove(self, *a, **k):
                """
                Simulates a failing delete operation by always raising RuntimeError("boom delete").
                
                Raises:
                    RuntimeError: Always raised with message "boom delete".
                """
                raise RuntimeError("boom delete")

        store_instance.sessions = FakeSessions()
        with pytest.raises(SessionPersistenceError) as excinfo:
            store_instance.delete_session(sid)
        assert "boom delete" in str(excinfo.value)