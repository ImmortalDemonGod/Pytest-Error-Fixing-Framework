"""RED tests for pef-p03-harden-hypot-test-gen-subpro (F33-F36).

Exercises scripts/hypot_test_gen.py directly (the real, currently-vulnerable
public symbols) rather than the already-hardened DDD port under
src/dev/test_generator/.
"""
import logging
import os
import subprocess
import sys
from pathlib import Path

import scripts.hypot_test_gen as hypot_test_gen
from scripts.hypot_test_gen import TestableEntity, TestGenerator

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_injection_blocked(tmp_path, monkeypatch):
    """F33: shell metacharacters in the derived command must not execute."""
    monkeypatch.chdir(tmp_path)
    marker = tmp_path / "pwned.txt"
    generator = TestGenerator(output_dir=tmp_path / "out")

    malicious_command = f"$(touch {marker}).SomeClass.method"
    generator.run_hypothesis_write(malicious_command)

    assert not marker.exists(), (
        "run_hypothesis_write executed shell metacharacters embedded in the "
        "command string ($(...) ran via shell=True) — command injection"
    )


def test_retry_respects_max_retries(monkeypatch, caplog):
    """F34: retry-wait must fire on attempts 1..max_retries-1, terminal
    failure exactly once, on attempt max_retries."""
    monkeypatch.setattr(hypot_test_gen.time, "sleep", lambda *_: None)

    entity = TestableEntity(name="foo", module_path="mod", entity_type="function")
    variant = {"type": "basic", "cmd": "mod.foo"}
    generator = TestGenerator(output_dir=Path(__file__).resolve().parent)
    monkeypatch.setattr(generator, "run_hypothesis_write", lambda command: None)

    caplog.set_level(logging.DEBUG, logger="scripts.hypot_test_gen")
    generator.try_generate_test(entity, variant, max_retries=5)

    retry_records = [r for r in caplog.records if "retrying" in r.getMessage().lower()]
    final_failure_records = [
        r for r in caplog.records if "all attempts failed" in r.getMessage().lower()
    ]

    assert len(retry_records) == 4, (
        f"expected 4 retry-wait log messages (attempts 1-4) for max_retries=5, "
        f"got {len(retry_records)}: {[r.getMessage() for r in retry_records]}"
    )
    assert len(final_failure_records) == 1, (
        f"expected exactly 1 terminal-failure log message (attempt 5 only) for "
        f"max_retries=5, got {len(final_failure_records)}: "
        f"{[r.getMessage() for r in final_failure_records]}"
    )


def test_snoop_no_import_side_effect(tmp_path):
    """F35: importing scripts.hypot_test_gen must not create snoop_debug.log
    as an import-time side effect."""
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    result = subprocess.run(
        [sys.executable, "-c", "import scripts.hypot_test_gen"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"importing scripts.hypot_test_gen failed: {result.stderr}"
    )
    assert not (tmp_path / "snoop_debug.log").exists(), (
        "importing scripts.hypot_test_gen must not eagerly create "
        "snoop_debug.log as an import-time side effect"
    )


def test_venv_bin_hypothesis_path(monkeypatch, tmp_path):
    """F36: the hypothesis subprocess must target the venv-local binary
    (Path(sys.executable).parent / 'hypothesis'), not a bare PATH lookup."""
    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(hypot_test_gen.subprocess, "run", fake_run)
    generator = TestGenerator(output_dir=tmp_path / "out")
    generator.run_hypothesis_write("mod.Foo.bar")

    expected_bin = str(Path(sys.executable).parent / "hypothesis")
    invoked = captured["args"][0] if captured.get("args") else captured["kwargs"].get("args")

    assert expected_bin in str(invoked), (
        f"hypothesis subprocess must invoke the venv-local binary {expected_bin!r}, "
        f"got {invoked!r}"
    )
