"""RED test for F88/F38 (pef-p06b-guard-transient-api).

FixOrchestrator.fix_error's retry loop (src/branch_fixer/orchestration/orchestrator.py:357)
calls fix_service.attempt_fix(...) with no enclosing try/except. A FixServiceError raised on
attempt 1 (e.g. from a transient AI-provider CompletionError) therefore escapes fix_error
entirely instead of being treated like a failed attempt and retried. This test asserts the
CORRECT behavior (retry survives, session completes, and the FixServiceError's inner-cause
text is retained when logged) and must FAIL against the current, still-buggy code.
"""

import logging
import sys
import types
from types import SimpleNamespace

import pytest

from branch_fixer.core.models import ErrorDetails, TestError
from branch_fixer.orchestration.exceptions import FixServiceError
from branch_fixer.orchestration.orchestrator import FixOrchestrator


def _inject_fake_fix_service(behavior, call_recorder=None):
    """Same injection pattern already used by tests/unit/orchestration/test_orchestrator.py."""
    mod_name = "branch_fixer.orchestration.fix_service"
    fake_mod = types.ModuleType(mod_name)

    class FakeFixService:
        def __init__(self, *args, **kwargs):
            pass

        def attempt_fix(self, error, temperature):
            if call_recorder is not None:
                call_recorder.append(temperature)
            if not behavior:
                return False
            val = behavior.pop(0)
            if isinstance(val, Exception):
                raise val
            return val

    fake_mod.FixService = FakeFixService
    sys.modules[mod_name] = fake_mod
    return mod_name


@pytest.fixture
def simple_error(tmp_path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_dummy():\n    assert True\n", encoding="utf-8")
    ed = ErrorDetails(error_type="AssertionError", message="failed", stack_trace=None)
    return TestError(test_file=test_file, test_function="test_dummy", error_details=ed)


def test_fix_error_retries_past_transient_fixserviceerror_and_preserves_message(
    simple_error, caplog
):
    call_temps = []
    # Mimics the message shape a real F38-affected FixServiceError carries: the
    # contextualized inner text that must survive up to whatever logs/surfaces it.
    inner_cause_text = "Workspace validation failed: simulated rate limit exceeded"
    behavior = [FixServiceError(inner_cause_text), True]
    mod_name = _inject_fake_fix_service(behavior, call_recorder=call_temps)

    # Caller-supplied values set explicitly, per the plan's test-layer contract.
    max_retries = 2
    initial_temp = 0.3
    temp_increment = 0.1

    orch = FixOrchestrator(
        ai_manager=SimpleNamespace(),
        test_runner=SimpleNamespace(),
        change_applier=SimpleNamespace(),
        git_repo=SimpleNamespace(),
        max_retries=max_retries,
        initial_temp=initial_temp,
        temp_increment=temp_increment,
    )
    session = orch.start_session([simple_error])

    try:
        propagated_error = None
        ok = None
        with caplog.at_level(logging.WARNING):
            try:
                ok = orch.fix_error(simple_error)
            except FixServiceError as e:
                propagated_error = e

        # F88: a transient FixServiceError on attempt 1 must NOT abort the session.
        assert propagated_error is None, (
            "A transient FixServiceError raised on attempt 1 must be caught and "
            f"retried by fix_error(), not allowed to escape uncaught: {propagated_error!r}"
        )
        assert ok is True
        # Exactly one failed-then-retried attempt before the attempt-2 success.
        assert session.retry_count == 1
        assert call_temps == pytest.approx([initial_temp, initial_temp + temp_increment])

        # F38 (message-retention half of this finding's GOAL): whatever fix_error
        # surfaces about the caught failure must retain the inner cause text, not
        # discard it.
        assert inner_cause_text in caplog.text, (
            "The transient FixServiceError's inner cause text must be retained when "
            "fix_error catches and logs it, not discarded."
        )
    finally:
        del sys.modules[mod_name]
