"""
auto_reply_audit — checks auto-reply log, safety rules, low confidence sends.
"""
import sqlite3
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/auto_reply.db'

def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    logs = conn.execute(
        "SELECT sent, confidence, channel, sender, timestamp FROM auto_reply_log ORDER BY timestamp DESC LIMIT 100"
    ).fetchall()
    safety_count = conn.execute("SELECT COUNT(*) FROM auto_reply_safety").fetchone()[0]
    cu_fallbacks = conn.execute("SELECT COUNT(*) FROM cu_fallback_log").fetchone()[0]
    conn.close()

    sent = [r for r in logs if r['sent'] == 1]
    low_conf = [r for r in logs if r['confidence'] and r['confidence'] < 0.5]

    data = {
        'total_log': len(logs),
        'sent_count': len(sent),
        'low_confidence': len(low_conf),
        'safety_rules': safety_count,
        'cu_fallbacks': cu_fallbacks,
    }

    issues = []
    if safety_count == 0:
        issues.append('No safety rules configured')
    if cu_fallbacks > 0:
        issues.append(f'{cu_fallbacks} CU fallback events')
    if low_conf:
        issues.append(f'{len(low_conf)} sends with confidence <0.5')
    if not logs:
        issues.append('No auto-reply activity recorded')

    if 'No safety rules' in ' '.join(issues) or cu_fallbacks > 0:
        return TestResult('fail', ' | '.join(issues), '; '.join(issues), data)
    if issues:
        return TestResult('warn', ' | '.join(issues), '; '.join(issues), data)
    return TestResult('pass', f'Auto-reply OK: {len(sent)} sent, {safety_count} safety rules', '', data)
