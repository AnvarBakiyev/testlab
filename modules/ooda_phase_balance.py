"""
OODA Phase Balance Check

Checks that the daemon's COLLECT phase (events) is proportional
to its DECIDE/ACT phase (actions + proposals).

Fix: events_processed in daemon_runs counts connector checks, not
just actionable events. We only FAIL if claude_calls > 0 but
actions == 0 consistently (LLM ran but produced nothing).
This avoids false positives when events are low-priority dismissals.
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
        return TestResult(
            module='ooda_phase_balance',
            status='fail',
            msg=f'daemon_state.db not found: {db_path}',
        )

    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT events_processed, actions_taken, actions_proposed, claude_calls "
            "FROM daemon_runs "
            "ORDER BY started_at DESC LIMIT ?",
            (lookback_runs,)
        ).fetchall()
        conn.close()
    except Exception as e:
        return TestResult(module='ooda_phase_balance', status='fail', msg=f'DB error: {e}')

    if not rows:
        return TestResult(
            module='ooda_phase_balance',
            status='warn',
            msg='No daemon runs found in database',
        )

    total_events = sum(r[0] for r in rows)
    total_actions = sum(r[1] + r[2] for r in rows)
    total_claude_calls = sum(r[3] for r in rows)
    runs_with_events = sum(1 for r in rows if r[0] > 0)
    runs_with_actions = sum(1 for r in rows if r[1] + r[2] > 0)
    # Runs where LLM was called but produced zero actions
    runs_llm_no_action = sum(1 for r in rows if r[3] > 0 and r[1] + r[2] == 0)
    runs_with_llm = sum(1 for r in rows if r[3] > 0)

    if total_events == 0:
        return TestResult(
            module='ooda_phase_balance',
            status='pass',
            msg=f'No events in last {len(rows)} runs (system idle)',
        )

    detail = (
        f"Last {len(rows)} runs: {total_events} events in, "
        f"{total_actions} actions out | "
        f"{runs_with_events} runs had events, {runs_with_actions} produced actions | "
        f"{total_claude_calls} LLM calls, {runs_llm_no_action} LLM-but-no-action runs"
    )

    # REAL FAILURE: LLM was called but consistently produced no actions
    # This means Orient/Decide is broken, not just quiet
    if runs_with_llm > 5 and runs_llm_no_action == runs_with_llm:
        return TestResult(
            module='ooda_phase_balance',
            status='fail',
            msg=f'{runs_with_llm} LLM calls with ZERO actions — Decide phase broken?',
            detail=detail,
        )

    # Warning: many events but no actions and no LLM calls
    # Could mean events are all being dismissed before LLM stage
    ratio = total_actions / total_events if total_events > 0 else 0
    if ratio < min_action_ratio and runs_with_events > 10 and total_claude_calls == 0:
        return TestResult(
            module='ooda_phase_balance',
            status='warn',
            msg=f'Low action ratio: {ratio:.3f}, no LLM calls in {len(rows)} runs',
            detail=detail,
        )

    return TestResult(
        module='ooda_phase_balance',
        status='pass',
        msg=f'Balance OK: {total_events} events, {total_actions} actions, {total_claude_calls} LLM calls',
        detail=detail,
    )
