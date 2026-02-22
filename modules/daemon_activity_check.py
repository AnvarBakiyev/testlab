"""
daemon_activity_check - verifies the AGI daemon is alive and actively making decisions.

Checks:
1. Last decision timestamp (daemon may be frozen)
2. Decision rate (decisions per hour, sudden drops = processing stuck)
3. Error rate in recent decisions (high errors = systemic problem)
"""
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from core.base import TestResult

DEFAULT_DB = "/Users/anvarbakiyev/dronor/local_data/personal_agi/daemon_state.db"


def run(config: dict) -> TestResult:
    db_path = Path(config.get("db_path", DEFAULT_DB))
    max_silence_minutes = config.get("max_silence_minutes", 30)
    min_decisions_per_hour = config.get("min_decisions_per_hour", 2)
    max_error_rate = config.get("max_error_rate", 0.5)

    if not db_path.exists():
        return TestResult(status="fail", msg="daemon_state.db not found", detail="", data={})

    conn = sqlite3.connect(str(db_path))
    try:
        # Last decision timestamp
        row = conn.execute(
            "SELECT timestamp FROM daemon_decisions ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

        if not row:
            return TestResult(status="fail", msg="No decisions in daemon_state.db", detail="Daemon may never have run", data={})

        last_ts_str = row[0]
        try:
            last_ts = datetime.fromisoformat(last_ts_str.replace("Z", "+00:00"))
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
        except Exception:
            return TestResult(status="warn", msg=f"Cannot parse last decision timestamp: {last_ts_str}", detail="", data={})

        now = datetime.now(timezone.utc)
        silence_minutes = (now - last_ts).total_seconds() / 60

        # Decision rate in last hour
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        count_1h = conn.execute(
            "SELECT COUNT(*) FROM daemon_decisions WHERE timestamp > ?",
            (one_hour_ago,)
        ).fetchone()[0]

        # Error rate in last 50 decisions
        recent = conn.execute(
            "SELECT result FROM daemon_decisions ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        import json
        error_count = 0
        for r in recent:
            try:
                res = json.loads(r[0]) if r[0] else {}
                if isinstance(res, dict) and res.get("status") == "error":
                    error_count += 1
            except Exception:
                pass
        error_rate = error_count / len(recent) if recent else 0

        data = {
            "last_decision": last_ts_str,
            "silence_minutes": round(silence_minutes, 1),
            "decisions_last_hour": count_1h,
            "error_rate_50": round(error_rate, 2),
            "error_count_50": error_count
        }

        # Check silence
        if silence_minutes > max_silence_minutes:
            return TestResult(
                status="fail",
                msg=f"Daemon silent for {silence_minutes:.0f} minutes (max {max_silence_minutes})",
                detail=f"Last decision: {last_ts_str}",
                data=data
            )

        # Check decision rate
        if count_1h < min_decisions_per_hour:
            return TestResult(
                status="warn",
                msg=f"Low decision rate: {count_1h} decisions in last hour (min {min_decisions_per_hour})",
                detail="Daemon may be stuck or sleeping",
                data=data
            )

        # Check error rate
        if error_rate > max_error_rate:
            return TestResult(
                status="warn",
                msg=f"High error rate in recent decisions: {error_rate:.0%} ({error_count}/50)",
                detail="Many actions failing",
                data=data
            )

        return TestResult(
            status="pass",
            msg=f"Daemon active: {count_1h} decisions/hour, last {silence_minutes:.0f}min ago",
            detail="",
            data=data
        )
    finally:
        conn.close()
