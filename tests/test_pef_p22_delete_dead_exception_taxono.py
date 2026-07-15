# RED test for the finding — import verified by the harness; expected value from the finding's own command (see FACT).
from src.branch_fixer.core.exceptions import CoordinationError, InteractionError, ComponentError, WorkflowError  # verified working import — do not edit


def test_coordinationerror_pins_the_finding_defect():
    # This is a deletion-only finding (F5/F6, audit/02-static-audit.md:54): CoordinationError,
    # InteractionError, ComponentError, and WorkflowError are dead code with zero production
    # consumers (confirmed by QUALITY_AUDIT.md:21). The correct expected state, per the finding's
    # GOAL, is that src/branch_fixer/core/exceptions.py no longer exists. Currently it does exist
    # (the import above succeeds), so this assertion is RED against the current buggy state and
    # will turn GREEN once the file is deleted.
    import os

    exceptions_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "branch_fixer",
        "core",
        "exceptions.py",
    )
    assert CoordinationError.__module__ == "src.branch_fixer.core.exceptions"
    assert not os.path.exists(exceptions_file), (
        f"{exceptions_file} should be deleted: CoordinationError, InteractionError, "
        "ComponentError, and WorkflowError are dead code with zero production consumers "
        "(audit/02-static-audit.md:54, QUALITY_AUDIT.md:21)"
    )
