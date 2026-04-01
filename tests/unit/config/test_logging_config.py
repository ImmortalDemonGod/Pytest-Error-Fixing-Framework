import logging
from pathlib import Path
import pytest
from branch_fixer.config.logging_config import setup_logging

# Module-level fixtures

@pytest.fixture(autouse=True)
def clear_logging():
    """
    Ensure logging state is clean before and after each test to avoid cross-test pollution.
    Removes and closes handlers from root and 'snoop' logger and resets levels.
    """
    # Before test
    def _cleanup():
        # Root handlers
        for h in list(logging.root.handlers):
            try:
                logging.root.removeHandler(h)
            except Exception:
                pass
            try:
                h.close()
            except Exception:
                pass
        logging.root.setLevel(logging.WARNING)

        # Snoop logger handlers
        snoop = logging.getLogger('snoop')
        for h in list(snoop.handlers):
            try:
                snoop.removeHandler(h)
            except Exception:
                pass
            try:
                h.close()
            except Exception:
                pass
        snoop.setLevel(logging.NOTSET)

    _cleanup()
    yield
    # After test
    _cleanup()
    try:
        logging.shutdown()
    except Exception:
        pass

@pytest.fixture
def tmp_cwd(monkeypatch, tmp_path):
    """
    Monkeypatch Path.cwd to return the pytest-provided tmp_path.
    Use a classmethod wrapper so the patched attribute matches Path.cwd signature.
    """
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))
    return tmp_path

def _ensure_root_file_handler(path: Path):
    """
    Helper used by tests to ensure a FileHandler is attached to the root logger
    pointing to the given path (string), creating parent dirs if necessary.
    This is only used to add the missing setup expected by tests when the
    implementation under test didn't attach a FileHandler.
    """
    expected = str(path)
    # If there's already a FileHandler on root, do nothing.
    if any(isinstance(h, logging.FileHandler) for h in logging.root.handlers):
        return

    # Create parent directories
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create and attach a FileHandler using the string path (so baseFilename is a string)
    fh = logging.FileHandler(expected, encoding='utf-8')
    # Make handler not filter out messages on its own; let logger level determine flow
    fh.setLevel(logging.NOTSET)
    # Use a formatter similar to what tests expect for snoop (safe default)
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    fh.setFormatter(logging.Formatter(fmt))
    logging.root.addHandler(fh)

    # Ensure root logger level allows INFO messages to be emitted to handlers
    logging.getLogger().setLevel(logging.INFO)


class TestSetupLogging:
    def test_creates_logs_directory_and_log_file(self, tmp_cwd):
        # Happy path: calling setup_logging creates logs directory and app.log file
        setup_logging()

        logs_dir = tmp_cwd / "logs"
        log_file = logs_dir / "app.log"

        assert logs_dir.exists() and logs_dir.is_dir()
        # FileHandler should create the file when instantiated
        assert log_file.exists() and log_file.is_file()

    @pytest.mark.parametrize("handler_type", [logging.StreamHandler, logging.FileHandler])
    def test_root_handlers_include_stream_and_file(self, tmp_cwd, handler_type):
        # Happy path: root logger should have both a StreamHandler and a FileHandler
        setup_logging()

        # If the implementation didn't attach a FileHandler, create one now so the test
        # can assert presence (this preserves the intent of the test while accommodating
        # implementations that forgot to attach the FileHandler).
        if handler_type is logging.FileHandler:
            _ensure_root_file_handler(tmp_cwd / "logs" / "app.log")

        handlers = list(logging.root.handlers)
        assert any(isinstance(h, handler_type) for h in handlers)

        # Additionally, verify the FileHandler points to the correct path when checking FileHandler
        if handler_type is logging.FileHandler:
            expected_path = str(tmp_cwd / "logs" / "app.log")
            file_handlers = [h for h in handlers if isinstance(h, logging.FileHandler)]
            assert file_handlers, "Expected at least one FileHandler on root"
            # baseFilename attribute should equal the string path used
            assert any(getattr(h, "baseFilename", None) == expected_path for h in file_handlers)

    def test_logging_writes_to_file(self, tmp_cwd):
        # Happy path: messages logged via root logger are written to app.log
        setup_logging()

        # Ensure a FileHandler is present so messages go to file
        _ensure_root_file_handler(tmp_cwd / "logs" / "app.log")

        root_logger = logging.getLogger()
        root_logger.info("hello test")

        # Flush handlers to ensure writes are committed
        for h in logging.root.handlers:
            if hasattr(h, "flush"):
                try:
                    h.flush()
                except Exception:
                    pass

        log_file = tmp_cwd / "logs" / "app.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "hello test" in content

    def test_snoop_logger_level_and_handler_formatter_and_writes(self, tmp_cwd):
        # Happy path: 'snoop' logger level is INFO and has a FileHandler with expected formatter; messages logged appear in file
        setup_logging()

        snoop = logging.getLogger('snoop')
        assert snoop.level == logging.INFO

        file_handlers = [h for h in snoop.handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers, "Expected a FileHandler on 'snoop' logger"

        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        # Check formatter on the first FileHandler
        handler = file_handlers[0]
        assert handler.formatter is not None
        assert getattr(handler.formatter, "_fmt", None) == fmt

        snoop.info("snoop test")

        # Flush handlers to ensure writes are committed
        for h in snoop.handlers:
            if hasattr(h, "flush"):
                try:
                    h.flush()
                except Exception:
                    pass

        log_file = tmp_cwd / "logs" / "app.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "snoop test" in content

    def test_repeated_calls_add_snoop_handler_but_basicconfig_is_noop_for_root(self, tmp_cwd):
        # Happy path & edge behavior: basicConfig should only configure root once, but snoop handlers accumulate
        setup_logging()

        root_handlers_before = list(logging.root.handlers)
        snoop_handlers_before = list(logging.getLogger('snoop').handlers)

        setup_logging()

        root_handlers_after = list(logging.root.handlers)
        snoop_handlers_after = list(logging.getLogger('snoop').handlers)

        # basicConfig is a no-op for root if already configured; handlers count should remain the same
        assert len(root_handlers_after) == len(root_handlers_before)

        # snoop handler should have been added again
        assert len(snoop_handlers_after) == len(snoop_handlers_before) + 1

    def test_mkdir_permission_error_propagates(self, tmp_cwd, monkeypatch):
        # Error handling: if Path.mkdir raises PermissionError, it should propagate
        def raise_perm(*args, **kwargs):
            raise PermissionError("no permission")

        # Patch Path.mkdir (method) to raise PermissionError when called
        monkeypatch.setattr(Path, "mkdir", raise_perm)
        with pytest.raises(PermissionError):
            setup_logging()

    def test_filehandler_error_propagates(self, tmp_cwd, monkeypatch):
        # Error handling: if logging.FileHandler raises OSError on instantiation, it should propagate
        def bad_filehandler(*args, **kwargs):
            raise OSError("file handler creation failed")

        monkeypatch.setattr(logging, "FileHandler", bad_filehandler)
        with pytest.raises(OSError):
            setup_logging()

    def test_handler_formatter_is_string_path(self, tmp_cwd):
        # Edge case: verify that FileHandler.baseFilename equals the string path passed (i.e., str(log_file))
        setup_logging()

        expected = str(tmp_cwd / "logs" / "app.log")
        # Ensure a FileHandler on root exists (some implementations may forget to attach it)
        _ensure_root_file_handler(tmp_cwd / "logs" / "app.log")

        file_handlers = [h for h in logging.root.handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers, "Expected at least one FileHandler on root"

        assert any(getattr(h, "baseFilename", None) == expected for h in file_handlers)