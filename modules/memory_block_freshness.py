"""
memory_block_freshness — checks updated_at per block in core_memory.json.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from core.base import TestResult

DEFAULT_PATH = "/Users/anvarbakiyev/dronor/local_data/personal_agi/core_memory.json"

def run(config: dict) -> TestResult:
    path = Path(config.get("memory_path", DEFAULT_PATH))
    warn_days = int(config.get("warn_days", 7))
    fail_days = int(config.get("fail_days", 21))
    if not path.exists():
        return TestResult(status="fail", msg=f"Not found: {path}", detail="", data={})
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return TestResult(status="fail", msg=f"Parse error: {e}", detail="", data={})
    now = datetime.now(timezone.utc)
    blocks = data.get("blocks", {})
    stale, results = [], {}
    for bname, block in blocks.items():
        if not isinstance(block, dict): continue
        upd = block.get("updated_at", "")
        if not upd:
            stale.append({"block": bname, "days": None, "reason": "no updated_at"})
            continue
        try:
            dt = datetime.fromisoformat(upd.replace("Z", "+00:00"))
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            age = (now - dt).days
            results[bname] = age
            if age >= fail_days: stale.append({"block": bname, "days": age, "reason": f">{fail_days}d"})
            elif age >= warn_days: stale.append({"block": bname, "days": age, "reason": f">{warn_days}d"})
        except Exception as e:
            stale.append({"block": bname, "days": None, "reason": str(e)})
    data_out = {"blocks": results, "stale": stale}
    fails = [s for s in stale if s.get("days") and s["days"] >= fail_days]
    warns = [s for s in stale if s not in fails]
    if fails:
        names = [f"{s['block']} ({s['days']}d)" for s in fails]
        return TestResult(status="fail", msg=f"{len(fails)} block(s) not updated for >{fail_days} days", detail=", ".join(names), data=data_out)
    if warns:
        names = [f"{s['block']} ({s.get('days','?')}d)" for s in warns]
        return TestResult(status="warn", msg=f"{len(warns)} block(s) older than {warn_days} days", detail=", ".join(names), data=data_out)
    return TestResult(status="pass", msg=f"All {len(results)} blocks fresh (within {warn_days}d)", detail="", data=data_out)
