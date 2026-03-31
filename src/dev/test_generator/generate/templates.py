"""
Command-string templates for hypothesis write invocations — pure domain layer.

Translates (TestableEntity, GenerationVariant) pairs into the exact command
arguments that should be passed to ``hypothesis write``.  No subprocess calls
happen here; this is just string construction logic extracted from
scripts/hypot_test_gen.py (generate_method_variants / generate_function_variants).
"""

from src.dev.test_generator.core.models import GenerationVariant, TestableEntity

# Base flags used for every hypothesis write invocation.
_BASE_FLAGS = "--style=unittest --annotate"

# Map each special variant to the extra flag(s) it needs.
_VARIANT_FLAGS: dict = {
    GenerationVariant.DEFAULT: "",
    GenerationVariant.ROUNDTRIP: "--roundtrip",
    GenerationVariant.IDEMPOTENT: "--idempotent",
    GenerationVariant.ERRORS_EQUIVALENT: "--errors-equivalent",
    GenerationVariant.BINARY_OP: "--binary-op",
}


def build_hypothesis_command(entity: TestableEntity, variant: GenerationVariant) -> str:
    """Return the argument string for ``hypothesis write <args>``.

    The caller is responsible for prepending ``hypothesis write`` and
    executing the command.

    Examples
    --------
    >>> build_hypothesis_command(entity_add, GenerationVariant.DEFAULT)
    '--style=unittest --annotate pkg.mod.add'
    >>> build_hypothesis_command(entity_encode, GenerationVariant.ROUNDTRIP)
    '--style=unittest --annotate --roundtrip pkg.mod.Codec.encode'
    """
    target = _entity_target(entity)
    extra = _VARIANT_FLAGS.get(variant, "")
    parts = [_BASE_FLAGS]
    if extra:
        parts.append(extra)
    parts.append(target)
    return " ".join(parts)


def _entity_target(entity: TestableEntity) -> str:
    """Build the dotted target path for hypothesis write."""
    if entity.entity_type in ("method", "instance_method") and entity.parent_class:
        return f"{entity.module_path}.{entity.parent_class}.{entity.name}"
    return f"{entity.module_path}.{entity.name}"
