# Bug catalog — Finding F14 (CodeScene CLI installer: unverified `curl | sh`)

- **Symptom:** The CodeScene-CLI install guard pipes an unauthenticated network download straight into
  a shell interpreter with no integrity check, so a compromised/MITM'd response executes arbitrary code.
  - `file:line` — `scripts/analyze_code.sh:96`
  - Wrong: `curl -sSf https://downloads.codescene.io/enterprise/cli/install-codescene-cli.sh | sh` — the
    downloaded bytes are executed via the pipe before anything examines them.
  - Correct: the download is written to a file first, its sha256 is compared against a pinned constant,
    and `sh` is only invoked on the file if the checksum matches; a mismatch aborts with a non-zero exit
    and never calls `sh` on the file.

- **Symptom:** No checksum-verification function exists anywhere in the codebase for this installer, so
  there is nothing a caller could invoke even if it wanted to gate execution on integrity.
  - `file:line` — `scripts/analyze_code.sh:88-108` (whole install guard block; confirmed via
    `grep -nE "sha256|checksum|gpg|shasum" scripts/analyze_code.sh` → 0 matches)
  - Wrong: no `verify_codescene_installer_checksum`-equivalent function/constant exists in the repo.
  - Correct: a sourceable helper (e.g. `scripts/lib/verify_installer_checksum.sh`) defines a pinned
    `CODESCENE_INSTALLER_SHA256` constant and a `verify_codescene_installer_checksum <path>` function that
    returns 0 only when the file at `<path>` hashes to that pinned value, and non-zero otherwise.

- **Symptom:** A byte-mutated copy of the installer script is indistinguishable from the real one at
  execution time — the guard has no oracle to reject tampered content before running it.
  - `file:line` — `scripts/analyze_code.sh:95-99`
  - Wrong: any content returned by the `curl` request (real, corrupted, or attacker-substituted) reaches
    `sh` unconditionally as long as the HTTP request itself succeeds (`curl -sSf` only checks HTTP status,
    not payload integrity).
  - Correct: content whose sha256 does not match the pinned `CODESCENE_INSTALLER_SHA256` is rejected
    (process exits non-zero, `sh` is never invoked on it); content matching the pin proceeds to execution.
