"""
Filesystem writer for generated test files.

Promoted from scripts/hypot_test_gen.py (write_and_verify_output / handle_generated_output).
Single responsibility: write a string to a path and verify the round-trip.
"""

from pathlib import Path

from src.dev.test_generator.core.models import GenerationAttempt, TestableEntity


def output_filename(entity: TestableEntity, variant_label: str) -> str:
    """Derive a deterministic filename for a generated test.

    Examples
    --------
    ``add``, ``default`` → ``test_add_default.py``
    ``Codec.encode``, ``roundtrip`` → ``test_Codec_encode_roundtrip.py``
    """
    if entity.parent_class:
        prefix = f"{entity.parent_class}_{entity.name}"
    else:
        prefix = entity.name
    return f"test_{prefix}_{variant_label}.py"


def write_module_test(code: str, source_stem: str, output_dir: Path) -> Path:
    """Write a module-level consolidated test file and return its path.

    Parameters
    ----------
    code:
        The generated test source code.
    source_stem:
        The stem of the source file being tested (e.g. ``"change_applier"``).
        The output file will be named ``test_{source_stem}.py``.
    output_dir:
        Directory to write the file into.

    Raises
    ------
    RuntimeError
        If the written file is empty or content does not round-trip.
    """
    out_path = output_dir / f"test_{source_stem}.py"
    out_path.write_text(code, encoding="utf-8")
    written = out_path.read_text(encoding="utf-8")
    if not written:
        raise RuntimeError(f"Output file is empty after writing: {out_path}")
    if written != code:
        raise RuntimeError(f"Content mismatch after writing: {out_path}")
    return out_path


def write_attempt(attempt: GenerationAttempt, output_dir: Path) -> Path:
    """Write *attempt.generated_code* to *output_dir* and return the path.

    Raises
    ------
    ValueError
        If the attempt has no generated code or has not succeeded.
    RuntimeError
        If the written file is empty or the content does not round-trip.
    """
    if attempt.status != "success" or attempt.generated_code is None:
        raise ValueError(
            f"Attempt {attempt.id} is not in success state — cannot write."
        )

    filename = output_filename(attempt.entity, attempt.variant.value)
    out_path = output_dir / filename
    out_path.write_text(attempt.generated_code, encoding="utf-8")

    # Verify round-trip
    written = out_path.read_text(encoding="utf-8")
    if not written:
        raise RuntimeError(f"Output file is empty after writing: {out_path}")
    if written != attempt.generated_code:
        raise RuntimeError(f"Content mismatch after writing: {out_path}")

    return out_path
