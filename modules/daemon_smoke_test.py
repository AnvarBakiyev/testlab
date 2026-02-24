"""daemon_smoke_test — functional smoke test for agi_daemon module graph.

Two checks:
1. Static: AST scan for functions called in each module but not imported.
2. Runtime: actually import all modules and verify key symbols exist.
"""
import ast
import os
import subprocess
import sys
from core.base import TestResult

APPS_DIR = '/Users/anvarbakiyev/dronor/apps'

CORE_MODULES = [
    'telegram_bot.py',
    'agi_daemon.py',
    'daily_tasks.py',
    'event_collectors.py',
    'action_executor.py',
    'cars_engine.py',
    'daemon_config.py',
]

RUNTIME_SCRIPT = '''
import sys
sys.path.insert(0, '.')
errors = []

try:
    import daemon_config; daemon_config.load_config()
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
    for sym in ['claude_calls_this_hour', 'claude_calls_hour_start',
                'reason_about_batch', 'process_telegram_callbacks',
                'is_quiet_hours']:
        assert hasattr(tb, sym), f'missing {sym}'
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


def _static_audit() -> list[str]:
    """Return list of 'module: missing_name' strings."""
    # Build map: function_name -> source_module
    all_funcs = {}
    for fname in os.listdir(APPS_DIR):
        if not fname.endswith('.py') or fname.startswith('agi_daemon') or fname.startswith('.'):
            continue
        try:
            code = open(os.path.join(APPS_DIR, fname)).read()
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.col_offset == 0 and not node.name.startswith('_'):
                        all_funcs[node.name] = fname
        except Exception:
            pass

    issues = []
    for target in CORE_MODULES:
        fpath = os.path.join(APPS_DIR, target)
        if not os.path.exists(fpath):
            continue
        code = open(fpath).read()
        tree = ast.parse(code)

        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for a in node.names: imported.add(a.asname or a.name)
            if isinstance(node, ast.Import):
                for a in node.names: imported.add(a.asname or a.name.split('.')[0])
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.col_offset == 0: imported.add(node.name)
            if isinstance(node, ast.Assign) and getattr(node, 'col_offset', 99) == 0:
                for t in node.targets:
                    if isinstance(t, ast.Name): imported.add(t.id)

        used_calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                used_calls.add(node.func.id)

        for name in sorted(used_calls):
            if name not in imported and name in all_funcs:
                issues.append(f'{target}: calls {name!r} (defined in {all_funcs[name]}) but not imported')

    return issues


def run(config: dict) -> TestResult:
    # 1. Static audit
    static_issues = _static_audit()
    if static_issues:
        detail = '\n'.join(static_issues)
        return TestResult('fail', f'Static audit: {len(static_issues)} missing import(s)', detail)

    # 2. Runtime check
    result = subprocess.run(
        [sys.executable, '-c', RUNTIME_SCRIPT],
        capture_output=True, text=True, cwd=APPS_DIR, timeout=30,
    )
    if result.returncode == 0:
        return TestResult('pass', 'All daemon modules smoke-test passed', '')

    error_text = (result.stdout + result.stderr).strip()
    first_line = error_text.splitlines()[0] if error_text else 'unknown'
    return TestResult('fail', f'Runtime smoke failed: {first_line}', error_text)
