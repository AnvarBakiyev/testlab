"""
llm_ux_critic — uses Claude Haiku to review pending drafts for human-friendliness.
"""
import sqlite3, json, requests
from pathlib import Path
from core.base import TestResult

DEFAULT_DB = "/Users/anvarbakiyev/dronor/local_data/personal_agi/pending_actions.db"
DEFAULT_KEY = "/Users/anvarbakiyev/Desktop/credentials/claude_api_key.txt"
SYSTEM = """You are a strict UX critic for a Personal AI assistant that sends messages to a real user.
Review AI-generated draft messages and flag ones that sound robotic, confusing, or contain machine artifacts.
For each draft verdict: ok=natural, warn=minor issues, bad=machine-like/confusing/artifacts.
Respond ONLY with valid JSON: {"verdicts": [{"id": "...", "verdict": "ok|warn|bad", "reason": "one sentence"}], "summary": "one sentence"}"""

def run(config: dict) -> TestResult:
    db = Path(config.get("db_path", DEFAULT_DB))
    key_path = Path(config.get("api_key_file", DEFAULT_KEY))
    sample = int(config.get("sample_size", 5))
    model = config.get("model", "claude-haiku-4-5-20251001")
    fail_thr = float(config.get("fail_threshold", 0.5))
    warn_thr = float(config.get("warn_threshold", 0.25))
    if not db.exists():
        return TestResult(status="fail", msg=f"DB not found: {db}", detail="", data={})
    if not key_path.exists():
        return TestResult(status="fail", msg=f"API key not found: {key_path}", detail="", data={})
    api_key = key_path.read_text().strip()
    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT id, action_type, description FROM pending WHERE status='PENDING' ORDER BY rowid DESC LIMIT ?", (sample,)).fetchall()
    conn.close()
    if not rows:
        return TestResult(status="pass", msg="No pending actions to review", detail="", data={})
    drafts = [{"id": r[0][:8], "type": r[1], "text": (r[2] or "")[:300]} for r in rows]
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 1000, "system": SYSTEM, "messages": [{"role": "user", "content": f"Review {len(drafts)} drafts:\n{json.dumps(drafts, ensure_ascii=False)}"}]},
            timeout=30
        )
        raw = resp.json()["content"][0]["text"].strip()
        if raw.startswith("```"): raw = raw.split("```")[1]; raw = raw[4:] if raw.startswith("json") else raw
        result = json.loads(raw)
    except Exception as e:
        return TestResult(status="warn", msg=f"LLM API error: {e}", detail="", data={})
    verdicts = result.get("verdicts", [])
    summary = result.get("summary", "")
    bad = sum(1 for v in verdicts if v.get("verdict") == "bad")
    warn = sum(1 for v in verdicts if v.get("verdict") == "warn")
    total = len(verdicts)
    ratio = bad / total if total else 0
    data_out = {"checked": total, "bad": bad, "warn": warn, "ok": total-bad-warn, "summary": summary, "verdicts": verdicts}
    if ratio >= fail_thr:
        return TestResult(status="fail", msg=f"{bad}/{total} drafts are machine-like or confusing", detail=summary, data=data_out)
    if ratio >= warn_thr or warn > 0:
        return TestResult(status="warn", msg=f"{bad} bad, {warn} warn / {total} drafts reviewed", detail=summary, data=data_out)
    return TestResult(status="pass", msg=f"All {total} drafts sound natural", detail=summary, data=data_out)
