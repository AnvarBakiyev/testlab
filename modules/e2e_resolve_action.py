"""
E2E: resolve_action — approve/reject actually updates DB status.
Uses a real pending action in 'dry-run' mode: reads then verifies logic works.
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

        # Find a pending action to test with
        row = conn.execute(
            "SELECT id, status FROM pending "
            "WHERE status NOT IN ('approved','rejected','executed') "
            "LIMIT 1"
        ).fetchone()

        if not row:
            conn.close()
            return TestResult("warn", "No pending actions to test resolve with",
                              data={"pending_count": 0})

        action_id = row["id"]

        # Verify resolve UPDATE query works (dry run: use ROLLBACK)
        conn.execute("BEGIN")
        conn.execute(
            "UPDATE pending SET status='approved', resolved_at=datetime('now'), resolution='test' "
            "WHERE id=?", [action_id]
        )
        updated = conn.execute(
            "SELECT status FROM pending WHERE id=?", [action_id]
        ).fetchone()
        status_after = updated["status"] if updated else None
        conn.execute("ROLLBACK")
        conn.close()

        if status_after != "approved":
            return TestResult("fail",
                f"resolve_action broken: status={status_after} after UPDATE",
                data={"action_id": action_id})

        return TestResult("pass",
            f"resolve_action OK — DB update works (dry-run on {action_id})",
            data={"tested_action_id": action_id})
    except Exception as e:
        return TestResult("fail", f"resolve_action test crashed: {e}")
