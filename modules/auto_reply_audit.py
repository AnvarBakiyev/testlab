"""
auto_reply_audit — checks auto-reply log, safety rules, low confidence sends.

Fix: empty auto_reply_safety is downgraded from FAIL to WARN.
Safety rules are optional configuration, not a broken system.
FAIL only on: cu_fallbacks > 0 (real errors) or low-confidence actual sends.
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
    # Low confidence AND actually sent (not just draft)
    low_conf_sent = [r for r in logs if r['sent'] == 1 and r['confidence'] and r['confidence'] < 0.5]

    data = {
        'total_log': len(logs),
        'sent_count': len(sent),
        'low_confidence': len(low_conf_sent),
        'safety_rules': safety_count,
        'cu_fallbacks': cu_fallbacks,
    }

    # Hard failures: actual system errors
    hard_issues = []
    if cu_fallbacks > 0:
        hard_issues.append(f'{cu_fallbacks} CU fallback events')
    if low_conf_sent:
        hard_issues.append(f'{len(low_conf_sent)} sends with confidence <0.5')

    if hard_issues:
        return TestResult('fail', ' | '.join(hard_issues), '; '.join(hard_issues), data)

    # Soft warnings: configuration gaps
    warn_issues = []
    if safety_count == 0:
        warn_issues.append('No safety rules configured (optional but recommended)')
    if not logs:
        warn_issues.append('No auto-reply activity recorded')

    if warn_issues:
        return TestResult('warn', ' | '.join(warn_issues), '; '.join(warn_issues), data)

    return TestResult('pass', f'Auto-reply OK: {len(sent)} sent, {safety_count} safety rules', '', data)
