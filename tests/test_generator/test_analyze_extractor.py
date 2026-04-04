"""Unit tests for src/dev/test_generator/analyze/extractor.py

Tests match the original scripts/hypot_test_gen.py contract exactly:
- Classes      → [DEFAULT]
- Methods      → [DEFAULT, ERRORS] + all matching specials (can stack)
- Functions    → [DEFAULT] + only ROUNDTRIP or BINARY_OP (first match)
"""

import pytest

from src.dev.test_generator.analyze.extractor import (
    _function_variants,
    _method_variants,
    select_variants,
)
from src.dev.test_generator.core.models import GenerationVariant, TestableEntity


def _entity(name: str, entity_type: str = "function", parent: str = None) -> TestableEntity:
    """
    Create a TestableEntity with a fixed module path ("pkg.mod") for use in tests.
    
    Parameters:
        name (str): The entity's name.
        entity_type (str): The kind of entity (e.g., "function", "method", "class"). Defaults to "function".
        parent (str | None): Optional parent class name for methods; omitted for non-method entities.
    
    Returns:
        TestableEntity: An instance with the given name, entity_type, parent_class set to `parent`, and module_path set to "pkg.mod".
    """
    return TestableEntity(
        name=name, module_path="pkg.mod", entity_type=entity_type, parent_class=parent
    )


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class TestClasses:
    def test_class_returns_only_default(self):
        assert select_variants(_entity("MyClass", "class")) == [GenerationVariant.DEFAULT]

    def test_class_named_like_encoder_still_only_default(self):
        assert select_variants(_entity("Encoder", "class")) == [GenerationVariant.DEFAULT]


# ---------------------------------------------------------------------------
# Functions — only ROUNDTRIP or BINARY_OP, no IDEMPOTENT/ERRORS_EQUIVALENT
# ---------------------------------------------------------------------------

class TestFunctions:
    def test_plain_function_default_only(self):
        assert select_variants(_entity("compute")) == [GenerationVariant.DEFAULT]

    def test_encode_gets_roundtrip(self):
        v = select_variants(_entity("encode_payload"))
        assert GenerationVariant.ROUNDTRIP in v
        assert v[0] == GenerationVariant.DEFAULT

    def test_decode_gets_roundtrip(self):
        assert GenerationVariant.ROUNDTRIP in select_variants(_entity("decode"))

    def test_serialize_gets_roundtrip(self):
        assert GenerationVariant.ROUNDTRIP in select_variants(_entity("serialize"))

    def test_deserialize_gets_roundtrip(self):
        assert GenerationVariant.ROUNDTRIP in select_variants(_entity("deserialize_json"))

    def test_add_gets_binary_op(self):
        assert GenerationVariant.BINARY_OP in select_variants(_entity("add"))

    def test_multiply_gets_binary_op(self):
        assert GenerationVariant.BINARY_OP in select_variants(_entity("multiply"))

    def test_combine_gets_binary_op(self):
        assert GenerationVariant.BINARY_OP in select_variants(_entity("combine_lists"))

    def test_transform_does_NOT_get_idempotent_for_functions(self):
        # Original: IDEMPOTENT only added for methods, not functions
        v = select_variants(_entity("transform_data"))
        assert GenerationVariant.IDEMPOTENT not in v

    def test_validate_does_NOT_get_errors_equivalent_for_functions(self):
        v = select_variants(_entity("validate_input"))
        assert GenerationVariant.ERRORS_EQUIVALENT not in v

    def test_only_one_special_for_functions(self):
        # encode_and_add: roundtrip patterns checked first → only ROUNDTRIP
        v = select_variants(_entity("encode_and_add"))
        specials = [x for x in v if x not in (GenerationVariant.DEFAULT,)]
        assert len(specials) == 1
        assert specials[0] == GenerationVariant.ROUNDTRIP

    def test_no_errors_variant_for_functions(self):
        v = select_variants(_entity("compute"))
        assert GenerationVariant.ERRORS not in v


# ---------------------------------------------------------------------------
# Methods — always DEFAULT + ERRORS; all four specials can stack
# ---------------------------------------------------------------------------

class TestMethods:
    def test_plain_method_gets_default_and_errors(self):
        e = _entity("compute", "instance_method", "MyClass")
        v = select_variants(e)
        assert GenerationVariant.DEFAULT in v
        assert GenerationVariant.ERRORS in v

    def test_default_always_first(self):
        e = _entity("encode", "instance_method", "Codec")
        assert select_variants(e)[0] == GenerationVariant.DEFAULT

    def test_errors_always_second(self):
        e = _entity("compute", "instance_method", "MyClass")
        assert select_variants(e)[1] == GenerationVariant.ERRORS

    def test_encode_method_gets_roundtrip(self):
        e = _entity("encode", "instance_method", "Codec")
        assert GenerationVariant.ROUNDTRIP in select_variants(e)

    def test_transform_method_gets_idempotent(self):
        e = _entity("transform_data", "instance_method", "Proc")
        assert GenerationVariant.IDEMPOTENT in select_variants(e)

    def test_validate_method_gets_errors_equivalent(self):
        e = _entity("validate", "instance_method", "Form")
        assert GenerationVariant.ERRORS_EQUIVALENT in select_variants(e)

    def test_add_method_gets_binary_op(self):
        e = _entity("add", "method", "Math")
        assert GenerationVariant.BINARY_OP in select_variants(e)

    def test_specials_can_stack_on_method(self):
        # transform_encode matches both IDEMPOTENT and ROUNDTRIP
        e = _entity("transform_encode", "instance_method", "Proc")
        v = select_variants(e)
        assert GenerationVariant.IDEMPOTENT in v
        assert GenerationVariant.ROUNDTRIP in v

    def test_all_four_specials_stack(self):
        # Name matching all four patterns
        e = _entity("transform_encode_validate_add", "instance_method", "X")
        v = select_variants(e)
        assert GenerationVariant.IDEMPOTENT in v
        assert GenerationVariant.ERRORS_EQUIVALENT in v
        assert GenerationVariant.ROUNDTRIP in v
        assert GenerationVariant.BINARY_OP in v

    def test_static_method_same_logic_as_instance_method(self):
        e = _entity("add", "method", "Math")
        v = select_variants(e)
        assert GenerationVariant.ERRORS in v
        assert GenerationVariant.BINARY_OP in v


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestMethodVariants:
    def test_always_includes_default_and_errors(self):
        e = _entity("foo", "instance_method", "X")
        v = _method_variants(e)
        assert v[:2] == [GenerationVariant.DEFAULT, GenerationVariant.ERRORS]


class TestFunctionVariants:
    def test_never_includes_errors(self):
        e = _entity("foo")
        assert GenerationVariant.ERRORS not in _function_variants(e)

    def test_never_includes_idempotent(self):
        e = _entity("transform")
        assert GenerationVariant.IDEMPOTENT not in _function_variants(e)
