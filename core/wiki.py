from datetime import datetime
from pathlib import Path

TESTLAB_ROOT = Path(__file__).parent.parent
S = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}

def update_project_wiki(project_config, suite_results):
    pid = project_config["id"]
    pname = project_config["name"]
    wiki_dir = TESTLAB_ROOT / "wiki" / "projects"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    wiki_path = wiki_dir / (pid + ".md")
    lines = [
        "# " + pname + " --- Test Status",
        "",
        "*Updated: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "*",
        "",
        "## Summary",
        "",
        "| Suite | Result | Updated |",
        "|-------|--------|---------|",
    ]
    for sr in suite_results:
        e = S[sr.status]
        ts = sr.finished_at[:16].replace("T", " ") if sr.finished_at else "-"
        lines.append("| " + e + " " + sr.suite_name + " | " + sr.summary + " | " + ts + " |")
    lines.append("")
    lines.append("## Details")
    lines.append("")
    for sr in suite_results:
        e = S[sr.status]
        lines.append(e + " " + sr.suite_name)
        lines.append("")
        for t in sr.tests:
            te = S[t.status]
            lines.append("- " + te + " " + t.module + ": " + t.msg)
            if t.detail and t.status != "pass":
                detail = t.detail[:200].replace(chr(10), " ")
                lines.append("  > " + detail)
        lines.append("")
    sep = chr(10)
    wiki_path.write_text(sep.join(lines) + sep, encoding="utf-8")
    return wiki_path
