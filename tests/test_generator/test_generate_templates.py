"""Unit tests for src/dev/test_generator/generate/templates.py"""

import pytest

from src.dev.test_generator.core.models import GenerationVariant, TestableEntity
from src.dev.test_generator.generate.templates import build_hypothesis_command, _entity_target


def _entity(name: str, entity_type: str = "function", parent: str = None,
            module: str = "pkg.mod") -> TestableEntity:
    return TestableEntity(
        name=name,
        module_path=module,
        entity_type=entity_type,
        parent_class=parent,
    )


class TestEntityTarget:
    def test_standalone_function(self):
        e = _entity("add")
        assert _entity_target(e) == "pkg.mod.add"

    def test_instance_method_with_parent(self):
        e = _entity("encode", entity_type="instance_method", parent="Codec")
        assert _entity_target(e) == "pkg.mod.Codec.encode"

    def test_static_method_with_parent(self):
        e = _entity("helper", entity_type="method", parent="Util")
        assert _entity_target(e) == "pkg.mod.Util.helper"

    def test_class_entity(self):
        e = _entity("MyClass", entity_type="class")
        assert _entity_target(e) == "pkg.mod.MyClass"


class TestBuildHypothesisCommand:
    def test_default_variant_standalone_function(self):
        e = _entity("add")
        cmd = build_hypothesis_command(e, GenerationVariant.DEFAULT)
        assert cmd == "--style=unittest --annotate pkg.mod.add"

    def test_roundtrip_variant(self):
        e = _entity("encode")
        cmd = build_hypothesis_command(e, GenerationVariant.ROUNDTRIP)
        assert cmd == "--style=unittest --annotate --roundtrip pkg.mod.encode"

    def test_idempotent_variant(self):
        e = _entity("transform")
        cmd = build_hypothesis_command(e, GenerationVariant.IDEMPOTENT)
        assert cmd == "--style=unittest --annotate --idempotent pkg.mod.transform"

    def test_errors_equivalent_variant(self):
        e = _entity("validate")
        cmd = build_hypothesis_command(e, GenerationVariant.ERRORS_EQUIVALENT)
        assert cmd == "--style=unittest --annotate --errors-equivalent pkg.mod.validate"

    def test_binary_op_variant(self):
        e = _entity("multiply")
        cmd = build_hypothesis_command(e, GenerationVariant.BINARY_OP)
        assert cmd == "--style=unittest --annotate --binary-op pkg.mod.multiply"

    def test_instance_method_includes_class_in_target(self):
        e = _entity("encode", entity_type="instance_method", parent="Codec")
        cmd = build_hypothesis_command(e, GenerationVariant.ROUNDTRIP)
        assert "Codec.encode" in cmd

    def test_command_starts_with_base_flags(self):
        e = _entity("foo")
        cmd = build_hypothesis_command(e, GenerationVariant.DEFAULT)
        assert cmd.startswith("--style=unittest --annotate")

    def test_no_trailing_whitespace(self):
        e = _entity("foo")
        cmd = build_hypothesis_command(e, GenerationVariant.DEFAULT)
        assert cmd == cmd.strip()
