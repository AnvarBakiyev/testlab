"""
pending_duplicates_deep — duplicate action detection by sender+type and source_event_id.
"""
import sqlite3, json
from collections import defaultdict
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, action_type, description, params, source_event_id "
        "FROM pending WHERE status = 'pending'"
    ).fetchall()
    conn.close()

    sender_groups = defaultdict(list)
    event_groups = defaultdict(list)
    for r in rows:
        sender = 'unknown'
        try:
            p = json.loads(r['params'] or '{}')
            sender = p.get('sender') or p.get('from') or p.get('chat_id', 'unknown')
        except Exception:
            pass
        sender_groups[f"{r['action_type']}::{sender}"].append(dict(r))
        if r['source_event_id']:
            event_groups[r['source_event_id']].append(dict(r))

    sender_dupes = {k: v for k, v in sender_groups.items() if len(v) > 1}
    event_dupes  = {k: v for k, v in event_groups.items()  if len(v) > 1}
    n_sender = sum(len(v) - 1 for v in sender_dupes.values())
    n_event  = sum(len(v) - 1 for v in event_dupes.values())

    examples = []
    for key, items in list(sender_dupes.items())[:3]:
        examples.append(f"{key}: {[i['id'] for i in items]}")

    data = {
        'total_pending': len(rows),
        'sender_dupe_groups': len(sender_dupes),
        'event_dupe_groups': len(event_dupes),
        'extra_actions': n_sender + n_event,
    }
    detail = '; '.join(examples)

    total = n_sender + n_event
    if total > 10:
        return TestResult('fail', f'{n_sender} duplicate by sender, {n_event} by event_id', detail, data)
    if total > 0:
        return TestResult('warn', f'{n_sender} duplicate by sender, {n_event} by event_id', detail, data)
    return TestResult('pass', f'No duplicates in {len(rows)} pending actions', '', data)
