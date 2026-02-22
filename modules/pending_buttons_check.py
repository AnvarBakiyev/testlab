"""
pending_buttons_check — validates Telegram button text and callback_data limits.
"""
import sqlite3, json
from pathlib import Path
from core.base import TestResult

DEFAULT_DB = "/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db"

def run(config: dict) -> TestResult:
    path = Path(config.get("db_path", DEFAULT_DB))
    max_btn = int(config.get("max_button_text", 20))
    max_cb = int(config.get("max_callback_bytes", 64))
    sample = int(config.get("sample_size", 30))
    if not path.exists():
        return TestResult(status="fail", msg=f"DB not found: {path}", detail="", data={})
    conn = sqlite3.connect(str(path))
    rows = conn.execute("SELECT id, action_type, params FROM pending WHERE status='PENDING' ORDER BY rowid DESC LIMIT ?", (sample,)).fetchall()
    conn.close()
    issues, with_buttons = [], 0
    for rid, atype, params_str in rows:
        if not params_str: continue
        try: params = json.loads(params_str)
        except Exception: continue
        buttons = params.get("reply_markup", {}) or params.get("buttons", [])
        if not buttons: continue
        with_buttons += 1
        inline = buttons.get("inline_keyboard", []) if isinstance(buttons, dict) else buttons
        for row_btns in inline:
            if not isinstance(row_btns, list): row_btns = [row_btns]
            for btn in row_btns:
                if not isinstance(btn, dict): continue
                text = btn.get("text", "")
                cb = btn.get("callback_data", "")
                found = []
                if len(text) > max_btn: found.append(f"text too long: {len(text)} chars")
                if len(cb.encode("utf-8")) > max_cb: found.append(f"callback_data too long: {len(cb.encode('utf-8'))}b")
                if found: issues.append({"id": rid[:8], "type": atype, "problems": found})
    data_out = {"checked": len(rows), "with_buttons": with_buttons, "issues": len(issues), "details": issues[:5]}
    if len(issues) > 3:
        return TestResult(status="fail", msg=f"{len(issues)} button violations in {with_buttons} actions", detail=str([i['problems'] for i in issues[:2]]), data=data_out)
    if issues:
        return TestResult(status="warn", msg=f"{len(issues)} button(s) exceed Telegram limits", detail=str([i['problems'] for i in issues[:2]]), data=data_out)
    return TestResult(status="pass", msg=f"{with_buttons} actions with buttons — all within limits", detail="", data=data_out)
