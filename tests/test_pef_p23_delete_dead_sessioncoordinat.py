# RED test for the finding — import verified by the harness; expected value from the finding's own command (see FACT).
from src.branch_fixer.orchestration.coordinator import SessionCoordinator  # verified working import — do not edit


def test_sessioncoordinator_pins_the_finding_defect():
    # F70 (coordinator.py:19-31): coordinate_fix_attempt is a permanent async no-op (body is
    # `pass`, always returns None) despite zero production callers and zero test coverage in
    # src/ or tests/. The finding's goal condition is deletion, not implementation, so the
    # correct expected state is that this attribute does not exist on SessionCoordinator at all.
    assert not hasattr(SessionCoordinator, "coordinate_fix_attempt"), (
        "SessionCoordinator.coordinate_fix_attempt still exists as a permanent no-op stub "
        "(src/branch_fixer/orchestration/coordinator.py:19-31: body is `pass`, always returns "
        "None) despite having zero production callers and zero test coverage. Per the finding's "
        "goal condition, the correct fix is full deletion of SessionCoordinator, not "
        "implementing this method — it should not exist."
    )
    # F71 (coordinator.py:33-47): handle_failure hardcodes `return False` unconditionally for
    # the same reason — zero callers, zero coverage, correct fix is deletion not a real return.
    assert not hasattr(SessionCoordinator, "handle_failure"), (
        "SessionCoordinator.handle_failure still hardcodes `return False` unconditionally "
        "(src/branch_fixer/orchestration/coordinator.py:33-47) despite having zero production "
        "callers and zero test coverage. Per the finding's goal condition, the correct fix is "
        "full deletion of SessionCoordinator, not implementing this method — it should not "
        "exist."
    )
