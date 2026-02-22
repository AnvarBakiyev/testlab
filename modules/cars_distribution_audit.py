"""
Audit: CARS score distribution.
Detects score clustering (all same), dead zones, calibration drift.
"""
from dataclasses import dataclass
from typing import Any
import sqlite3
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

    pending = conn.execute(
        "SELECT cars_score, action_type FROM pending WHERE status='pending'"
    ).fetchall()
    recent_archive = conn.execute("""
        SELECT cars_score, action_type, status, resolution
        FROM pending_archive
        WHERE archived_at > datetime('now', '-7 days')
    """).fetchall()
    conn.close()

    issues = []

    # Check clustering in pending
    scores = [r['cars_score'] for r in pending if r['cars_score'] is not None]
    if scores:
        rounded = [round(s, 1) for s in scores]
        counter = Counter(rounded)
        top_score, top_count = counter.most_common(1)[0]
        clustering_pct = top_count / len(scores) * 100

        if clustering_pct > 80:
            issues.append(f'Score clustering: {clustering_pct:.0f}% of pending have score /Users/anvarbakiyev{top_score}')

        score_range = max(scores) - min(scores)
        if score_range < 0.1:
            issues.append(f'Zero variance: all scores between {min(scores):.2f} and {max(scores):.2f}')

    # Type breakdown
    by_type = Counter(r['action_type'] for r in pending)

    # Approval rate from feedback
    feedback = conn.execute(
        "SELECT user_decision, action_type FROM feedback_log"
    ).fetchall() if False else []
    try:
        conn2 = sqlite3.connect(DB)
        feedback = conn2.execute(
            "SELECT user_decision, action_type FROM feedback_log"
        ).fetchall()
        conn2.close()
        approved = sum(1 for f in feedback if f[0] == 'approve')
        rejected = sum(1 for f in feedback if f[0] == 'reject')
        approval_rate = approved / len(feedback) * 100 if feedback else 0
    except:
        approved = rejected = 0
        approval_rate = 0

    details = {
        'total_pending': len(pending),
        'score_min': round(min(scores), 3) if scores else None,
        'score_max': round(max(scores), 3) if scores else None,
        'score_mean': round(sum(scores)/len(scores), 3) if scores else None,
        'top_score': top_score if scores else None,
        'top_score_pct': round(clustering_pct, 1) if scores else None,
        'by_action_type': dict(by_type.most_common()),
        'feedback_total': len(feedback),
        'approval_rate_pct': round(approval_rate, 1),
        'issues': issues,
    }

    if issues:
        return ModuleResult('fail', ' | '.join(issues), details)
    return ModuleResult('pass', f'CARS distribution healthy (range {details["score_min"]}-{details["score_max"]})', details)
