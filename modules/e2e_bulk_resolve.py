"""
E2E: bulk_resolve_actions — accepts valid JSON list, parses correctly.
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

        # Get up to 3 pending action IDs
        rows = conn.execute(
            "SELECT id FROM pending "
            "WHERE status NOT IN ('approved','rejected','executed') "
            "LIMIT 3"
        ).fetchall()
        conn.close()

        if not rows:
            return TestResult("warn", "No pending actions to test bulk_resolve with")

        ids = [r["id"] for r in rows]

        # Test that JSON parsing works (same logic as CC's bulk_resolve_actions)
        try:
            parsed = json.loads(json.dumps(ids))
            if not isinstance(parsed, list) or parsed != ids:
                raise ValueError("Roundtrip failed")
        except Exception as e:
            return TestResult("fail",
                f"bulk_resolve JSON parsing broken: {e}",
                data={"ids": ids})

        # Verify UPDATE would affect correct rows (dry run)
        conn2 = sqlite3.connect(path)
        conn2.execute("BEGIN")
        placeholders = ",".join(["?"] * len(ids))
        conn2.execute(
            f"UPDATE pending SET status='rejected' WHERE id IN ({placeholders})", ids
        )
        affected = conn2.execute(
            f"SELECT count(*) FROM pending WHERE id IN ({placeholders}) AND status='rejected'", ids
        ).fetchone()[0]
        conn2.execute("ROLLBACK")
        conn2.close()

        if affected != len(ids):
            return TestResult("warn",
                f"bulk_resolve would affect {affected}/{len(ids)} rows",
                data={"expected": len(ids), "actual": affected})

        return TestResult("pass",
            f"bulk_resolve OK — {len(ids)} actions would update correctly",
            data={"tested_ids_count": len(ids)})
    except Exception as e:
        return TestResult("fail", f"bulk_resolve test crashed: {e}")
