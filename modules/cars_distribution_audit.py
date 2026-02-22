"""
cars_distribution_audit — CARS score clustering and variance check.
"""
import sqlite3
from collections import Counter
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    pending = conn.execute(
        "SELECT cars_score, action_type FROM pending WHERE status='pending'"
    ).fetchall()
    feedback = conn.execute(
        "SELECT user_decision FROM feedback_log"
    ).fetchall()
    conn.close()

    scores = [r['cars_score'] for r in pending if r['cars_score'] is not None]
    by_type = dict(Counter(r['action_type'] for r in pending).most_common())
    approved = sum(1 for f in feedback if f['user_decision'] == 'approve')
    approval_rate = round(approved / len(feedback) * 100, 1) if feedback else 0

    issues = []
    clustering_pct = 0
    top_score = None

    if scores:
        rounded = [round(s, 1) for s in scores]
        counter = Counter(rounded)
        top_score, top_count = counter.most_common(1)[0]
        clustering_pct = round(top_count / len(scores) * 100, 1)
        score_range = max(scores) - min(scores)
        if clustering_pct > 80:
            issues.append(f'{clustering_pct}% of scores cluster around {top_score}')
        if score_range < 0.1:
            issues.append(f'Zero variance: {min(scores):.3f}–{max(scores):.3f}')

    data = {
        'total_pending': len(pending),
        'score_min': round(min(scores), 3) if scores else None,
        'score_max': round(max(scores), 3) if scores else None,
        'score_mean': round(sum(scores)/len(scores), 3) if scores else None,
        'top_score_pct': clustering_pct,
        'feedback_total': len(feedback),
        'approval_rate_pct': approval_rate,
        'by_action_type': by_type,
    }

    if issues:
        return TestResult('fail', ' | '.join(issues), ', '.join(issues), data)
    return TestResult('pass', f'CARS healthy: range {data["score_min"]}–{data["score_max"]}, {approval_rate}% approval', '', data)
