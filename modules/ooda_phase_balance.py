"""
OODA Phase Balance Check — TestLab Phase 1

Checks that the daemon's COLLECT phase (events) is proportional
to its DECIDE/ACT phase (actions + proposals).

If we have many events but zero actions across multiple runs,
something is silently broken in Orient or Decide phases.
"""
import sqlite3
from pathlib import Path
sys_import = __import__('sys')
sys_import.path.insert(0, str(Path(__file__).parent.parent))
from core.base import TestResult


def run(config: dict) -> TestResult:
    db_path = config.get('state_db_path', '')
    lookback_runs = config.get('lookback_runs', 20)
    min_action_ratio = config.get('min_action_ratio', 0.01)

    if not db_path or not Path(db_path).exists():
        return TestResult(module='ooda_phase_balance',
            status='fail',
            msg=f'daemon_state.db not found: {db_path}',
        )

    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT events_processed, actions_taken, actions_proposed "
            "FROM daemon_runs "
            "ORDER BY started_at DESC LIMIT ?",
            (lookback_runs,)
        ).fetchall()
        conn.close()
    except Exception as e:
        return TestResult(module='ooda_phase_balance', status='fail', msg=f'DB error: {e}')

    if not rows:
        return TestResult(module='ooda_phase_balance',
            status='warn',
            msg='No daemon runs found in database',
        )

    total_events = sum(r[0] for r in rows)
    total_actions = sum(r[1] + r[2] for r in rows)  # taken + proposed
    runs_with_events = sum(1 for r in rows if r[0] > 0)
    runs_with_actions = sum(1 for r in rows if r[1] + r[2] > 0)

    # If no events at all, system is idle (not broken)
    if total_events == 0:
        return TestResult(module='ooda_phase_balance',
            status='pass',
            msg=f'No events in last {len(rows)} runs (system idle)',
        )

    ratio = total_actions / total_events if total_events > 0 else 0

    detail = (
        f"Last {len(rows)} runs: {total_events} events in, "
        f"{total_actions} actions out | "
        f"{runs_with_events} runs had events, {runs_with_actions} produced actions"
    )

    # Runs with events but zero actions across the board = suspicious
    if runs_with_events > 5 and runs_with_actions == 0:
        return TestResult(module='ooda_phase_balance',
            status='fail',
            msg=f'{runs_with_events} runs with events but ZERO actions — Orient/Decide broken?',
            detail=detail,
        )
    elif ratio < min_action_ratio and runs_with_events > 3:
        return TestResult(module='ooda_phase_balance',
            status='warn',
            msg=f'Low action ratio: {ratio:.3f} (min {min_action_ratio})',
            detail=detail,
        )
    else:
        return TestResult(module='ooda_phase_balance',
            status='pass',
            msg=f'Balance OK: {total_events} events → {total_actions} actions',
            detail=detail,
        )
