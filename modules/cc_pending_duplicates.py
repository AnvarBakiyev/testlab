"""
cc_pending_duplicates — detects duplicate draft cards per contact in pending_actions.
"""
import sqlite3, json
from pathlib import Path
from collections import defaultdict
from core.base import TestResult

DEFAULT_DB = "/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db"

def run(config: dict) -> TestResult:
    path = Path(config.get("db_path", DEFAULT_DB))
    max_per = int(config.get("max_per_contact", 2))
    sample = int(config.get("sample_size", 100))
    if not path.exists():
        return TestResult(status="fail", msg=f"DB not found: {path}", detail="", data={})
    conn = sqlite3.connect(str(path))
    rows = conn.execute("SELECT id, action_type, description, params FROM pending WHERE status='PENDING' ORDER BY rowid DESC LIMIT ?", (sample,)).fetchall()
    conn.close()
    groups = defaultdict(list)
    for rid, atype, desc, params_str in rows:
        contact = ""
        if params_str:
            try:
                p = json.loads(params_str)
                contact = p.get("contact_name") or p.get("recipient") or p.get("name") or ""
            except Exception: pass
        if not contact:
            contact = (desc or "").split()[0] if desc else "unknown"
        groups[(contact.strip().lower(), atype)].append(rid)
    dups = {k: v for k, v in groups.items() if len(v) > max_per}
    data_out = {"pending": len(rows), "dup_groups": len(dups), "details": [{"contact": k[0], "type": k[1], "count": len(v)} for k, v in list(dups.items())[:5]]}
    if len(dups) > 3:
        return TestResult(status="fail", msg=f"{len(dups)} contacts have >{max_per} identical pending actions", detail=str(data_out["details"][:2]), data=data_out)
    if dups:
        return TestResult(status="warn", msg=f"{len(dups)} duplicate group(s) found", detail=str(data_out["details"][:2]), data=data_out)
    return TestResult(status="pass", msg=f"All {len(rows)} pending actions are unique", detail="", data=data_out)
