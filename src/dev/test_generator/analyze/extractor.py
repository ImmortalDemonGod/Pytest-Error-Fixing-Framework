"""
Variant selection logic — pure domain layer, no I/O.

Determines which GenerationVariant(s) should be applied to each TestableEntity
based on its name and type.  Extracted from the variant-selection methods in
scripts/hypot_test_gen.py (generate_test_variants / _generate_special_variants).
"""

from typing import List, Optional

from src.dev.test_generator.core.models import GenerationVariant, TestableEntity

# ---------------------------------------------------------------------------
# Name-pattern → variant mappings
# ---------------------------------------------------------------------------

_ROUNDTRIP_PATTERNS = ("encode", "decode", "serialize", "deserialize")
_IDEMPOTENT_PATTERNS = ("transform", "convert", "process", "format")
_ERRORS_EQUIV_PATTERNS = ("validate", "verify", "check", "assert")
_BINARY_OP_PATTERNS = ("add", "subtract", "multiply", "combine", "merge", "sub", "mul")


def select_variants(entity: TestableEntity) -> List[GenerationVariant]:
    """Return the ordered list of variants to try for *entity*.

    Rules:
    - Class      → [DEFAULT]
    - Function / Method / InstanceMethod → always [DEFAULT], plus any
      name-matched special variant appended at the end.

    The DEFAULT variant maps to a plain ``hypothesis write`` call.  Special
    variants correspond to ``--roundtrip``, ``--idempotent``, etc. flags.
    """
    if entity.entity_type == "class":
        return [GenerationVariant.DEFAULT]

    variants: List[GenerationVariant] = [GenerationVariant.DEFAULT]
    name = entity.name.lower()

    special = _special_variant_for_name(name)
    if special is not None:
        variants.append(special)

    return variants


def _special_variant_for_name(name: str) -> Optional[GenerationVariant]:
    """Return the first matching special variant for *name*, or None."""
    if any(p in name for p in _ROUNDTRIP_PATTERNS):
        return GenerationVariant.ROUNDTRIP
    if any(p in name for p in _IDEMPOTENT_PATTERNS):
        return GenerationVariant.IDEMPOTENT
    if any(p in name for p in _ERRORS_EQUIV_PATTERNS):
        return GenerationVariant.ERRORS_EQUIVALENT
    if any(p in name for p in _BINARY_OP_PATTERNS):
        return GenerationVariant.BINARY_OP
    return None
