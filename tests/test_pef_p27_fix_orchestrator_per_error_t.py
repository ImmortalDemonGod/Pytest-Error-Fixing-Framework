"""
RED tests for finding F50 (covers F50, F51, F62): FixOrchestrator per-error state
bugs in src/branch_fixer/orchestration/orchestrator.py.

All three tests assert the CORRECT expected behavior and must currently FAIL
because the production bugs are still present:
  1. get_progress() reports temperature from the global (cross-error) retry_count
     instead of the current error's own attempt count.
  2. run_session() skips the failed_tests/passed_tests update when it returns
     early because an error could not be fixed.
  3. FixService is constructed once per retry attempt instead of once per error.
"""
import sys
import types
from types import SimpleNamespace

import pytest

from branch_fixer.core.models import ErrorDetails, TestError
from branch_fixer.orchestration.orchestrator import FixOrchestrator


def _inject_fake_fix_service(attempt_fix_impl):
    """Install a fake branch_fixer.orchestration.fix_service.FixService module."""
    mod_name = "branch_fixer.orchestration.fix_service"
    fake_mod = types.ModuleType(mod_name)

    class FakeFixService:
        def __init__(self, *args, **kwargs):
            pass

        def attempt_fix(self, error, temperature):
            return attempt_fix_impl(error, temperature)

    fake_mod.FixService = FakeFixService
    sys.modules[mod_name] = fake_mod
    return mod_name


def _make_error(tmp_path, name):
    f = tmp_path / f"{name}.py"
    f.write_text("x = 1\n", encoding="utf-8")
    return TestError(
        test_file=f,
        test_function=name,
        error_details=ErrorDetails(error_type="E", message="m"),
    )


def _make_orchestrator(**overrides):
    kwargs = dict(
        ai_manager=SimpleNamespace(),
        test_runner=SimpleNamespace(),
        change_applier=SimpleNamespace(),
        git_repo=SimpleNamespace(),
        max_retries=3,
        initial_temp=0.4,
        temp_increment=0.1,
    )
    kwargs.update(overrides)
    return FixOrchestrator(**kwargs)


def test_get_progress_temperature_reflects_current_error_not_global_retry_count(
    tmp_path,
):
    """F50: current_temperature must match the temperature actually in use for
    the CURRENT error's attempt, not initial_temp + temp_increment * the
    session-wide retry_count accumulated by OTHER, earlier errors."""
    e1 = _make_error(tmp_path, "t1")
    e2 = _make_error(tmp_path, "t2")

    orch = _make_orchestrator(max_retries=3, initial_temp=0.4, temp_increment=0.1)
    orch.start_session([e1, e2])

    observed = []

    def attempt_fix_impl(error, temperature):
        if error is e1:
            # e1 fails every attempt -> bumps the session-wide retry_count to 3
            return False
        # e2's first attempt: the REAL temperature just sent to fix_service is
        # `temperature` (== orch.initial_temp, since e2 has had zero attempts
        # of its own). get_progress() must agree with that value.
        observed.append((temperature, orch.get_progress().current_temperature))
        return True

    mod_name = _inject_fake_fix_service(attempt_fix_impl)
    try:
        assert orch.fix_error(e1) is False
        assert orch.fix_error(e2) is True

        actual_temp_used, reported_temp = observed[0]
        assert actual_temp_used == pytest.approx(0.4)
        # This is the bug: get_progress() currently reports
        # initial_temp + temp_increment * session.retry_count (0.4 + 0.1*3 = 0.7...)
        # instead of the 0.4 that was actually used for e2's first attempt.
        assert reported_temp == pytest.approx(actual_temp_used)
    finally:
        del sys.modules[mod_name]


def test_run_session_persists_correct_counts_when_error_left_unfixed(tmp_path):
    """F51: when run_session() returns early because an error could not be
    fixed, session.failed_tests/passed_tests must still be computed correctly
    (not left at their zero defaults)."""
    e1 = _make_error(tmp_path, "t1")

    orch = _make_orchestrator()
    s = orch.start_session([e1])

    # Simulate an irreparable error: _handle_error_fix returns False and the
    # error's status is never marked "fixed".
    orch._handle_error_fix = lambda error: False

    result = orch.run_session(s.id)

    assert result is False
    assert s.failed_tests == 1
    assert s.passed_tests == 0


def test_fixservice_constructed_once_per_error_not_per_retry_attempt(tmp_path):
    """F62: FixService must be instantiated exactly once per error, and reused
    across that error's retry attempts -- not re-constructed on every attempt."""
    e1 = _make_error(tmp_path, "t1")

    orch = _make_orchestrator(max_retries=3)
    orch.start_session([e1])

    init_calls = []
    attempts = {"n": 0}

    mod_name = "branch_fixer.orchestration.fix_service"
    fake_mod = types.ModuleType(mod_name)

    class FakeFixService:
        def __init__(self, *args, **kwargs):
            init_calls.append(1)

        def attempt_fix(self, error, temperature):
            attempts["n"] += 1
            # Fails the first attempt, succeeds on the second.
            return attempts["n"] >= 2

    fake_mod.FixService = FakeFixService
    sys.modules[mod_name] = fake_mod
    try:
        assert orch.fix_error(e1) is True
        assert attempts["n"] == 2
        assert len(init_calls) == 1
    finally:
        del sys.modules[mod_name]
