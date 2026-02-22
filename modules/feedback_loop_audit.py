"""
feedback_loop_audit — checks CARS learning: feedback volume, recency, was_correct population.
"""
import sqlite3
from collections import Counter
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    feedback = conn.execute("SELECT * FROM feedback_log ORDER BY created_at DESC").fetchall()
    recent = conn.execute(
        "SELECT user_decision FROM feedback_log WHERE created_at > datetime('now', '-7 days')"
    ).fetchall()
    without_correct = conn.execute(
        "SELECT COUNT(*) FROM feedback_log WHERE was_correct IS NULL"
    ).fetchone()[0]
    conn.close()

    decisions = Counter(r['user_decision'] for r in feedback)
    approval_rate = round(decisions.get('approve', 0) / len(feedback) * 100, 1) if feedback else 0

    data = {
        'total_feedback': len(feedback),
        'recent_7d': len(recent),
        'decision_breakdown': dict(decisions),
        'without_correctness': without_correct,
        'approval_rate_pct': approval_rate,
    }

    issues = []
    if not feedback:
        return TestResult('fail', 'No feedback recorded — CARS cannot learn', '', data)
    if not recent:
        issues.append('No feedback in last 7 days')
    if without_correct > len(feedback) * 0.5:
        issues.append(f'{without_correct} entries missing was_correct field')

    if issues:
        return TestResult('warn', ' | '.join(issues), '; '.join(issues), data)
    return TestResult('pass', f'Feedback active: {len(feedback)} total, {len(recent)} in last 7d, {approval_rate}% approval', '', data)
