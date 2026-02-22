"""
Audit: Pending Actions - age analysis.
Detects actions stuck >24h, >72h, >7d without resolution.
"""
from dataclasses import dataclass
from typing import Any
import sqlite3
from datetime import datetime, timezone

@dataclass
class ModuleResult:
    status: str
    msg: str
    details: Any = None

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> ModuleResult:
    warn_hours = config.get('warn_hours', 24)
    fail_hours = config.get('fail_hours', 72)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, action_type, description, cars_score, created_at, params
        FROM pending WHERE status = 'pending'
        ORDER BY created_at
    """).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    stale_warn, stale_fail, stale_week = [], [], []

    for r in rows:
        try:
            ts = r['created_at'].replace('Z', '+00:00') if r['created_at'] else None
            if not ts:
                continue
            created = datetime.fromisoformat(ts)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_h = (now - created).total_seconds() / 3600
            entry = {'id': r['id'], 'action_type': r['action_type'],
                     'age_hours': round(age_h, 1), 'description': r['description'][:80]}
            if age_h > 168:
                stale_week.append(entry)
            elif age_h > fail_hours:
                stale_fail.append(entry)
            elif age_h > warn_hours:
                stale_warn.append(entry)
        except Exception:
            pass

    details = {
        'total_pending': len(rows),
        'older_than_24h': len(stale_warn) + len(stale_fail) + len(stale_week),
        'older_than_72h': len(stale_fail) + len(stale_week),
        'older_than_7d': len(stale_week),
        'examples_72h': stale_fail[:5],
        'examples_7d': stale_week[:5],
    }

    if stale_week:
        return ModuleResult('fail', f"{len(stale_week)} actions older than 7 days, {len(stale_fail)} older than 72h", details)
    if stale_fail:
        return ModuleResult('fail', f"{len(stale_fail)} actions older than {fail_hours}h without resolution", details)
    if stale_warn:
        return ModuleResult('warn', f"{len(stale_warn)} actions older than {warn_hours}h", details)
    return ModuleResult('pass', f'All {len(rows)} pending actions are fresh (<{warn_hours}h)', details)
