"""
core/github.py — Коммит и пуш результатов в GitHub.
Коммитит только results/, wiki/projects/, projects/.
Credentials никогда не попадают в репо (.gitignore).
"""
import subprocess
from datetime import datetime
from pathlib import Path

TESTLAB_ROOT = Path(__file__).parent.parent


def push_results(suite_result, testlab_root=None) -> dict:
    root = testlab_root or TESTLAB_ROOT
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = (f"testlab({suite_result.project}): {suite_result.suite_id} "
           f"status={suite_result.status} [{ts}] {suite_result.summary}")
    try:
        _git(["add",
              f"results/{suite_result.project}/",
              f"wiki/projects/{suite_result.project}.md",
              "projects/"], cwd=root)
        _git(["commit", "-m", msg], cwd=root)
        _git(["push"], cwd=root)
        return {"status": "ok", "msg": f"Pushed: {msg}"}
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode()
        if "nothing to commit" in stderr:
            return {"status": "ok", "msg": "Nothing to commit"}
        return {"status": "error", "msg": stderr[:300]}


def _git(args, cwd):
    return subprocess.run(
        ["git"] + args, cwd=str(cwd), capture_output=True, check=True
    ).stdout.decode()
