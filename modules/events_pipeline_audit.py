"""
events_pipeline_audit — checks for stuck/error events and pipeline throughput.
"""
import sqlite3
from datetime import datetime, timezone
from collections import Counter
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/events.db'

def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    unprocessed = conn.execute(
        "SELECT id, source, event_type, created_at FROM events "
        "WHERE processed_at IS NULL ORDER BY created_at LIMIT 100"
    ).fetchall()
    errors = conn.execute(
        "SELECT COUNT(*) FROM events WHERE status = 'error'"
    ).fetchone()[0]
    recent_24h = conn.execute(
        "SELECT COUNT(*) FROM events WHERE created_at > datetime('now', '-24 hours')"
    ).fetchone()[0]
    status_counts = dict(conn.execute(
        "SELECT status, COUNT(*) FROM events GROUP BY status"
    ).fetchall())
    conn.close()

    now = datetime.now(timezone.utc)
    stuck = []
    for r in unprocessed:
        try:
            ts = r['created_at'].replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if (now - dt).total_seconds() > 3600:
                stuck.append(f"{r['id']} ({r['source']}/{r['event_type']}, {round((now-dt).total_seconds()/3600)}h)")
        except Exception:
            pass

    data = {
        'total_events': sum(status_counts.values()),
        'status_breakdown': status_counts,
        'recent_24h': recent_24h,
        'unprocessed': len(unprocessed),
        'stuck_over_1h': len(stuck),
        'error_count': errors,
    }

    issues = []
    if stuck:   issues.append(f'{len(stuck)} events unprocessed >1h')
    if errors:  issues.append(f'{errors} events in error status')

    detail = '; '.join(stuck[:5])
    if issues:
        return TestResult('fail', ' | '.join(issues), detail, data)
    return TestResult('pass', f'Pipeline healthy: {recent_24h} events/24h, 0 stuck', '', data)
