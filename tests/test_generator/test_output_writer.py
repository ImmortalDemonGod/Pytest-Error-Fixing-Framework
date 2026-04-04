"""Unit tests for src/dev/test_generator/output/writer.py"""

import pytest
from pathlib import Path

from src.dev.test_generator.core.models import GenerationAttempt, GenerationVariant, TestableEntity
from src.dev.test_generator.output.writer import output_filename, write_attempt, write_module_test


def _entity(name: str, entity_type: str = "function", parent: str = None) -> TestableEntity:
    """
    Create a TestableEntity preconfigured for tests with a fixed module path.
    
    Parameters:
        name (str): The entity's name.
        entity_type (str): The kind of entity (e.g., "function", "instance_method").
        parent (str | None): The parent class name for methods, or None for top-level entities.
    
    Returns:
        TestableEntity: An entity with the provided attributes and module_path set to "pkg.mod".
    """
    return TestableEntity(
        name=name, module_path="pkg.mod", entity_type=entity_type, parent_class=parent
    )


def _success_attempt(entity: TestableEntity, variant: GenerationVariant, code: str) -> GenerationAttempt:
    """
    Create a GenerationAttempt for the given entity and variant that is marked successful with the provided code.
    
    Parameters:
        entity (TestableEntity): The entity the attempt targets.
        variant (GenerationVariant): The generation variant for the attempt.
        code (str): The generated test code to store in the attempt.
    
    Returns:
        GenerationAttempt: A GenerationAttempt in the success state containing `code`.
    """
    a = GenerationAttempt(entity=entity, variant=variant)
    a.mark_success(code)
    return a


class TestOutputFilename:
    def test_standalone_function(self):
        e = _entity("add")
        assert output_filename(e, "default") == "test_add_default.py"

    def test_method_with_parent(self):
        e = _entity("encode", entity_type="instance_method", parent="Codec")
        assert output_filename(e, "roundtrip") == "test_Codec_encode_roundtrip.py"

    def test_ends_with_py(self):
        e = _entity("foo")
        assert output_filename(e, "binary_op").endswith(".py")


class TestWriteAttempt:
    def test_writes_file_to_output_dir(self, tmp_path):
        e = _entity("add")
        attempt = _success_attempt(e, GenerationVariant.DEFAULT, "def test_add(): pass\n")
        out = write_attempt(attempt, tmp_path)
        assert out.exists()
        assert out.read_text() == "def test_add(): pass\n"

    def test_returns_correct_path(self, tmp_path):
        e = _entity("add")
        attempt = _success_attempt(e, GenerationVariant.DEFAULT, "code")
        out = write_attempt(attempt, tmp_path)
        assert out.parent == tmp_path
        assert out.name == "test_add_default.py"

    def test_raises_if_attempt_not_success(self, tmp_path):
        e = _entity("foo")
        attempt = GenerationAttempt(entity=e, variant=GenerationVariant.DEFAULT)
        with pytest.raises(ValueError, match="not in success state"):
            write_attempt(attempt, tmp_path)

    def test_raises_if_attempt_failed(self, tmp_path):
        e = _entity("foo")
        attempt = GenerationAttempt(entity=e, variant=GenerationVariant.DEFAULT)
        attempt.mark_failed("oops")
        with pytest.raises(ValueError, match="not in success state"):
            write_attempt(attempt, tmp_path)


class TestWriteModuleTest:
    def test_writes_file_named_test_stem(self, tmp_path):
        code = "import pytest\n" + "x = 1\n" * 10
        out = write_module_test(code, "change_applier", tmp_path)
        assert out.name == "test_change_applier.py"
        assert out.exists()

    def test_content_round_trips(self, tmp_path):
        code = "import pytest\n" + "x = 1\n" * 10
        write_module_test(code, "mymod", tmp_path)
        assert (tmp_path / "test_mymod.py").read_text() == code

    def test_returns_path(self, tmp_path):
        code = "import pytest\n" + "x = 1\n" * 10
        out = write_module_test(code, "mymod", tmp_path)
        assert isinstance(out, Path)
        assert out == tmp_path / "test_mymod.py"

    def test_raises_runtime_error_if_empty_write(self, tmp_path, monkeypatch):
        # Simulate read_text returning empty after write
        monkeypatch.setattr(Path, "read_text", lambda self, **kw: "")
        with pytest.raises(RuntimeError, match="empty after writing"):
            write_module_test("import pytest\n" + "x = 1\n" * 10, "mod", tmp_path)

    def test_raises_runtime_error_on_content_mismatch(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "read_text", lambda self, **kw: "different content")
        with pytest.raises(RuntimeError, match="Content mismatch"):
            write_module_test("import pytest\n" + "x = 1\n" * 10, "mod", tmp_path)
