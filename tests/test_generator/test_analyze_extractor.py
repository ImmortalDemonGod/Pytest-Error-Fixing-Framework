"""Unit tests for src/dev/test_generator/analyze/extractor.py"""

import pytest

from src.dev.test_generator.analyze.extractor import select_variants, _special_variant_for_name
from src.dev.test_generator.core.models import GenerationVariant, TestableEntity


def _entity(name: str, entity_type: str = "function", parent: str = None) -> TestableEntity:
    return TestableEntity(
        name=name,
        module_path="pkg.mod",
        entity_type=entity_type,
        parent_class=parent,
    )


class TestSelectVariantsForClasses:
    def test_class_returns_only_default(self):
        e = _entity("MyClass", entity_type="class")
        assert select_variants(e) == [GenerationVariant.DEFAULT]

    def test_class_name_matching_patterns_still_default_only(self):
        # Even if a class is named 'Encoder' we don't add roundtrip for classes
        e = _entity("Encoder", entity_type="class")
        assert select_variants(e) == [GenerationVariant.DEFAULT]


class TestSelectVariantsForFunctions:
    def test_plain_function_returns_default_only(self):
        e = _entity("compute")
        assert select_variants(e) == [GenerationVariant.DEFAULT]

    def test_encode_function_gets_roundtrip(self):
        variants = select_variants(_entity("encode_payload"))
        assert GenerationVariant.ROUNDTRIP in variants
        assert variants[0] == GenerationVariant.DEFAULT

    def test_decode_function_gets_roundtrip(self):
        variants = select_variants(_entity("decode"))
        assert GenerationVariant.ROUNDTRIP in variants

    def test_serialize_gets_roundtrip(self):
        assert GenerationVariant.ROUNDTRIP in select_variants(_entity("serialize"))

    def test_deserialize_gets_roundtrip(self):
        assert GenerationVariant.ROUNDTRIP in select_variants(_entity("deserialize_json"))

    def test_transform_gets_idempotent(self):
        assert GenerationVariant.IDEMPOTENT in select_variants(_entity("transform_data"))

    def test_convert_gets_idempotent(self):
        assert GenerationVariant.IDEMPOTENT in select_variants(_entity("convert"))

    def test_validate_gets_errors_equivalent(self):
        assert GenerationVariant.ERRORS_EQUIVALENT in select_variants(_entity("validate_input"))

    def test_verify_gets_errors_equivalent(self):
        assert GenerationVariant.ERRORS_EQUIVALENT in select_variants(_entity("verify"))

    def test_check_gets_errors_equivalent(self):
        assert GenerationVariant.ERRORS_EQUIVALENT in select_variants(_entity("check_schema"))

    def test_add_gets_binary_op(self):
        assert GenerationVariant.BINARY_OP in select_variants(_entity("add"))

    def test_multiply_gets_binary_op(self):
        assert GenerationVariant.BINARY_OP in select_variants(_entity("multiply"))

    def test_combine_gets_binary_op(self):
        assert GenerationVariant.BINARY_OP in select_variants(_entity("combine_lists"))

    def test_only_one_special_variant_appended(self):
        # 'encode' matches roundtrip — should not also match idempotent
        variants = select_variants(_entity("encode"))
        special = [v for v in variants if v != GenerationVariant.DEFAULT]
        assert len(special) == 1

    def test_default_is_always_first(self):
        for name in ("encode", "transform", "validate", "add", "greet"):
            variants = select_variants(_entity(name))
            assert variants[0] == GenerationVariant.DEFAULT


class TestSelectVariantsForMethods:
    def test_instance_method_same_logic_as_function(self):
        e = _entity("encode", entity_type="instance_method", parent="Codec")
        assert GenerationVariant.ROUNDTRIP in select_variants(e)

    def test_static_method_same_logic(self):
        e = _entity("add", entity_type="method", parent="Math")
        assert GenerationVariant.BINARY_OP in select_variants(e)


class TestSpecialVariantForName:
    def test_no_match_returns_none(self):
        assert _special_variant_for_name("compute") is None

    def test_roundtrip_priority_over_others(self):
        # A name containing both 'encode' and 'add': roundtrip wins (checked first)
        result = _special_variant_for_name("encode_and_add")
        assert result == GenerationVariant.ROUNDTRIP
