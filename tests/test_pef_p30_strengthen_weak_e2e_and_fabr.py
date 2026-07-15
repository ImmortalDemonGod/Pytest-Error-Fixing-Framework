# RED test for the finding — the fix-pipeline harness pre-resolved and VERIFIED the import below (#146).
# Your ONLY job: replace the sentinel line in the test body with a REAL assertion that FAILS against the
# CURRENT (buggy) value of ANALYSIS_SYSTEM_PROMPT (assert the CORRECT expected value). Do NOT change the import line.
# Use the FACT output(s) above for the CORRECT expected value — do NOT invent a number.
from src.dev.test_generator.generate.prompts import ANALYSIS_SYSTEM_PROMPT  # verified working import — do not edit


def test_analysis_system_prompt_pins_the_finding_defect():
    # ANALYSIS_SYSTEM_PROMPT is imported above and ready to assert on.
    # Replace the next line with e.g.:  assert abs(ANALYSIS_SYSTEM_PROMPT - <CORRECT_VALUE_from_the_FACT_above>) < <TOL>
    raise NotImplementedError("SCAFFOLD_SENTINEL_fill_the_red_assertion")
