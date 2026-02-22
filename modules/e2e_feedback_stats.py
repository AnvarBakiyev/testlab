"""
E2E: Feedback stats screen — feedback_log table exists and returns data.
"""
import os
import sqlite3

AGI_BASE = os.path.expanduser("/Users/anvarbakiyev/dronor/local_data/personal_agi")

def run(cfg: dict):
    from core.base import TestResult
    try:
        path = os.path.join(AGI_BASE, "pending_actions.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row

        # Check table exists
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        if "feedback_log" not in tables:
            conn.close()
            return TestResult("fail", "feedback_log table missing — CARS feedback broken",
                              detail="Table must exist for get_feedback_stats() to work")

        total = conn.execute("SELECT count(*) FROM feedback_log").fetchone()[0]
        correct = conn.execute(
            "SELECT count(*) FROM feedback_log WHERE was_correct=1"
        ).fetchone()[0]
        conn.close()

        accuracy = round(correct / total * 100, 1) if total > 0 else None

        if total == 0:
            return TestResult("warn", "feedback_log is empty — no CARS feedback recorded yet",
                              data={"total": 0})

        if accuracy is not None and accuracy < 50:
            return TestResult("warn",
                f"CARS accuracy low: {accuracy}% ({correct}/{total})",
                data={"total": total, "correct": correct, "accuracy_pct": accuracy})

        return TestResult("pass",
            f"Feedback stats OK — {total} entries, {accuracy}% accurate",
            data={"total": total, "correct": correct, "accuracy_pct": accuracy})
    except Exception as e:
        return TestResult("fail", f"Feedback stats crashed: {e}")
