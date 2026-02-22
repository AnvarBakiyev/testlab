"""
E2E: Activity Log screen — agi_daemon log file exists and has recent entries.
"""
import os
from pathlib import Path
from datetime import datetime, timedelta

AGI_BASE = os.path.expanduser("/Users/anvarbakiyev/dronor/local_data/personal_agi")

def run(cfg: dict):
    from core.base import TestResult
    try:
        # Look for daemon log files
        base = Path(AGI_BASE)
        log_candidates = list(base.glob("*.log")) + list(base.glob("*.jsonl"))
        log_candidates = [f for f in log_candidates if "daemon" in f.name.lower()
                          or "activity" in f.name.lower() or "agi" in f.name.lower()]

        if not log_candidates:
            return TestResult("warn",
                "No daemon log files found — activity log may be empty",
                detail=f"Searched in: {AGI_BASE}")

        newest = max(log_candidates, key=lambda f: f.stat().st_mtime)
        mtime = datetime.fromtimestamp(newest.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        size_kb = newest.stat().st_size // 1024

        if age_hours > 24:
            return TestResult("warn",
                f"Activity log stale: last update {age_hours:.0f}h ago",
                data={"log_file": newest.name, "age_hours": round(age_hours, 1),
                      "size_kb": size_kb})

        return TestResult("pass",
            f"Activity log OK — {newest.name}, {age_hours:.1f}h ago, {size_kb}KB",
            data={"log_file": newest.name, "age_hours": round(age_hours, 1),
                  "size_kb": size_kb})
    except Exception as e:
        return TestResult("fail", f"Activity log check crashed: {e}")
