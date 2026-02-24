"""daemon_smoke_test — functional smoke test for agi_daemon module graph.

Checks that all modules import cleanly AND their key symbols are accessible.
Catches NameError/AttributeError that static analysis misses (e.g. moved globals).
Runs in subprocess with cwd=apps/ to match real daemon startup environment.
"""
import subprocess
import sys
from core.base import TestResult

APPS_DIR = '/Users/anvarbakiyev/dronor/apps'

SMOKE_SCRIPT = '''
import sys
sys.path.insert(0, '.')
errors = []

try:
    import daemon_config
    daemon_config.load_config()
except Exception as e:
    errors.append(f'daemon_config: {e}')

try:
    from event_collectors import (
        collect_events, collect_postponed_actions, collect_pending_actions,
        collect_due_reminders, collect_upcoming_meetings, collect_meeting_prep,
        collect_calendar_conflicts, collect_deadline_alerts,
        collect_self_sent_emails, collect_unanswered_emails,
        collect_unanswered_vip_emails,
    )
except Exception as e:
    errors.append(f'event_collectors: {e}')

try:
    from action_executor import execute_action, log_decision, mark_events_processed, mark_reminders_done
except Exception as e:
    errors.append(f'action_executor: {e}')

try:
    import telegram_bot as tb
    assert hasattr(tb, 'claude_calls_this_hour')
    assert hasattr(tb, 'claude_calls_hour_start')
    assert hasattr(tb, 'reason_about_batch')
    assert hasattr(tb, 'process_telegram_callbacks')
except Exception as e:
    errors.append(f'telegram_bot: {e}')

try:
    from daily_tasks import run_morning_briefing, run_importance_recalc, check_backup_alert, update_wiki_status
except Exception as e:
    errors.append(f'daily_tasks: {e}')

try:
    import agi_daemon
except Exception as e:
    errors.append(f'agi_daemon: {e}')

if errors:
    for e in errors: print(e)
    sys.exit(1)
else:
    print('OK')
'''


def run(config: dict) -> TestResult:
    result = subprocess.run(
        [sys.executable, '-c', SMOKE_SCRIPT],
        capture_output=True,
        text=True,
        cwd=APPS_DIR,
        timeout=30,
    )
    if result.returncode == 0:
        return TestResult('pass', 'All daemon modules smoke-test passed', '')

    error_text = (result.stdout + result.stderr).strip()
    first_line = error_text.splitlines()[0] if error_text else 'unknown'
    return TestResult(
        'fail',
        f'Daemon smoke failed: {first_line}',
        error_text,
    )
