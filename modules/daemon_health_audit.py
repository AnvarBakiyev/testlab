"""
Audit: Daemon health - run frequency, error rate, throughput.
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

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/daemon_state.db'

def run(config: dict) -> ModuleResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Last 24h runs
    runs = conn.execute("""
        SELECT started_at, completed_at, events_processed,
               actions_taken, errors, claude_calls
        FROM daemon_runs
        WHERE started_at > datetime('now', '-24 hours')
        ORDER BY started_at DESC
    """).fetchall()

    # Last run
    last_run = conn.execute(
        "SELECT started_at, errors FROM daemon_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()

    # Error rate
    total_runs = conn.execute(
        "SELECT COUNT(*) FROM daemon_runs WHERE started_at > datetime('now', '-24 hours')"
    ).fetchone()[0]
    error_runs = conn.execute(
        """SELECT COUNT(*) FROM daemon_runs
           WHERE started_at > datetime('now', '-24 hours') AND errors > 0"""
    ).fetchone()[0]

    # Action type breakdown last 24h
    decisions = conn.execute("""
        SELECT action_type, COUNT(*) as cnt
        FROM daemon_decisions
        WHERE timestamp > datetime('now', '-24 hours')
        GROUP BY action_type
        ORDER BY cnt DESC
    """).fetchall()

    # Dead letter queue
    dlq = conn.execute("SELECT COUNT(*) FROM dead_letter_queue").fetchone()[0]

    conn.close()

    now = datetime.now(timezone.utc)
    issues = []

    # Check recency
    last_run_age_min = None
    if last_run:
        try:
            ts = last_run['started_at'].replace('Z', '+00:00')
            last_dt = datetime.fromisoformat(ts)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            last_run_age_min = round((now - last_dt).total_seconds() / 60, 1)
            if last_run_age_min > 10:
                issues.append(f'Daemon last run {last_run_age_min}min ago (expected <5min)')
        except:
            pass

    error_rate = error_runs / total_runs * 100 if total_runs > 0 else 0
    if error_rate > 20:
        issues.append(f'High error rate: {error_rate:.0f}% of runs have errors')

    if dlq > 0:
        issues.append(f'{dlq} events in dead letter queue')

    if total_runs < 50:
        issues.append(f'Only {total_runs} runs in last 24h (expected /Users/anvarbakiyev288 at 5min interval)')

    details = {
        'runs_24h': total_runs,
        'runs_with_errors': error_runs,
        'error_rate_pct': round(error_rate, 1),
        'last_run_age_min': last_run_age_min,
        'dead_letter_queue': dlq,
        'decisions_24h': {r['action_type']: r['cnt'] for r in decisions},
        'total_events_processed_24h': sum(r['events_processed'] or 0 for r in runs),
    }

    if issues:
        return ModuleResult('fail', ' | '.join(issues), details)
    return ModuleResult('pass',
        f'Daemon healthy: {total_runs} runs/24h, last {last_run_age_min}min ago', details)
