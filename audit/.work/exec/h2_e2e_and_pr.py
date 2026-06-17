"""Proof-of-attempt: real end-to-end fix logic (ChangeApplier + verify_fix subprocess,
AI boundary stubbed) on a genuinely-failing test; and real PR-build logic with gh stubbed."""
import os, subprocess, shutil
from pathlib import Path

from branch_fixer.core.models import CodeChanges
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.pytest.runner import TestRunner

# ---- A. End-to-end fix on a genuinely failing test (not xfail) ----
d = Path("/tmp/fixdemo"); d.mkdir(parents=True, exist_ok=True)
tf = d / "test_demo.py"
tf.write_text("def test_demo():\n    assert 2 + 2 == 5  # genuinely fails\n", encoding="utf-8")

runner = TestRunner()
before = runner.verify_fix(tf, "test_demo")
print(f"[E2E] verify_fix BEFORE fix: {before}  (expect False — test genuinely fails)")

applier = ChangeApplier()
changes = CodeChanges(original_code=tf.read_text(),
                      modified_code="def test_demo():\n    assert 2 + 2 == 4  # fixed\n")
ok, backup = applier.apply_changes_with_backup(tf, changes)
print(f"[E2E] apply_changes_with_backup -> success={ok}, backup={backup}")
print(f"[E2E] backup exists on disk: {bool(backup) and Path(backup).exists()}")
print(f"[E2E] file now contains: {tf.read_text().strip()!r}")

after = runner.verify_fix(tf, "test_demo")
print(f"[E2E] verify_fix AFTER fix: {after}  (expect True — fix makes it pass)")
print(f"[E2E] RESULT: real fix pipeline flipped the test {before} -> {after}")

# negative-path: assert-guard should REJECT a fix that deletes all assertions
tf.write_text("def test_demo():\n    assert 2 + 2 == 5\n", encoding="utf-8")
ok2, backup2 = applier.apply_changes_with_backup(tf, CodeChanges(
    original_code=tf.read_text(), modified_code="def test_demo():\n    pass  # no assertion\n"))
print(f"[E2E] assert-guard on assertion-deleting fix: success={ok2} (expect False — guard rejects)")

# ---- B. Real PR-build logic, gh + subprocess boundary stubbed ----
import branch_fixer.services.git.pr_manager as prm
captured = {}
def fake_run(argv, **kw):
    captured["argv"] = argv
    return subprocess.CompletedProcess(argv, 0, stdout="https://github.com/fake/owner/repo/pull/1\n", stderr="")
prm.subprocess.run = fake_run
prm.shutil.which = lambda name: "/usr/bin/gh" if name == "gh" else shutil.which(name)

pm = prm.PRManager()
details = pm.create_pr(title="Fix failing test", description="auto fix",
                       branch_name="fix-demo-abc123", modified_files=[Path("tests/test_demo.py")])
print(f"\n[PR] create_pr returned type: {type(details).__name__}")
print(f"[PR] gh argv actually built: {captured.get('argv')}")
print(f"[PR] PRDetails.id={getattr(details,'id',None)} url={getattr(details,'url',None)} "
      f"status={getattr(details,'status',None)} branch={getattr(details,'branch_name',None)}")
print(f"[PR] NOTE F61: modified_files passed but gh argv contains no file refs: "
      f"{'tests/test_demo.py' not in str(captured.get('argv'))}")
print("\n=== DONE h2 ===")
