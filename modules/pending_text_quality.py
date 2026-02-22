"""
pending_text_quality - checks pending_actions description for text artifacts.
"""
import sqlite3
import re
from pathlib import Path
from core.base import TestResult

DEFAULT_DB = "/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db"

PATTERNS = [
    (r"execution_log|expert_name|Kwargs:", "internal log"),
    (r"<[a-z]+>.*?</[a-z]+>", "HTML tags"),
]


def run(config: dict) -> TestResult:
    path = Path(config.get("db_path", DEFAULT_DB))
    max_len = int(config.get("max_length", 800))
    sample = int(config.get("sample_size", 20))
    if not path.exists():
        return TestResult(status="fail", msg=f"DB not found: {path}", detail="", data={})
    conn = sqlite3.connect(str(path))
    rows = conn.execute(
        "SELECT id, action_type, description FROM pending WHERE status=\'PENDING\' ORDER BY rowid DESC LIMIT ?",
        (sample,)
    ).fetchall()
    conn.close()
    if not rows:
        return TestResult(status="pass", msg="No pending actions to check", detail="", data={})
    issues = []
    for rid, atype, desc in rows:
        text = desc or ""
        found = []
        if len(text) > max_len:
            found.append(f"too long ({len(text)} chars)")
        for pat, label in PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                found.append(label)
        if found:
            issues.append({"id": rid[:8], "type": atype, "problems": found})
    total = len(issues)
    data_out = {"checked": len(rows), "issues": total, "details": issues[:5]}
    if total > len(rows) // 2:
        return TestResult(
            status="fail",
            msg=f"{total}/{len(rows)} pending actions have text issues",
            detail=str([i["problems"] for i in issues[:2]]),
            data=data_out
        )
    if total > 0:
        return TestResult(
            status="warn",
            msg=f"{total} issue(s) in {len(rows)} pending actions",
            detail=str([i["problems"] for i in issues[:2]]),
            data=data_out
        )
    return TestResult(status="pass", msg=f"All {len(rows)} descriptions clean", detail="", data=data_out)
