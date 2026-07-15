# RED test for the finding — import verified by the harness; expected value from the finding's own command (see FACT).
from pathlib import Path

from src.dev.test_generator.generate.prompts import ANALYSIS_SYSTEM_PROMPT  # verified working import — do not edit

# F81 (audit/02-static-audit.md#L97): test_analysis_uses_analysis_system_prompt imports
# ANALYSIS_SYSTEM_PROMPT but its assert statement never references it — it only checks the
# generic substrings "analyze"/"plan". Per the plan (D-2/§2#3), fabric.py already passes the
# constant verbatim today, so an equality check against production behavior would pass, not fail.
# The actual defect is in the weak test's own assert line, so this test pins THAT directly: it
# reads the assert line's source text and requires it to reference ANALYSIS_SYSTEM_PROMPT.
_FABRIC_TEST_PATH = (
    Path(__file__).resolve().parent / "test_generator" / "test_strategy_fabric.py"
)


def test_analysis_system_prompt_pins_the_finding_defect():
    assert ANALYSIS_SYSTEM_PROMPT  # sanity: the real constant is importable and non-empty

    lines = _FABRIC_TEST_PATH.read_text().splitlines()
    start = next(
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("def test_analysis_uses_analysis_system_prompt")
    )
    end = next(
        i
        for i in range(start + 1, len(lines))
        if lines[i].startswith("    def ")
    )
    assert_line = next(
        line for line in reversed(lines[start:end]) if line.strip().startswith("assert")
    )

    assert "ANALYSIS_SYSTEM_PROMPT" in assert_line, (
        "test_analysis_uses_analysis_system_prompt's assertion must reference the imported "
        "ANALYSIS_SYSTEM_PROMPT constant (F81 drift-blindness) instead of only checking generic "
        f"'analyze'/'plan' substrings — found: {assert_line.strip()!r}"
    )
