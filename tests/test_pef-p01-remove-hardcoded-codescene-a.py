"""RED test for F13: hardcoded CodeScene access token in scripts/analyze_code.sh.

Finding: https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework/blob/
697ab7f3414459edd480bb72a342446d040b3134/audit/02-static-audit.md#L12
"""
import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "analyze_code.sh"

LEAKED_TOKEN = (
    "Njk0NjM-MjAyNi0wMS0xN1QxOTo1Mzo1Mw-I3sicmVmYWN0b3IuYWNjZXNzIiAiY2xpLmFjY2Vzcy"
    "J9.30-SmgU-Ybio83czYew_WCtu_QvyPWyWlSQQD63_gZA"
)

# End of the buggy "0y-1. Ensure CodeScene Access Token is set" block (line 122's
# closing `fi`) — slicing here isolates the token-fallback bug from the unrelated
# `uv`/`cs`/ruff install machinery that follows, so this test cannot be defeated
# (or made to hang / hit the network) by later, out-of-scope parts of the script.
TOKEN_BLOCK_END_LINE = 123


def _write_stub_executable(bin_dir: Path, name: str) -> None:
    stub = bin_dir / name
    stub.write_text("#!/bin/sh\nexit 0\n")
    mode = stub.stat().st_mode
    stub.chmod(mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def test_missing_cs_access_token_fails_fast_without_hardcoded_fallback(tmp_path):
    script_text = SCRIPT_PATH.read_text()

    # Class C (negative) + AC1: no credential-shaped literal may ever be
    # assigned to CS_ACCESS_TOKEN anywhere in the tracked script.
    assert LEAKED_TOKEN not in script_text, (
        f"hardcoded CodeScene access token literal still present in {SCRIPT_PATH}"
    )

    # Class A (behavioral) + AC2: with CS_ACCESS_TOKEN unset, the script must
    # fail fast (non-zero exit, explicit stderr message) instead of silently
    # exporting a baked-in default and continuing.
    stub_bin_dir = tmp_path / "stubbin"
    stub_bin_dir.mkdir()
    _write_stub_executable(stub_bin_dir, "uv")
    _write_stub_executable(stub_bin_dir, "cs")

    target_file = tmp_path / "dummy_target.py"
    target_file.write_text("x = 1\n")

    script_slice = tmp_path / "token_block_slice.sh"
    lines = script_text.splitlines(keepends=True)[:TOKEN_BLOCK_END_LINE]
    script_slice.write_text("".join(lines))

    env = os.environ.copy()
    env.pop("CS_ACCESS_TOKEN", None)
    env["PATH"] = f"{stub_bin_dir}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(script_slice), str(target_file)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode != 0, (
        "analyze_code.sh must exit non-zero when CS_ACCESS_TOKEN is unset "
        f"(fail fast instead of using a baked-in default); got exit code "
        f"{result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert "CS_ACCESS_TOKEN" in result.stderr, (
        f"expected an explicit CS_ACCESS_TOKEN error on stderr, got {result.stderr!r}"
    )
    assert "Setting a default" not in (result.stdout + result.stderr), (
        "script must not silently fall back to a default token"
    )
