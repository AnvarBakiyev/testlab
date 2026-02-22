"""
Audit: Events pipeline health.
Checks for stuck unprocessed events, error rate, stale events, throughput.
"""
from dataclasses import dataclass
from typing import Any
import sqlite3
from datetime import datetime, timezone
from collections import Counter

@dataclass
class ModuleResult:
    status: str
    msg: str
    details: Any = None

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/events.db'

def run(config: dict) -> ModuleResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Unprocessed events
    unprocessed = conn.execute("""
        SELECT id, source, event_type, created_at, status
        FROM events
        WHERE status IN ('pending', 'new', NULL)
           OR processed_at IS NULL
        ORDER BY created_at
        LIMIT 100
    """).fetchall()

    # Error events
    errors = conn.execute("""
        SELECT id, source, event_type, created_at, status
        FROM events
        WHERE status = 'error'
        ORDER BY created_at DESC
        LIMIT 50
    """).fetchall()

    # Volume last 24h
    recent = conn.execute("""
        SELECT source, event_type, status, created_at
        FROM events
        WHERE created_at > datetime('now', '-24 hours')
    """).fetchall()

    # Oldest unprocessed
    oldest_unprocessed = conn.execute("""
        SELECT created_at FROM events
        WHERE processed_at IS NULL
        ORDER BY created_at LIMIT 1
    """).fetchone()

    # Status breakdown total
    status_counts = dict(conn.execute(
        "SELECT status, COUNT(*) FROM events GROUP BY status"
    ).fetchall())

    conn.close()

    now = datetime.now(timezone.utc)
    issues = []

    # Check for stuck events
    stuck_old = []
    for r in unprocessed:
        try:
            ts = r['created_at'].replace('Z', '+00:00')
            created = datetime.fromisoformat(ts)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_h = (now - created).total_seconds() / 3600
            if age_h > 1:
                stuck_old.append({'id': r['id'], 'source': r['source'],
                                  'event_type': r['event_type'],
                                  'age_hours': round(age_h, 1)})
        except:
            pass

    if stuck_old:
        issues.append(f'{len(stuck_old)} unprocessed events older than 1h')
    if errors:
        issues.append(f'{len(errors)} events in error status')

    by_source = Counter(r['source'] for r in recent)
    by_type = Counter(r['event_type'] for r in recent)

    details = {
        'total_events': sum(status_counts.values()),
        'status_breakdown': status_counts,
        'recent_24h': len(recent),
        'recent_by_source': dict(by_source.most_common()),
        'recent_by_type': dict(by_type.most_common(10)),
        'unprocessed_count': len(unprocessed),
        'stuck_older_than_1h': len(stuck_old),
        'error_count': len(errors),
        'examples_stuck': stuck_old[:5],
        'examples_errors': [dict(e) for e in errors[:3]],
    }

    if issues:
        return ModuleResult('fail', ' | '.join(issues), details)
    return ModuleResult('pass', f'Pipeline healthy: {len(recent)} events/24h, 0 stuck', details)
