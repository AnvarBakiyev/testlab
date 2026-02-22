"""
pending_orphans_audit — data integrity: wrong status, id overlap with archive, missing description.
"""
import sqlite3
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    wrong_status = conn.execute(
        "SELECT id, status, action_type FROM pending WHERE status != 'pending'"
    ).fetchall()
    id_overlap = conn.execute(
        "SELECT p.id FROM pending p INNER JOIN pending_archive pa ON p.id = pa.id"
    ).fetchall()
    no_description = conn.execute(
        "SELECT id, action_type FROM pending WHERE (description IS NULL OR description = '') AND status = 'pending'"
    ).fetchall()
    status_breakdown = dict(conn.execute(
        "SELECT status, COUNT(*) FROM pending GROUP BY status"
    ).fetchall())
    conn.close()

    data = {
        'status_breakdown': status_breakdown,
        'wrong_status_count': len(wrong_status),
        'id_overlap_count': len(id_overlap),
        'no_description_count': len(no_description),
    }

    issues = []
    if id_overlap:
        issues.append(f'{len(id_overlap)} IDs in both pending and archive')
    if wrong_status:
        issues.append(f'{len(wrong_status)} rows with non-pending status')
    if no_description:
        issues.append(f'{len(no_description)} actions missing description')

    detail = '; '.join(issues)
    if id_overlap:
        return TestResult('fail', ' | '.join(issues), detail, data)
    if issues:
        return TestResult('warn', ' | '.join(issues), detail, data)
    return TestResult('pass', 'No orphaned actions, data integrity OK', '', data)
