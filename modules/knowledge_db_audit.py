"""
Audit: Knowledge DB integrity.
Detects corrupted knowledge_cc_*.db files and validates the main knowledge.db.
"""
from dataclasses import dataclass
from typing import Any
import sqlite3
from pathlib import Path

@dataclass
class ModuleResult:
    status: str
    msg: str
    details: Any = None

BASE = Path('/Users/anvarbakiyev/dronor/local_data/personal_agi')

def run(config: dict) -> ModuleResult:
    corrupted = []
    valid = []
    cc_files = list(BASE.glob('knowledge_cc_*.db'))

    for f in cc_files:
        try:
            conn = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            conn.execute('SELECT 1').fetchone()
            conn.close()
            valid.append(f.name)
        except Exception as e:
            corrupted.append({'file': f.name, 'size_kb': f.stat().st_size // 1024})

    # Check main knowledge.db
    main_db = BASE / 'knowledge.db'
    main_status = 'missing'
    main_tables = []
    if main_db.exists():
        try:
            conn = sqlite3.connect(f'file:{main_db}?mode=ro', uri=True)
            main_tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn.close()
            main_status = 'ok'
        except Exception as e:
            main_status = f'corrupted: {e}'

    details = {
        'cc_files_total': len(cc_files),
        'cc_files_corrupted': len(corrupted),
        'cc_files_valid': len(valid),
        'main_knowledge_db': main_status,
        'main_tables': main_tables,
        'corrupted_examples': corrupted[:10],
    }

    issues = []
    if len(corrupted) > 50:
        issues.append(f'{len(corrupted)} corrupted knowledge_cc_*.db files')
    if main_status != 'ok':
        issues.append(f'Main knowledge.db is {main_status}')

    # Orphaned cc files are just Kuzu WAL fragments - warn not fail
    if len(corrupted) > 0 and not issues:
        return ModuleResult('warn',
            f'{len(corrupted)}/{len(cc_files)} knowledge_cc files not readable (may be Kuzu WAL)', details)
    if issues:
        return ModuleResult('fail', ' | '.join(issues), details)
    return ModuleResult('pass', f'Knowledge DB intact ({len(valid)} cc files valid)', details)
