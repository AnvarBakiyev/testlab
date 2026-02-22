"""
Audit: Auto-reply system health.
Checks reply log, safety rules, fallback rate.
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

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/auto_reply.db'

def run(config: dict) -> ModuleResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    logs = conn.execute(
        "SELECT * FROM auto_reply_log ORDER BY timestamp DESC LIMIT 100"
    ).fetchall()

    safety_rules = conn.execute(
        "SELECT COUNT(*) FROM auto_reply_safety"
    ).fetchone()[0]

    cu_fallbacks = conn.execute(
        "SELECT COUNT(*) FROM cu_fallback_log"
    ).fetchone()[0]

    conn.close()

    issues = []
    sent = [r for r in logs if r['sent'] == 1]
    failed = [r for r in logs if r['sent'] == 0]
    low_confidence = [r for r in logs if r['confidence'] and r['confidence'] < 0.5]

    if len(logs) == 0:
        issues.append('No auto-reply activity recorded (system may not be running)')
    if low_confidence:
        issues.append(f'{len(low_confidence)} replies sent with confidence < 0.5')
    if cu_fallbacks > 0:
        issues.append(f'{cu_fallbacks} CU fallback events (API failures)')
    if safety_rules == 0:
        issues.append('No safety rules configured for auto-reply')

    details = {
        'total_log_entries': len(logs),
        'sent_count': len(sent),
        'failed_count': len(failed),
        'low_confidence_count': len(low_confidence),
        'safety_rules_count': safety_rules,
        'cu_fallback_count': cu_fallbacks,
        'recent_examples': [{
            'channel': r['channel'],
            'sender': r['sender'],
            'confidence': r['confidence'],
            'sent': r['sent'],
            'timestamp': r['timestamp']
        } for r in logs[:5]],
    }

    if [i for i in issues if 'not be running' in i or 'confidence' in i]:
        return ModuleResult('warn', ' | '.join(issues), details)
    if issues:
        return ModuleResult('fail', ' | '.join(issues), details)
    return ModuleResult('pass',
        f'Auto-reply healthy: {len(sent)} sent, {safety_rules} safety rules', details)
