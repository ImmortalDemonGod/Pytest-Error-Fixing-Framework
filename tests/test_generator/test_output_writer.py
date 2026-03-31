"""Unit tests for src/dev/test_generator/output/writer.py"""

import pytest
from pathlib import Path

from src.dev.test_generator.core.models import GenerationAttempt, GenerationVariant, TestableEntity
from src.dev.test_generator.output.writer import output_filename, write_attempt


def _entity(name: str, entity_type: str = "function", parent: str = None) -> TestableEntity:
    return TestableEntity(
        name=name, module_path="pkg.mod", entity_type=entity_type, parent_class=parent
    )


def _success_attempt(entity: TestableEntity, variant: GenerationVariant, code: str) -> GenerationAttempt:
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
