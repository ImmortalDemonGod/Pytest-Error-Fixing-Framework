"""
Variant selection logic — pure domain layer, no I/O.

Determines which GenerationVariant(s) should be applied to each TestableEntity
based on its name and type.  Faithfully mirrors the logic in
scripts/hypot_test_gen.py (generate_test_variants / generate_method_variants /
generate_function_variants / _generate_special_variants).

Key behavioural contract (matches original exactly):
- Class            → [DEFAULT]
- Method / Instance method → [DEFAULT, ERRORS] + all matching specials
  (specials can stack: a method named transform_encode gets both IDEMPOTENT and
  ROUNDTRIP appended)
- Function         → [DEFAULT] + only ROUNDTRIP or BINARY_OP (first match,
  no IDEMPOTENT or ERRORS_EQUIVALENT for functions)
"""

from typing import List

from src.dev.test_generator.core.models import GenerationVariant, TestableEntity

# ---------------------------------------------------------------------------
# Name-pattern → variant mappings
# ---------------------------------------------------------------------------

_ROUNDTRIP_PATTERNS = ("encode", "decode", "serialize", "deserialize")
_IDEMPOTENT_PATTERNS = ("transform", "convert", "process", "format")
_ERRORS_EQUIV_PATTERNS = ("validate", "verify", "check", "assert")
_BINARY_OP_PATTERNS = ("add", "subtract", "multiply", "combine", "merge", "sub", "mul")


def select_variants(entity: TestableEntity) -> List[GenerationVariant]:
    """Return the ordered list of variants to attempt for *entity*."""
    if entity.entity_type == "class":
        return [GenerationVariant.DEFAULT]
    if entity.entity_type in ("method", "instance_method"):
        return _method_variants(entity)
    return _function_variants(entity)


def _method_variants(entity: TestableEntity) -> List[GenerationVariant]:
    """Methods always get DEFAULT + ERRORS; all four specials can stack."""
    variants: List[GenerationVariant] = [
        GenerationVariant.DEFAULT,
        GenerationVariant.ERRORS,
    ]
    name = entity.name.lower()
    # All four checks are independent — multiple specials can accumulate
    if any(p in name for p in _IDEMPOTENT_PATTERNS):
        variants.append(GenerationVariant.IDEMPOTENT)
    if any(p in name for p in _ERRORS_EQUIV_PATTERNS):
        variants.append(GenerationVariant.ERRORS_EQUIVALENT)
    if any(p in name for p in _ROUNDTRIP_PATTERNS):
        variants.append(GenerationVariant.ROUNDTRIP)
    if any(p in name for p in _BINARY_OP_PATTERNS):
        variants.append(GenerationVariant.BINARY_OP)
    return variants


def _function_variants(entity: TestableEntity) -> List[GenerationVariant]:
    """Functions get DEFAULT + only ROUNDTRIP or BINARY_OP (first match)."""
    variants: List[GenerationVariant] = [GenerationVariant.DEFAULT]
    name = entity.name.lower()
    if any(p in name for p in _ROUNDTRIP_PATTERNS):
        variants.append(GenerationVariant.ROUNDTRIP)
    elif any(p in name for p in _BINARY_OP_PATTERNS):
        variants.append(GenerationVariant.BINARY_OP)
    return variants
