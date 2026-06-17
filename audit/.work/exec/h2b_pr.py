"""Real PR-build logic with the gh/subprocess boundary stubbed."""
import subprocess, shutil
from pathlib import Path
import branch_fixer.services.git.pr_manager as prm
from branch_fixer.services.git.repository import GitRepository

captured = {}
def fake_run(argv, **kw):
    captured["argv"] = argv
    return subprocess.CompletedProcess(argv, 0, stdout="https://github.com/fake/owner/repo/pull/1\n", stderr="")
prm.subprocess.run = fake_run
prm.shutil.which = lambda n: "/usr/bin/gh" if n == "gh" else shutil.which(n)

try:
    repo = GitRepository(Path("."))
except TypeError:
    repo = GitRepository(root=Path("."))
pm = prm.PRManager(repo)
d = pm.create_pr(title="Fix failing test", description="auto fix",
                 branch_name="fix-demo-abc123", modified_files=[Path("tests/test_demo.py")])
print("[PR] create_pr returned type:", type(d).__name__)
print("[PR] gh argv actually built:", captured.get("argv"))
print(f"[PR] id={getattr(d,'id',None)} url={getattr(d,'url',None)} "
      f"status={getattr(d,'status',None)} branch={getattr(d,'branch_name',None)}")
print(f"[PR] F61 confirmed (modified_files NOT passed to gh): "
      f"{'test_demo.py' not in str(captured.get('argv'))}")
print("=== DONE h2b ===")
