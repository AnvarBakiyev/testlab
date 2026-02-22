"""
draft_quality_audit — checks draft actions for empty body, placeholders, too-short text.
"""
import sqlite3, json, re
from core.base import TestResult

DB = '/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db'
DRAFT_TYPES = {'draft_email', 'email_response', 'draft_whatsapp', 'telegram_reply', 'whatsapp_response'}
DRAFT_KEYS = ['body', 'draft', 'message', 'text', 'reply']
PLACEHOLDER_RE = re.compile(r'\[.*?\]|\{\{.*?\}\}')

def run(config: dict) -> TestResult:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, action_type, description, params FROM pending WHERE status = 'pending'"
    ).fetchall()
    conn.close()

    draft_rows = [r for r in rows if r['action_type'] in DRAFT_TYPES]
    no_body, empty, too_short, placeholders = [], [], [], []

    for r in draft_rows:
        try:
            p = json.loads(r['params'] or '{}')
        except Exception:
            p = {}
        draft = next((str(p[k]) for k in DRAFT_KEYS if k in p and p[k]), None)

        entry = f"{r['id']} ({r['action_type']})"
        if draft is None:
            no_body.append(entry)
        elif not draft.strip():
            empty.append(entry)
        elif len(draft.strip()) < 20:
            too_short.append(entry)
        elif PLACEHOLDER_RE.search(draft):
            placeholders.append(entry)

    data = {
        'total_draft_actions': len(draft_rows),
        'no_body': len(no_body),
        'empty': len(empty),
        'too_short': len(too_short),
        'placeholders': len(placeholders),
    }

    issues, crit = [], []
    if no_body:      crit.append(f'{len(no_body)} drafts with no body')
    if empty:        crit.append(f'{len(empty)} empty drafts')
    if placeholders: crit.append(f'{len(placeholders)} drafts with unfilled placeholders')
    if too_short:    issues.append(f'{len(too_short)} drafts too short (<20 chars)')

    all_issues = crit + issues
    detail = '; '.join(all_issues)
    if crit:
        return TestResult('fail', ' | '.join(crit), detail, data)
    if issues:
        return TestResult('warn', ' | '.join(issues), detail, data)
    return TestResult('pass', f'All {len(draft_rows)} drafts look complete', '', data)
