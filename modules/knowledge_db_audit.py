"""
knowledge_db_audit — validates main knowledge.db (Kuzu) and cc shard files.

Fix: knowledge.db is a Kuzu database, NOT SQLite.
Kuzu requires subprocess + os._exit(0) pattern (WAL safety).
cc shard files (knowledge_cc_*.db) are SQLite — checked directly.
"""
import sqlite3
import subprocess
import sys
import json
import tempfile
import os
from pathlib import Path
from core.base import TestResult

BASE = Path('/Users/anvarbakiyev/dronor/local_data/personal_agi')

# NOTE: {{ and }} are escaped braces for str.format()
KUZU_CHECK_SCRIPT = '''
import kuzu, os, sys, json
try:
    db = kuzu.Database("{kg_path}", read_only=True)
    conn = kuzu.Connection(db)
    r = conn.execute("MATCH (p:Person) RETURN count(p) AS cnt")
    person_count = r.get_next()[0] if r.has_next() else 0
    r2 = conn.execute("MATCH (o:Organization) RETURN count(o) AS cnt")
    org_count = r2.get_next()[0] if r2.has_next() else 0
    print(json.dumps({{"status": "ok", "persons": person_count, "orgs": org_count}}))
except Exception as e:
    print(json.dumps({{"status": "error", "error": str(e)}}))
sys.stdout.flush()
os._exit(0)
'''


def run(config: dict) -> TestResult:
    # Check SQLite cc shards
    cc_files = list(BASE.glob('knowledge_cc_*.db'))
    corrupted = []
    for f in cc_files:
        try:
            conn = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            conn.execute('SELECT 1').fetchone()
            conn.close()
        except Exception:
            corrupted.append(f.name)

    # Check main Kuzu DB via subprocess
    main_db = BASE / 'knowledge.db'
    main_status = 'missing'
    kuzu_data = {}

    if main_db.exists():
        script_content = KUZU_CHECK_SCRIPT.format(kg_path=str(main_db))
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp')
        tf.write(script_content)
        tf.close()
        try:
            proc = subprocess.run(
                [sys.executable, tf.name],
                capture_output=True, text=True, timeout=30
            )
            os.unlink(tf.name)
            if proc.stdout.strip():
                result = json.loads(proc.stdout.strip())
                if result.get('status') == 'ok':
                    main_status = 'ok'
                    kuzu_data = result
                else:
                    main_status = f"error: {result.get('error', 'unknown')}"
            else:
                main_status = f'no output (stderr: {proc.stderr[:100]})'
        except Exception as e:
            main_status = f'subprocess error: {e}'

    data = {
        'cc_total': len(cc_files),
        'cc_corrupted': len(corrupted),
        'main_db_status': main_status,
        'kuzu_persons': kuzu_data.get('persons', 0),
        'kuzu_orgs': kuzu_data.get('orgs', 0),
    }

    if main_status != 'ok':
        return TestResult('fail', f'knowledge.db is {main_status}', f'{len(corrupted)}/{len(cc_files)} cc shards unreadable', data)
    if len(corrupted) > 50:
        return TestResult('fail', f'{len(corrupted)} corrupted cc shard files', '', data)
    if corrupted:
        return TestResult('warn', f'{len(corrupted)}/{len(cc_files)} cc shards unreadable (may be Kuzu WAL)', '', data)
    return TestResult('pass', f'Knowledge DB intact: {kuzu_data.get("persons", 0)} persons, {len(cc_files)} shards OK', '', data)
