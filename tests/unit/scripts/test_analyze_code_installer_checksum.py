"""Oracle test for Finding F14.

`scripts/analyze_code.sh:95-99` currently pipes the CodeScene CLI installer straight from `curl` into
`sh` with no integrity check. Per the locked plan (.aiv/plans/pef-p02-verify-codescene-cli-install-plan.md
B1/B4), the fix is a sourceable helper (`scripts/lib/verify_installer_checksum.sh`) exposing
`verify_codescene_installer_checksum <path>`, which must exit 0 for a file matching the pinned sha256 and
non-zero for anything else. This test exercises that real bash function via a live subprocess (Class A
behavioral evidence), against fixture files supplied directly by the test itself (test-layer contract
§12: the caller-supplied file path is set explicitly here, not assumed).
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER_SCRIPT = REPO_ROOT / "scripts" / "lib" / "verify_installer_checksum.sh"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "codescene_installer"
PINNED_FIXTURE = FIXTURES_DIR / "install-codescene-cli.pinned.sh"
MUTATED_FIXTURE = FIXTURES_DIR / "install-codescene-cli.mutated.sh"


def _run_verify(fixture_path: Path) -> subprocess.CompletedProcess:
    assert HELPER_SCRIPT.exists(), (
        f"expected a checksum-verification helper at {HELPER_SCRIPT} (plan B1), but it does not exist — "
        "scripts/analyze_code.sh:95-99 still pipes curl output directly into sh with no integrity check"
    )
    assert fixture_path.exists(), f"missing test fixture: {fixture_path} (plan B2/B3)"
    return subprocess.run(
        [
            "bash",
            "-c",
            f'source "{HELPER_SCRIPT}"; verify_codescene_installer_checksum "{fixture_path}"',
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_codescene_installer_mutated_fixture_is_rejected():
    """A byte-mutated installer must NOT pass checksum verification (AC1)."""
    result = _run_verify(MUTATED_FIXTURE)
    assert result.returncode != 0, (
        "verify_codescene_installer_checksum must reject a byte-mutated CodeScene installer "
        f"(exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r})"
    )


def test_codescene_installer_pinned_fixture_is_accepted():
    """An installer matching the pinned sha256 must pass checksum verification (AC2)."""
    result = _run_verify(PINNED_FIXTURE)
    assert result.returncode == 0, (
        "verify_codescene_installer_checksum must accept the installer matching the pinned sha256 "
        f"(exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r})"
    )
