"""
kg_freshness - checks last update_kg decision timestamp.
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from core.base import TestResult

DEFAULT_DB = "/Users/anvarbakiyev/dronor/local_data/personal_agi/daemon_state.db"


def run(config: dict) -> TestResult:
    path = Path(config.get("db_path", DEFAULT_DB))
    warn_days = int(config.get("warn_days", 3))
    fail_days = int(config.get("fail_days", 7))
    if not path.exists():
        return TestResult(status="fail", msg=f"DB not found: {path}", detail="", data={})
    conn = sqlite3.connect(str(path))
    row = conn.execute(
        "SELECT timestamp FROM daemon_decisions WHERE action_type=\'update_kg\' ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return TestResult(status="fail", msg="No update_kg decisions found - KG never updated", detail="", data={})
    now = datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (now - dt).days
    except Exception as e:
        return TestResult(status="warn", msg=f"Cannot parse last KG update date: {e}", detail="", data={})
    data_out = {"last_update_at": row[0], "age_days": age}
    if age >= fail_days:
        return TestResult(
            status="fail",
            msg=f"KG not updated for {age} days (threshold {fail_days}d)",
            detail=f"Last: {row[0]}",
            data=data_out
        )
    if age >= warn_days:
        return TestResult(
            status="warn",
            msg=f"KG last updated {age} days ago (warn threshold {warn_days}d)",
            detail=f"Last: {row[0]}",
            data=data_out
        )
    return TestResult(status="pass", msg=f"KG freshness OK - updated {age} day(s) ago", detail="", data=data_out)
