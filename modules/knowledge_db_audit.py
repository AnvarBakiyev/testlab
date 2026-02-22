"""
knowledge_db_audit — validates main knowledge.db and counts corrupted cc shard files.
"""
import sqlite3
from pathlib import Path
from core.base import TestResult

BASE = Path('/Users/anvarbakiyev/dronor/local_data/personal_agi')

def run(config: dict) -> TestResult:
    cc_files = list(BASE.glob('knowledge_cc_*.db'))
    corrupted = []
    for f in cc_files:
        try:
            conn = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            conn.execute('SELECT 1').fetchone()
            conn.close()
        except Exception:
            corrupted.append(f.name)

    main_db = BASE / 'knowledge.db'
    main_status = 'missing'
    main_tables = []
    if main_db.exists():
        try:
            conn = sqlite3.connect(f'file:{main_db}?mode=ro', uri=True)
            main_tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            conn.close()
            main_status = 'ok'
        except Exception as e:
            main_status = f'corrupted: {e}'

    data = {
        'cc_total': len(cc_files),
        'cc_corrupted': len(corrupted),
        'main_db_status': main_status,
        'main_db_tables': main_tables,
    }

    if main_status != 'ok':
        return TestResult('fail', f'knowledge.db is {main_status}', f'{len(corrupted)}/{len(cc_files)} cc shards unreadable', data)
    if len(corrupted) > 50:
        return TestResult('fail', f'{len(corrupted)} corrupted cc shard files', '', data)
    if corrupted:
        return TestResult('warn', f'{len(corrupted)}/{len(cc_files)} cc shards unreadable (may be Kuzu WAL)', '', data)
    return TestResult('pass', f'Knowledge DB intact, {len(cc_files)} shards OK', '', data)
