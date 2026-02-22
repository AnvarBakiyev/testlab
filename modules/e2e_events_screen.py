"""
E2E: Events screen — events.db readable, recent events present.
"""
import os
import sqlite3
from datetime import datetime, timedelta

AGI_BASE = os.path.expanduser("/Users/anvarbakiyev/dronor/local_data/personal_agi")

def run(cfg: dict):
    from core.base import TestResult
    try:
        path = os.path.join(AGI_BASE, "events.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row

        total = conn.execute("SELECT count(*) FROM events").fetchone()[0]
        cutoff = (datetime.now() - timedelta(hours=48)).isoformat()
        recent = conn.execute(
            "SELECT count(*) FROM events WHERE created_at > ?", [cutoff]
        ).fetchone()[0]

        error_count = 0
        try:
            error_count = conn.execute(
                "SELECT count(*) FROM events WHERE status='error'"
            ).fetchone()[0]
        except:
            pass
        conn.close()

        if total == 0:
            return TestResult("warn", "Events DB is empty", data={"total": 0})

        if recent == 0:
            return TestResult("warn",
                f"No events in last 48h (total: {total}) — pipeline may be stalled",
                data={"total": total, "recent_48h": 0})

        if error_count > 10:
            return TestResult("warn",
                f"{error_count} error events found",
                data={"total": total, "recent_48h": recent, "errors": error_count})

        return TestResult("pass",
            f"Events screen OK — {recent} recent, {total} total",
            data={"total": total, "recent_48h": recent, "errors": error_count})
    except Exception as e:
        return TestResult("fail", f"Events screen crashed: {e}")
