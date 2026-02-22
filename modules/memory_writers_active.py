"""
memory_writers_active - checks if memory expert writers ran recently.
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from core.base import TestResult

DEFAULT_DB = "/Users/anvarbakiyev/dronor/local_data/personal_agi/daemon_state.db"
DEFAULT_EXPERTS = "memory_auto_manager,memory_updater,memory_learning_extractor,memory_reflection"


def run(config: dict) -> TestResult:
    path = Path(config.get("db_path", DEFAULT_DB))
    max_hours = int(config.get("max_hours", 48))
    experts = [e.strip() for e in config.get("memory_experts", DEFAULT_EXPERTS).split(",")]
    if not path.exists():
        return TestResult(status="fail", msg=f"DB not found: {path}", detail="", data={})
    threshold = (datetime.now(timezone.utc) - timedelta(hours=max_hours)).strftime("%Y-%m-%dT%H:%M:%S")
    conn = sqlite3.connect(str(path))
    found = {}
    for exp in experts:
        row = conn.execute(
            "SELECT timestamp FROM daemon_decisions WHERE description LIKE ? AND timestamp > ? ORDER BY rowid DESC LIMIT 1",
            (f"%{exp}%", threshold)
        ).fetchone()
        if row:
            found[exp] = row[0]
    conn.close()
    missing = [e for e in experts if e not in found]
    data_out = {"experts": experts, "found": found, "missing": missing, "hours": max_hours}
    if len(missing) == len(experts):
        return TestResult(
            status="fail",
            msg=f"NO memory experts ran in last {max_hours}h - memory frozen",
            detail="Missing: " + ", ".join(missing),
            data=data_out
        )
    if missing:
        return TestResult(
            status="warn",
            msg=f"{len(missing)}/{len(experts)} memory writers inactive in last {max_hours}h",
            detail="Missing: " + ", ".join(missing),
            data=data_out
        )
    return TestResult(
        status="pass",
        msg=f"All {len(experts)} memory writers active within {max_hours}h",
        detail="",
        data=data_out
    )
