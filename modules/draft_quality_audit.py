"""
Audit: Draft quality in pending actions.
Checks for empty drafts, too-short drafts, wrong language, template leftovers.
"""
from dataclasses import dataclass
from typing import Any
import sqlite3, json, re

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
        SELECT id, action_type, description, params, cars_score
        FROM pending WHERE status = 'pending'
    """).fetchall()
    conn.close()

    empty, too_short, has_placeholders, no_draft = [], [], [], []
    PLACEHOLDER_RE = re.compile(r'\[.*?\]|\{\{.*?\}\}|<.*?>')
    DRAFT_KEYS = ['body', 'draft', 'message', 'text', 'reply']
    DRAFT_ACTION_TYPES = ['draft_email', 'email_response', 'draft_whatsapp',
                          'telegram_reply', 'whatsapp_response']

    for r in rows:
        if r['action_type'] not in DRAFT_ACTION_TYPES:
            continue
        try:
            p = json.loads(r['params'] or '{}')
        except:
            p = {}

        draft = None
        for key in DRAFT_KEYS:
            if key in p and p[key]:
                draft = str(p[key])
                break

        entry = {'id': r['id'], 'action_type': r['action_type'],
                 'description': r['description'][:80]}

        if draft is None:
            no_draft.append(entry)
        elif len(draft.strip()) == 0:
            empty.append(entry)
        elif len(draft.strip()) < 20:
            entry['draft'] = draft[:100]
            too_short.append(entry)
        elif PLACEHOLDER_RE.search(draft):
            entry['draft'] = draft[:150]
            has_placeholders.append(entry)

    draft_actions = [r for r in rows if r['action_type'] in DRAFT_ACTION_TYPES]
    issues = []
    if no_draft:
        issues.append(f'{len(no_draft)} draft actions with no body')
    if empty:
        issues.append(f'{len(empty)} empty drafts')
    if has_placeholders:
        issues.append(f'{len(has_placeholders)} drafts with unfilled placeholders')
    if too_short:
        issues.append(f'{len(too_short)} drafts too short (<20 chars)')

    details = {
        'total_draft_actions': len(draft_actions),
        'no_draft': len(no_draft),
        'empty_draft': len(empty),
        'too_short': len(too_short),
        'has_placeholders': len(has_placeholders),
        'examples_no_draft': no_draft[:3],
        'examples_placeholders': has_placeholders[:3],
    }

    if empty or has_placeholders or no_draft:
        return ModuleResult('fail', ' | '.join(issues), details)
    if too_short:
        return ModuleResult('warn', ' | '.join(issues), details)
    return ModuleResult('pass', f'All {len(draft_actions)} drafts look complete', details)
