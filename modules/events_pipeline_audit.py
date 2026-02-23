"""
events_pipeline_audit — checks for stuck/error events and pipeline throughput.

Fix: events are marked done via status field ('processed','dismissed','noted').
processed_at IS NULL does NOT mean unprocessed — most events don't set processed_at.
Stuck events = status='pending' AND created_at is old.
"""
import sqlite3
from datetime import datetime, timezone
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/events.db'


def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # FIX: stuck = status is 'pending' (not yet handled) AND old
    stuck_rows = conn.execute(
        "SELECT id, source, event_type, created_at FROM events "
        "WHERE status = 'pending' "
        "AND created_at < datetime('now', '-1 hours') "
        "ORDER BY created_at LIMIT 100"
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

    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()

    now = datetime.now(timezone.utc)
    stuck = []
    for r in stuck_rows:
        try:
            ts = r['created_at'].replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_h = round((now - dt).total_seconds() / 3600)
            stuck.append(f"{r['id']} ({r['source']}/{r['event_type']}, {age_h}h)")
        except Exception:
            pass

    data = {
        'total_events': total_events,
        'status_breakdown': status_counts,
        'recent_24h': recent_24h,
        'unprocessed': len(stuck_rows),
        'stuck_over_1h': len(stuck),
        'error_count': errors,
    }

    issues = []
    if stuck:
        issues.append(f'{len(stuck)} events stuck in pending >1h')
    if errors:
        issues.append(f'{errors} events in error status')

    detail = '; '.join(stuck[:5])
    if issues:
        return TestResult('fail', ' | '.join(issues), detail, data)
    return TestResult('pass', f'Pipeline healthy: {recent_24h} events/24h, 0 stuck', '', data)
