"""
modules/telegram_callback_check.py — Validate Telegram callback buttons.

Checks that all PENDING actions that have telegram_message_id
(i.e. were sent to user with approve/reject buttons) are still valid:
- action still exists in DB
- action id is a valid string (won't break callback routing)
- no pending actions are stale (sitting for too long without resolution)

No real Telegram call — purely DB validation.

Config:
  pending_db_path: str     — absolute path to pending_actions.db
  id_pattern: str          — regex the action id must match
  max_pending_age_hours: int — warn if pending older than N hours (default 72)
"""
import sqlite3
import re
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base import TestResult

DEFAULT_ID_PATTERN = r'^[a-zA-Z0-9_\-]+$'


def run(config: dict) -> TestResult:
    db_path = config.get('pending_db_path', '')
    id_pattern = config.get('id_pattern', DEFAULT_ID_PATTERN)
    max_age_hours = config.get('max_pending_age_hours', 72)

    if not db_path or not Path(db_path).exists():
        return TestResult(status='fail', msg=f'pending_actions.db not found: {db_path}')

    try:
        conn = sqlite3.connect(db_path)
        with_tg = conn.execute(
            "SELECT id, created_at, telegram_message_id "
            "FROM pending "
            "WHERE status='PENDING' AND telegram_message_id IS NOT NULL "
            "ORDER BY created_at DESC"
        ).fetchall()
        total_pending = conn.execute(
            "SELECT COUNT(*) FROM pending WHERE status='PENDING'"
        ).fetchone()[0]
        conn.close()
    except Exception as e:
        return TestResult(status='fail', msg=f'DB error: {e}')

    notified = len(with_tg)
    not_notified = total_pending - notified
    now = datetime.now()
    invalid_ids = []
    stale_actions = []

    for row in with_tg:
        action_id, created_at, tg_msg_id = row
        if not re.match(id_pattern, str(action_id)):
            invalid_ids.append(action_id)
        try:
            created_dt = datetime.fromisoformat(created_at.replace('Z', ''))
            age_hours = (now - created_dt).total_seconds() / 3600
            if age_hours > max_age_hours:
                stale_actions.append((str(action_id)[:20], f'{age_hours:.0f}h'))
        except Exception:
            pass

    data = {
        'total_pending': total_pending,
        'notified_via_telegram': notified,
        'not_notified': not_notified,
        'invalid_ids': len(invalid_ids),
        'stale_actions': len(stale_actions),
    }

    if invalid_ids:
        return TestResult(
            status='fail',
            msg=f'{len(invalid_ids)} invalid action ids (broken callbacks)',
            detail=str(invalid_ids[:3]),
            data=data,
        )
    if stale_actions:
        return TestResult(
            status='warn',
            msg=f'{len(stale_actions)} stale pending (>{max_age_hours}h) | {notified} buttons valid',
            detail=str(stale_actions[:3]),
            data=data,
        )
    if total_pending == 0:
        return TestResult(status='pass', msg='No pending actions (system idle)', data=data)

    return TestResult(
        status='pass',
        msg=f'{notified} Telegram buttons valid | {not_notified} pending without TG message',
        data=data,
    )
