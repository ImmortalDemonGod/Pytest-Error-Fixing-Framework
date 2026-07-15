# RED test for the finding — import verified by the harness; expected value from the finding's own command (see FACT).
from src.branch_fixer.core.models import CodeChanges  # verified working import — do not edit

import dataclasses


def test_codechanges_pins_the_finding_defect():
    # Correct expected shape (plan D1/D2): the always-empty `original_code` field is removed
    # entirely, leaving `CodeChanges` with only `modified_code`.
    field_names = {f.name for f in dataclasses.fields(CodeChanges)}
    assert field_names == {"modified_code"}
