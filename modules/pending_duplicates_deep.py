"""
Audit: Pending Actions — duplicate detection.
Checks for actions with same sender+action_type in pending table.
Also detects same source_event_id appearing multiple times.
"""
from dataclasses import dataclass, field
from typing import Any
import sqlite3, json
from pathlib import Path
from collections import defaultdict

@dataclass
class ModuleResult:
    status: str
    msg: str
    details: Any = None

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'

def run(config: dict) -> ModuleResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT id, action_type, description, cars_score, created_at,
               source_event_id, params, status
        FROM pending
        WHERE status = 'pending'
        ORDER BY created_at
    """).fetchall()
    conn.close()

    # Group by (action_type + sender extracted from params/description)
    sender_groups = defaultdict(list)
    event_groups = defaultdict(list)

    for r in rows:
        # Extract sender from params JSON
        sender = 'unknown'
        try:
            p = json.loads(r['params'] or '{}')
            sender = p.get('sender') or p.get('from') or p.get('to') or p.get('chat_id', 'unknown')
        except:
            pass

        key = f"{r['action_type']}::{sender}"
        sender_groups[key].append(dict(r))

        if r['source_event_id']:
            event_groups[r['source_event_id']].append(dict(r))

    # Find duplicates
    sender_dupes = {k: v for k, v in sender_groups.items() if len(v) > 1}
    event_dupes = {k: v for k, v in event_groups.items() if len(v) > 1}

    total_dupes = sum(len(v) - 1 for v in sender_dupes.values())
    total_event_dupes = sum(len(v) - 1 for v in event_dupes.values())

    details = {
        'total_pending': len(rows),
        'sender_duplicate_groups': len(sender_dupes),
        'extra_actions_from_sender_dupes': total_dupes,
        'event_id_duplicate_groups': len(event_dupes),
        'examples': []
    }

    for key, items in list(sender_dupes.items())[:5]:
        details['examples'].append({
            'key': key,
            'count': len(items),
            'ids': [i['id'] for i in items],
            'descriptions': [i['description'][:80] for i in items]
        })

    total = total_dupes + total_event_dupes
    if total > 10:
        return ModuleResult('fail', f'{total_dupes} duplicate actions by sender, {total_event_dupes} by event_id', details)
    if total > 0:
        return ModuleResult('warn', f'{total_dupes} duplicate actions by sender, {total_event_dupes} by event_id', details)
    return ModuleResult('pass', f'No duplicates in {len(rows)} pending actions', details)
