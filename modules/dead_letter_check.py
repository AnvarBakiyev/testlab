"""
Dead Letter Queue Check — TestLab Phase 1

Counts failed/lost events in dead_letter_queue table.
Daemon writes here when reason_about_batch returns None
or when an event cannot be processed.
"""
import sqlite3
from pathlib import Path
sys_import = __import__('sys')
sys_import.path.insert(0, str(Path(__file__).parent.parent))
from core.base import TestResult


def run(config: dict) -> TestResult:
    db_path = config.get('state_db_path', '')
    window_hours = config.get('window_hours', 24)
    max_allowed = config.get('max_allowed', 5)

    if not db_path or not Path(db_path).exists():
        return TestResult(module='dead_letter_check',
            status='fail',
            msg=f'daemon_state.db not found: {db_path}',
        )

    try:
        conn = sqlite3.connect(db_path)

        # Check if table exists (daemon may not have run with Phase 1 yet)
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dead_letter_queue'"
        ).fetchone()

        if not table_exists:
            conn.close()
            return TestResult(module='dead_letter_check',
                status='warn',
                msg='dead_letter_queue table missing — restart daemon to apply Phase 1',
            )

        count = conn.execute(
            "SELECT COUNT(*) FROM dead_letter_queue "
            "WHERE created_at >= datetime('now', ? || ' hours')",
            (f'-{window_hours}',)
        ).fetchone()[0]

        # Get last few entries for context
        recent = conn.execute(
            "SELECT stage, reason, created_at FROM dead_letter_queue "
            "ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        conn.close()

    except Exception as e:
        return TestResult(module='dead_letter_check', status='fail', msg=f'DB error: {e}')

    detail = None
    if recent:
        detail = ' | '.join(f"{r[0]}: {r[1][:60]}" for r in recent)

    if count == 0:
        return TestResult(module='dead_letter_check',
            status='pass',
            msg=f'No lost events in last {window_hours}h',
        )
    elif count <= max_allowed:
        return TestResult(module='dead_letter_check',
            status='warn',
            msg=f'{count} lost events in last {window_hours}h (max {max_allowed})',
            detail=detail,
        )
    else:
        return TestResult(module='dead_letter_check',
            status='fail',
            msg=f'{count} lost events in last {window_hours}h — pipeline losing data',
            detail=detail,
        )
