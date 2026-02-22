"""
cc_log_leakage - checks daemon_decisions.result for internal log leakage.
"""
import sqlite3
import re
from pathlib import Path
from core.base import TestResult

DEFAULT_DB = "/Users/anvarbakiyev/dronor/local_data/personal_agi/daemon_state.db"

LEAK_PATTERNS = [
    (r"execution_log", "execution_log key"),
    (r"expert_name", "expert_name key"),
    (r"Traceback \(most recent", "Python traceback"),
    (r"Zapusk eksperta", "internal runner log"),
]


def run(config: dict) -> TestResult:
    path = Path(config.get("db_path", DEFAULT_DB))
    sample = int(config.get("sample_size", 50))
    if not path.exists():
        return TestResult(status="fail", msg=f"DB not found: {path}", detail="", data={})
    conn = sqlite3.connect(str(path))
    rows = conn.execute(
        "SELECT id, action_type, result FROM daemon_decisions ORDER BY rowid DESC LIMIT ?",
        (sample,)
    ).fetchall()
    conn.close()
    leaks = []
    for rid, atype, result in rows:
        if not result:
            continue
        for pat, label in LEAK_PATTERNS:
            if re.search(pat, result):
                leaks.append(f"{rid[:8]} ({atype}): {label}")
                break
    total = len(leaks)
    data_out = {"checked": len(rows), "leaks": total, "examples": leaks[:3]}
    if total > 5:
        return TestResult(
            status="fail",
            msg=f"{total}/{len(rows)} decisions contain internal logs",
            detail="; ".join(leaks[:2]),
            data=data_out
        )
    if total > 0:
        return TestResult(
            status="warn",
            msg=f"{total} log leak(s) in last {len(rows)} decisions",
            detail="; ".join(leaks[:2]),
            data=data_out
        )
    return TestResult(status="pass", msg=f"All {len(rows)} decisions clean", detail="", data=data_out)
