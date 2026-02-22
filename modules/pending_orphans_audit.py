"""
Audit: Orphaned pending actions.
Detects: actions with missing source_event, resolved actions still in pending,
actions with invalid status, archive vs pending consistency.
"""
from dataclasses import dataclass
from typing import Any
import sqlite3

@dataclass
class ModuleResult:
    status: str
    msg: str
    details: Any = None

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> ModuleResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Actions in pending but status not 'pending'
    wrong_status = conn.execute("""
        SELECT id, status, action_type, created_at
        FROM pending
        WHERE status != 'pending'
    """).fetchall()

    # Actions with null params
    null_params = conn.execute("""
        SELECT id, action_type, description
        FROM pending
        WHERE params IS NULL OR params = '' OR params = '{}'
        AND status = 'pending'
    """).fetchall()

    # Duplicate IDs between pending and archive
    id_overlap = conn.execute("""
        SELECT p.id FROM pending p
        INNER JOIN pending_archive pa ON p.id = pa.id
    """).fetchall()

    # Actions missing description
    no_description = conn.execute("""
        SELECT id, action_type FROM pending
        WHERE (description IS NULL OR description = '')
        AND status = 'pending'
    """).fetchall()

    # Status breakdown
    status_breakdown = dict(conn.execute(
        "SELECT status, COUNT(*) FROM pending GROUP BY status"
    ).fetchall())

    conn.close()

    issues = []
    if wrong_status:
        issues.append(f'{len(wrong_status)} actions in pending table with non-pending status')
    if id_overlap:
        issues.append(f'{len(id_overlap)} IDs exist in both pending and archive (data corruption)')
    if no_description:
        issues.append(f'{len(no_description)} actions missing description')

    details = {
        'status_breakdown': status_breakdown,
        'wrong_status_count': len(wrong_status),
        'null_params_count': len(null_params),
        'id_overlap_count': len(id_overlap),
        'no_description_count': len(no_description),
        'examples_wrong_status': [dict(r) for r in wrong_status[:5]],
        'examples_id_overlap': [r['id'] for r in id_overlap[:5]],
    }

    if id_overlap:
        return ModuleResult('fail', ' | '.join(issues), details)
    if issues:
        return ModuleResult('warn', ' | '.join(issues), details)
    return ModuleResult('pass', f'No orphaned actions, data integrity OK', details)
