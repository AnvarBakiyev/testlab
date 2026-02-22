"""
core/wiki.py - Write test-status markdown to testlab/wiki/ and optionally to local_data wiki.

Cache strategy: each suite result is stored in a per-project JSON cache.
When any suite runs, the markdown is rebuilt from ALL cached suite results,
so the wiki always shows a complete picture regardless of which suite ran last.
"""
import json
from datetime import datetime
from pathlib import Path

TESTLAB_ROOT = Path(__file__).parent.parent
S = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}


def _load_cache(cache_path: Path) -> dict:
    """Load {suite_id: serialised_result} dict from disk."""
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache_path: Path, cache: dict) -> None:
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _suite_to_dict(sr) -> dict:
    """Serialise a SuiteResult to a plain dict for JSON storage."""
    return {
        "suite_id":   sr.suite_id,
        "suite_name": sr.suite_name,
        "status":     sr.status,
        "summary":    sr.summary,
        "finished_at": sr.finished_at or "",
        "tests": [
            {
                "module": t.module,
                "status": t.status,
                "msg":    t.msg,
                "detail": t.detail or "",
            }
            for t in sr.tests
        ],
    }


def _build_markdown(pname: str, suite_dicts: list) -> str:
    lines = [
        "# " + pname + " — Test Status",
        "",
        "*Updated: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "*",
        "",
        "## Summary",
        "",
        "| Suite | Result | Updated |",
        "|-------|--------|---------|",
    ]
    for d in suite_dicts:
        e = S.get(d["status"], "?")
        ts = d["finished_at"][:16].replace("T", " ") if d["finished_at"] else "-"
        lines.append("| " + e + " " + d["suite_name"] + " | " + d["summary"] + " | " + ts + " |")
    lines.append("")
    lines.append("## Details")
    lines.append("")
    for d in suite_dicts:
        e = S.get(d["status"], "?")
        lines.append(e + " " + d["suite_name"])
        lines.append("")
        for t in d["tests"]:
            te = S.get(t["status"], "?")
            lines.append("- " + te + " " + t["module"] + ": " + t["msg"])
            if t["detail"] and t["status"] != "pass":
                lines.append("  > " + t["detail"][:200].replace("\n", " "))
        lines.append("")
    return "\n".join(lines) + "\n"


def update_project_wiki(project_config: dict, suite_results) -> Path:
    pid   = project_config["id"]
    pname = project_config["name"]

    projects_dir = TESTLAB_ROOT / "wiki" / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    cache_path   = projects_dir / (pid + "_cache.json")

    # Load existing cache and merge new results
    cache = _load_cache(cache_path)
    if not isinstance(suite_results, list):
        suite_results = [suite_results]
    for sr in suite_results:
        cache[sr.suite_id] = _suite_to_dict(sr)
    _save_cache(cache_path, cache)

    # Rebuild markdown from ALL cached suites (preserve project.json order)
    suite_order = list(project_config.get("test_suites", {}).keys())
    ordered = [cache[sid] for sid in suite_order if sid in cache]
    # append any cached suites not in current project.json (shouldn't happen, but safe)
    known = set(suite_order)
    ordered += [v for k, v in cache.items() if k not in known]

    content = _build_markdown(pname, ordered)

    # Write internal wiki
    internal_path = projects_dir / (pid + ".md")
    internal_path.write_text(content, encoding="utf-8")

    # Write to local_data wiki if configured
    wiki_path_rel = project_config.get("wiki_path")
    if wiki_path_rel:
        ext_path = Path("/Users/anvarbakiyev/dronor/local_data/wiki") / wiki_path_rel
        ext_path.parent.mkdir(parents=True, exist_ok=True)
        ext_path.write_text(content, encoding="utf-8")

    return internal_path
