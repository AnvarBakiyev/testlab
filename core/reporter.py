import json
from datetime import datetime, timezone
from pathlib import Path

TESTLAB_ROOT = Path(__file__).parent.parent
S = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}

def save_json(suite_result, testlab_root=None):
    root = testlab_root or TESTLAB_ROOT
    results_dir = root / "results" / suite_result.project
    results_dir.mkdir(parents=True, exist_ok=True)
    data = suite_result.to_dict()
    data["saved_at"] = datetime.now(timezone.utc).isoformat()
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    timestamped = results_dir / (suite_result.suite_id + "_" + ts + ".json")
    latest = results_dir / (suite_result.suite_id + "_latest.json")
    for path in (timestamped, latest):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return latest

def to_telegram(suite_result):
    e = S[suite_result.status]
    lines = [
        e + " suite=" + suite_result.suite_name + " [" + suite_result.project + "]",
        suite_result.summary,
        "",
    ]
    for t in suite_result.tests:
        te = S[t.status]
        lines.append(te + " " + t.module + ": " + t.msg)
        if t.status == "fail" and t.detail:
            lines.append("  >> " + t.detail[:120])
    sep = chr(10)
    return sep.join(lines)

def to_wiki_row(suite_result):
    e = S[suite_result.status]
    ts = suite_result.finished_at[:16].replace("T", " ") if suite_result.finished_at else "-"
    return "| " + e + " " + suite_result.suite_name + " | " + suite_result.summary + " | " + ts + " |"
