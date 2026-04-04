"""
Filesystem writer for generated test files.

Promoted from scripts/hypot_test_gen.py (write_and_verify_output / handle_generated_output).
Single responsibility: write a string to a path and verify the round-trip.
"""

from pathlib import Path

from src.dev.test_generator.core.models import GenerationAttempt, TestableEntity


def output_filename(entity: TestableEntity, variant_label: str) -> str:
    """
    Constructs a deterministic filename for a generated test module.
    
    Parameters:
    	entity (TestableEntity): Entity whose `name` and optional `parent_class` are used to form the filename prefix.
    	variant_label (str): Variant label appended to the filename.
    
    Returns:
    	filename (str): Filename in the form `test_{prefix}_{variant_label}.py` where `prefix` is `{parent_class}_{name}` if `parent_class` is present, otherwise `name`.
    """
    if entity.parent_class:
        prefix = f"{entity.parent_class}_{entity.name}"
    else:
        prefix = entity.name
    return f"test_{prefix}_{variant_label}.py"


def write_module_test(code: str, source_stem: str, output_dir: Path) -> Path:
    """
    Write a consolidated module-level test file for a given source stem.
    
    Parameters:
        code (str): Generated test source code to write.
        source_stem (str): Stem of the source file; the output filename will be `test_{source_stem}.py`.
        output_dir (Path): Directory to write the file into.
    
    Returns:
        out_path (Path): Path to the written file.
    
    Raises:
        RuntimeError: If the written file is empty or the read-back content differs from `code`.
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
    """
    Write a successful generation attempt's code to disk using a deterministic filename and verify the file content matches the source.
    
    Parameters:
        attempt (GenerationAttempt): A completed generation attempt whose `status` must be `"success"` and whose `generated_code` must be non-None.
        output_dir (Path): Directory where the file will be written.
    
    Returns:
        out_path (Path): Path to the written test file.
    
    Raises:
        ValueError: If `attempt.status` is not `"success"` or `attempt.generated_code` is None.
        RuntimeError: If the written file is empty or its content differs from `attempt.generated_code`.
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
