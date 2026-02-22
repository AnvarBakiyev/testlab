"""
E2E: Pending Actions screen — returns list, correct fields present.
"""
import os
import sqlite3
import json

AGI_BASE = os.path.expanduser("/Users/anvarbakiyev/dronor/local_data/personal_agi")

def run(cfg: dict):
    from core.base import TestResult
    try:
        path = os.path.join(AGI_BASE, "pending_actions.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, action_type, description, cars_score, status "
            "FROM pending WHERE status NOT IN ('approved','rejected','executed') "
            "ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
        conn.close()

        count = len(rows)
        missing_fields = []
        for r in rows[:10]:
            d = dict(r)
            for field in ["id", "action_type", "description", "cars_score"]:
                if d.get(field) is None:
                    missing_fields.append(f"{d.get('id','?')}.{field}")

        if missing_fields:
            return TestResult("warn",
                f"{count} pending actions, {len(missing_fields)} missing fields",
                detail="\n".join(missing_fields[:20]),
                data={"count": count, "missing": len(missing_fields)})

        return TestResult("pass",
            f"Pending screen OK — {count} actions loaded",
            data={"count": count})
    except Exception as e:
        return TestResult("fail", f"Pending screen crashed: {e}")
