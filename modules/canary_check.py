"""
Canary Check — TestLab Phase 1

Verifies that the daemon cycle completed recently by checking
the last canary_test event in events.db.

The daemon inserts a canary event (already-processed) at the end
of every cycle. If we don't see one recently, the cycle is stuck.
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
sys_import = __import__('sys')
sys_import.path.insert(0, str(Path(__file__).parent.parent))
from core.base import TestResult


def run(config: dict) -> TestResult:
    db_path = config.get('events_db_path', '')
    max_age_minutes = config.get('max_age_minutes', 15)

    if not db_path or not Path(db_path).exists():
        return TestResult(module='canary_check',
            status='fail',
            msg=f'events.db not found: {db_path}',
        )

    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT MAX(processed_at) FROM events WHERE event_type='canary_test'"
        ).fetchone()
        conn.close()
    except Exception as e:
        return TestResult(module='canary_check', status='fail', msg=f'DB error: {e}')

    last_canary = row[0] if row else None

    if not last_canary:
        return TestResult(module='canary_check',
            status='fail',
            msg='No canary events found — daemon has never run with Phase 1 changes',
        )

    try:
        last_dt = datetime.fromisoformat(last_canary)
    except ValueError:
        return TestResult(module='canary_check',
            status='fail',
            msg=f'Cannot parse canary timestamp: {last_canary}',
        )

    age = datetime.now() - last_dt
    age_minutes = age.total_seconds() / 60

    if age_minutes <= max_age_minutes:
        return TestResult(module='canary_check',
            status='pass',
            msg=f'Last cycle: {age_minutes:.1f} min ago',
        )
    elif age_minutes <= max_age_minutes * 3:
        return TestResult(module='canary_check',
            status='warn',
            msg=f'Cycle delayed: last canary {age_minutes:.1f} min ago (max {max_age_minutes})',
        )
    else:
        return TestResult(module='canary_check',
            status='fail',
            msg=f'Cycle STUCK: last canary {age_minutes:.1f} min ago (max {max_age_minutes})',
        )
