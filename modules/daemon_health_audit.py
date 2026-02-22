"""
daemon_health_audit — run frequency, error rate, DLQ, last run recency.
"""
import sqlite3
from datetime import datetime, timezone
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/daemon_state.db'

def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    last_run = conn.execute(
        "SELECT started_at, errors FROM daemon_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    total_24h = conn.execute(
        "SELECT COUNT(*) FROM daemon_runs WHERE started_at > datetime('now', '-24 hours')"
    ).fetchone()[0]
    error_24h = conn.execute(
        "SELECT COUNT(*) FROM daemon_runs WHERE started_at > datetime('now', '-24 hours') AND errors > 0"
    ).fetchone()[0]
    dlq = conn.execute("SELECT COUNT(*) FROM dead_letter_queue").fetchone()[0]
    decisions_24h = conn.execute(
        "SELECT action_type, COUNT(*) as cnt FROM daemon_decisions "
        "WHERE timestamp > datetime('now', '-24 hours') GROUP BY action_type ORDER BY cnt DESC"
    ).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    last_run_age_min = None
    if last_run:
        try:
            ts = last_run['started_at'].replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            last_run_age_min = round((now - dt).total_seconds() / 60, 1)
        except Exception:
            pass

    error_rate = round(error_24h / total_24h * 100, 1) if total_24h > 0 else 0

    data = {
        'runs_24h': total_24h,
        'error_rate_pct': error_rate,
        'last_run_age_min': last_run_age_min,
        'dead_letter_queue': dlq,
        'decisions_24h': {r['action_type']: r['cnt'] for r in decisions_24h},
    }

    issues = []
    if last_run_age_min and last_run_age_min > 10:
        issues.append(f'Last run {last_run_age_min}min ago (expected <5min)')
    if error_rate > 20:
        issues.append(f'Error rate {error_rate}% in last 24h')
    if dlq > 0:
        issues.append(f'{dlq} events in dead letter queue')
    if total_24h < 50:
        issues.append(f'Only {total_24h} runs in 24h (expected /Users/anvarbakiyev288)')

    if issues:
        return TestResult('fail', ' | '.join(issues), '; '.join(issues), data)
    return TestResult('pass', f'Daemon healthy: {total_24h} runs/24h, last {last_run_age_min}min ago, {error_rate}% errors', '', data)
