import subprocess, tempfile
from pathlib import Path
from branch_fixer.services.git.repository import GitRepository
d = Path(tempfile.mkdtemp(prefix="branchdemo_"))
subprocess.run(["git","init","-q","-b","main"],cwd=d,check=True)
subprocess.run(["git","-c","commit.gpgsign=false","-c","user.email=a@b.c","-c","user.name=x","commit","--allow-empty","-m","init","-q"],cwd=d,check=True)
repo = GitRepository(d)
print("[GIT] current branch:", repo.get_current_branch())
print("[GIT] create_fix_branch('fix-demo-xyz') ->", repo.create_fix_branch("fix-demo-xyz"))
print("[GIT] branch_exists('fix-demo-xyz'):", repo.branch_exists("fix-demo-xyz"))
try:
    print("[GIT] cleanup_fix_branch ->", repo.branch_manager.cleanup_fix_branch("fix-demo-xyz", force=True))
except Exception as e:
    print("[GIT] cleanup ->", type(e).__name__, str(e)[:80])
print("=== DONE h3 ===")
