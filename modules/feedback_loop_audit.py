"""
Audit: Feedback loop integrity.
Checks if user decisions are being recorded and CARS is learning from them.
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

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> ModuleResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    feedback = conn.execute(
        "SELECT * FROM feedback_log ORDER BY created_at DESC"
    ).fetchall()

    # Check if was_correct is being populated
    without_correctness = [r for r in feedback if r['was_correct'] is None]

    # Decision distribution
    decisions = Counter(r['user_decision'] for r in feedback)

    # Recent feedback (last 7 days)
    recent = conn.execute("""
        SELECT user_decision, was_correct, action_type, cars_score
        FROM feedback_log
        WHERE created_at > datetime('now', '-7 days')
    """).fetchall()

    # Check pending with no feedback ever
    archive_no_feedback = conn.execute("""
        SELECT COUNT(*) FROM pending_archive pa
        WHERE pa.status = 'approved'
        AND NOT EXISTS (
            SELECT 1 FROM feedback_log fl WHERE fl.action_id = pa.id
        )
        AND pa.archived_at > datetime('now', '-7 days')
    """).fetchone()[0]

    conn.close()

    issues = []

    if len(feedback) == 0:
        issues.append('No feedback recorded at all - CARS cannot learn')
    else:
        approve_rate = decisions.get('approve', 0) / len(feedback) * 100
        reject_rate = decisions.get('reject', 0) / len(feedback) * 100

        if len(recent) == 0:
            issues.append('No feedback in last 7 days - is user reviewing actions?')

        if len(without_correctness) > len(feedback) * 0.5:
            issues.append(f'{len(without_correctness)} feedback entries missing was_correct field')

    if archive_no_feedback > 20:
        issues.append(f'{archive_no_feedback} approved actions in last 7d with no feedback recorded')

    details = {
        'total_feedback': len(feedback),
        'recent_7d': len(recent),
        'decision_breakdown': dict(decisions),
        'without_correctness': len(without_correctness),
        'approved_without_feedback_7d': archive_no_feedback,
        'approve_rate_pct': round(decisions.get('approve', 0) / len(feedback) * 100, 1) if feedback else 0,
    }

    if issues:
        sev = 'fail' if 'cannot learn' in ' '.join(issues) else 'warn'
        return ModuleResult(sev, ' | '.join(issues), details)
    return ModuleResult('pass',
        f'Feedback loop active: {len(feedback)} total, {len(recent)} in last 7d', details)
