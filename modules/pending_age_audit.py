"""
pending_age_audit — detects stale pending actions older than warn/fail thresholds.
"""
import sqlite3
from datetime import datetime, timezone
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> TestResult:
    warn_hours = int(config.get('warn_hours', 24))
    fail_hours = int(config.get('fail_hours', 72))

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, action_type, description, created_at FROM pending WHERE status = 'pending'"
    ).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    stale_fail, stale_warn, stale_week = [], [], []
    for r in rows:
        try:
            ts = r['created_at'].replace('Z', '+00:00')
            created = datetime.fromisoformat(ts)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_h = (now - created).total_seconds() / 3600
            entry = f"{r['id']} ({r['action_type']}, {round(age_h)}h)"
            if age_h > 168:
                stale_week.append(entry)
            elif age_h > fail_hours:
                stale_fail.append(entry)
            elif age_h > warn_hours:
                stale_warn.append(entry)
        except Exception:
            pass

    data = {
        'total_pending': len(rows),
        'older_than_24h': len(stale_warn) + len(stale_fail) + len(stale_week),
        'older_than_72h': len(stale_fail) + len(stale_week),
        'older_than_7d': len(stale_week),
    }

    if stale_week:
        detail = '; '.join(stale_week[:5])
        return TestResult('fail', f'{len(stale_week)} actions older than 7 days', detail, data)
    if stale_fail:
        detail = '; '.join(stale_fail[:5])
        return TestResult('fail', f'{len(stale_fail)} actions older than {fail_hours}h', detail, data)
    if stale_warn:
        detail = '; '.join(stale_warn[:5])
        return TestResult('warn', f'{len(stale_warn)} actions older than {warn_hours}h', detail, data)
    return TestResult('pass', f'All {len(rows)} pending actions fresh (<{warn_hours}h)', '', data)
