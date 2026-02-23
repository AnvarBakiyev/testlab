"""
testlab.py — Точка входа Universal TestLab.

HTTP API на port 9200. Используется Command Center через
существующий wiki API для отображения в CC.

Endpoints:
  GET  /api/testlab/projects          — список проектов
  GET  /api/testlab/status/{project}  — последние результаты
  POST /api/testlab/run               — запустить сьют {project, suite}
  POST /api/testlab/run_all           — запустить все сьюты проекта {project}
"""
import sys
import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_file

# Добавляем testlab/ в sys.path чтобы import core.* и modules.* работал
TESTLAB_ROOT = Path(__file__).parent
if str(TESTLAB_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTLAB_ROOT))

from core.runner import run_suite, run_all_suites
from core import reporter, wiki, github

app = Flask(__name__)


def _load_projects() -> dict:
    """Load projects registry. Returns {project_id: config_dict}."""
    registry_path = TESTLAB_ROOT / "projects.json"
    registry = json.loads(registry_path.read_text())
    projects = {}
    for entry in registry["projects"]:
        cfg_path = TESTLAB_ROOT / entry["config"]
        if cfg_path.exists():
            projects[entry["id"]] = json.loads(cfg_path.read_text())
    return projects


def _load_project(project_id: str) -> dict | None:
    projects = _load_projects()
    return projects.get(project_id)


@app.route("/api/testlab/projects")
def list_projects():
    projects = _load_projects()
    return jsonify({
        "status": "ok",
        "projects": [
            {
                "id": cfg["id"],
                "name": cfg["name"],
                "description": cfg.get("description", ""),
                "suites": list(cfg["test_suites"].keys()),
            }
            for cfg in projects.values()
        ]
    })


@app.route("/api/testlab/status/<project_id>")
def project_status(project_id: str):
    """Returns latest results for all suites of a project."""
    results_dir = TESTLAB_ROOT / "results" / project_id
    if not results_dir.exists():
        return jsonify({"status": "ok", "project": project_id, "suites": [],
                        "note": "No runs yet"})
    suites = []
    for latest in sorted(results_dir.glob("*_latest.json")):
        try:
            data = json.loads(latest.read_text())
            suites.append(data)
        except Exception:
            pass
    return jsonify({"status": "ok", "project": project_id, "suites": suites})


@app.route("/api/testlab/run", methods=["POST"])
def run_one():
    """Run a single suite. Body: {project, suite, push_github=false}"""
    body = request.get_json() or {}
    project_id = body.get("project")
    suite_id = body.get("suite")
    push = body.get("push_github", False)

    if not project_id or not suite_id:
        return jsonify({"status": "error", "msg": "project and suite required"}), 400

    cfg = _load_project(project_id)
    if not cfg:
        return jsonify({"status": "error", "msg": f"Project not found: {project_id}"}), 404

    if suite_id not in cfg["test_suites"]:
        return jsonify({"status": "error",
                        "msg": f"Suite not found: {suite_id}",
                        "available": list(cfg["test_suites"].keys())}), 404

    result = run_suite(cfg, suite_id)
    saved = reporter.save_json(result, TESTLAB_ROOT)
    wiki.update_project_wiki(cfg, [result])

    push_result = None
    if push:
        push_result = github.push_results(result, TESTLAB_ROOT)

    return jsonify({
        "status": "ok",
        "suite_status": result.status,
        "summary": result.summary,
        "saved": str(saved),
        "push": push_result,
        "tests": [t.to_dict() for t in result.tests],
    })



# --- Async suite runner ---
import threading
import uuid as _uuid

_async_jobs = {}  # job_id -> {status, result}

@app.route("/api/testlab/run_async", methods=["POST"])
def run_async():
    """Start suite in background thread. Returns job_id immediately."""
    body = request.get_json() or {}
    project_id = body.get("project")
    suite_id = body.get("suite")

    if not project_id or not suite_id:
        return jsonify({"status": "error", "msg": "project and suite required"}), 400

    cfg = _load_project(project_id)
    if not cfg:
        return jsonify({"status": "error", "msg": f"Project not found: {project_id}"}), 404

    if suite_id not in cfg["test_suites"]:
        return jsonify({"status": "error", "msg": f"Suite not found: {suite_id}",
                        "available": list(cfg["test_suites"].keys())}), 404

    job_id = str(_uuid.uuid4())[:8]
    _async_jobs[job_id] = {"status": "running", "suite": suite_id, "project": project_id}

    def _run():
        try:
            result = run_suite(cfg, suite_id)
            reporter.save_json(result, TESTLAB_ROOT)
            _async_jobs[job_id] = {
                "status": "done",
                "suite_status": result.status,
                "summary": result.summary,
                "tests": [t.to_dict() for t in result.tests]
            }
        except Exception as e:
            _async_jobs[job_id] = {"status": "error", "msg": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "job_id": job_id})


@app.route("/api/testlab/job/<job_id>")
def job_status(job_id):
    """Poll async job status."""
    job = _async_jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)


@app.route("/api/testlab/run_all", methods=["POST"])
def run_all():
    """Run all suites for a project. Body: {project, push_github=false}"""
    body = request.get_json() or {}
    project_id = body.get("project")
    push = body.get("push_github", False)

    if not project_id:
        return jsonify({"status": "error", "msg": "project required"}), 400

    cfg = _load_project(project_id)
    if not cfg:
        return jsonify({"status": "error", "msg": f"Project not found: {project_id}"}), 404

    suite_results = run_all_suites(cfg)
    saved_paths = []
    for sr in suite_results:
        saved_paths.append(str(reporter.save_json(sr, TESTLAB_ROOT)))

    wiki_path = wiki.update_project_wiki(cfg, suite_results)

    push_result = None
    if push:
        # Push after last suite so all results are committed together
        push_result = github.push_results(suite_results[-1], TESTLAB_ROOT)

    overall = "fail" if any(sr.status == "fail" for sr in suite_results) else                "warn" if any(sr.status == "warn" for sr in suite_results) else "pass"

    return jsonify({
        "status": "ok",
        "project": project_id,
        "overall": overall,
        "wiki": str(wiki_path),
        "push": push_result,
        "suites": [
            {
                "suite_id": sr.suite_id,
                "suite_name": sr.suite_name,
                "status": sr.status,
                "summary": sr.summary,
                "tests": [t.to_dict() for t in sr.tests],
            }
            for sr in suite_results
        ]
    })



@app.route("/ui")
def dashboard():
    """Serve TestLab dashboard."""
    return send_file(TESTLAB_ROOT / "ui" / "dashboard.html")


@app.route("/api/testlab/history/<project_id>/<suite_id>")
def suite_history(project_id: str, suite_id: str):
    """Return last N historical runs for a suite."""
    results_dir = TESTLAB_ROOT / "results" / project_id
    limit = int(request.args.get("limit", 20))
    if not results_dir.exists():
        return jsonify({"status": "ok", "runs": []})
    runs = []
    pattern = f"{suite_id}_20*.json"  # timestamped files only
    files = sorted(results_dir.glob(pattern), reverse=True)[:limit]
    for f in files:
        try:
            data = json.loads(f.read_text())
            runs.append({
                "finished_at": data.get("finished_at", ""),
                "status": data.get("status", ""),
                "summary": data.get("summary", ""),
            })
        except Exception:
            pass
    return jsonify({"status": "ok", "project": project_id, "suite": suite_id, "runs": runs})


@app.route("/api/testlab/health")
def health():
    return jsonify({"status": "ok", "service": "universal-testlab"})


@app.route("/api/testlab/run_module", methods=["POST"])
def run_module_direct():
    """
    Universal endpoint for Dronor experts.
    Body: {"module": "module_name", "params": {...}}
    Returns: TestResult as JSON
    """
    from core.runner import _run_module
    body = request.get_json(force=True, silent=True) or {}
    module_name = body.get("module", "").strip()
    params = body.get("params", {})

    if not module_name:
        return jsonify({"status": "fail", "msg": "'module' field is required", "detail": "", "data": {}}), 400

    # Inject base_path so modules can use it if needed
    params["_base_path"] = str(Path(".").resolve())

    result = _run_module(module_name, params)
    return jsonify({
        "status": result.status,
        "msg": result.msg,
        "detail": result.detail,
        "duration_ms": result.duration_ms,
        "data": getattr(result, "data", {}),
    })




@app.route("/api/testlab/report/<project_id>")
def generate_report(project_id: str):
    """
    Generate a Markdown bug report with all FAIL/WARN from latest suite runs.
    Download as .md file ready to send to an engineer.
    """
    import glob
    from datetime import datetime

    project = _load_project(project_id)
    if not project:
        return jsonify({"status": "error", "msg": f"Project {project_id} not found"}), 404

    results_dir = Path("results") / project_id
    if not results_dir.exists():
        return jsonify({"status": "error", "msg": "No results found"}), 404

    # Load latest result per suite
    latest = {}
    for json_file in results_dir.glob("*.json"):
        if json_file.name.startswith("_"):
            continue
        suite_id = (json.loads(json_file.read_text()).get("suite_id") or json_file.stem.split("_")[0])
        mtime = json_file.stat().st_mtime
        if suite_id not in latest or mtime > latest[suite_id][1]:
            latest[suite_id] = (json_file, mtime)

    # Build report
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Bug Report — {project.get('name', project_id)}",
        f"Generated: {now}\n",
        "---\n",
    ]

    total_fail = total_warn = 0

    for suite_id, (json_file, _) in sorted(latest.items()):
        try:
            data = json.loads(json_file.read_text())
        except Exception:
            continue

        tests = data.get("tests", [])
        bad = [t for t in tests if t.get("status") in ("fail", "warn")]
        if not bad:
            continue

        suite_name = data.get("suite_name", suite_id)
        suite_status = data.get("status", "?")
        started = data.get("started_at", "")[:16].replace("T", " ")
        lines.append(f"## {suite_name} [{suite_status.upper()}] — {started}\n")

        for t in bad:
            status = t.get("status", "?").upper()
            module = t.get("module", "?")
            msg = t.get("msg", "")
            detail = t.get("detail", "")
            dur = t.get("duration_ms", 0)

            lines.append(f"### [{status}] `{module}`")
            lines.append(f"**Message:** {msg}  ")
            lines.append(f"**Duration:** {dur}ms\n")

            if detail:
                lines.append("**Detail:**")
                lines.append("```")
                lines.append(detail[:800])
                lines.append("```\n")

            if status == "FAIL":
                total_fail += 1
            else:
                total_warn += 1

    if total_fail == 0 and total_warn == 0:
        lines = [f"# Bug Report — {project.get('name', project_id)}",
                 f"Generated: {now}\n", "---\n",
                 "## All suites passing — no issues found."]

    lines.insert(3, f"**Summary:** {total_fail} failures, {total_warn} warnings\n")

    md_content = "\n".join(lines)
    filename = f"testlab_report_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

    from flask import Response
    return Response(
        md_content,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )




@app.route("/api/testlab/audit/run", methods=["POST", "GET"])
def run_audit_report():
    """Run all audit modules and return ready HTML report (same as run_audit.py)."""
    import importlib.util
    import json as _json
    from datetime import datetime

    AUDIT_SUITE = [
        ("pending_duplicates_deep",  "Pending: Duplicate Actions",    "Pending Actions"),
        ("pending_age_audit",        "Pending: Stale Actions (Age)",  "Pending Actions"),
        ("pending_orphans_audit",    "Pending: Data Integrity",       "Pending Actions"),
        ("draft_quality_audit",      "Pending: Draft Quality",        "Pending Actions"),
        ("cars_distribution_audit",  "CARS: Score Distribution",      "CARS & Feedback"),
        ("feedback_loop_audit",      "CARS: Feedback Loop",           "CARS & Feedback"),
        ("events_pipeline_audit",    "Events: Pipeline Health",       "Pipeline & Events"),
        ("daemon_health_audit",      "Daemon: Health & Throughput",   "Daemon"),
        ("auto_reply_audit",         "Auto-Reply: System Health",     "System"),
        ("knowledge_db_audit",       "Knowledge: DB Integrity",       "System"),
        ("memory_block_freshness",   "Memory: Block Freshness",       "Memory"),
        ("memory_writers_active",    "Memory: Writers Active",        "Memory"),
        ("update_kg_wiring",         "Memory: KG Wiring",             "Memory"),
        ("connector_config_check",   "Connectors: Config Check",      "Connectors"),
        ("daemon_activity_check",    "Daemon: Activity Check",        "Daemon"),
    ]

    STATUS_COLOR = {"pass": "#22c55e", "fail": "#ef4444", "warn": "#f59e0b",
                    "error": "#a855f7", "skip": "#6b7280"}
    STATUS_ICON  = {"pass": "✅", "fail": "❌", "warn": "⚠️",
                    "error": "💥", "skip": "⏭️"}

    results_by_group = {}
    summary = {"total": 0, "pass": 0, "fail": 0, "warn": 0, "error": 0, "skip": 0}

    for name, label, group in AUDIT_SUITE:
        mod_path = TESTLAB_ROOT / "modules" / f"{name}.py"
        try:
            if not mod_path.exists():
                status, msg, data = "skip", f"Module not found: {name}.py", {}
            else:
                spec = importlib.util.spec_from_file_location(name, mod_path)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                r    = mod.run({})
                status = r.status
                msg    = r.msg
                data   = getattr(r, "data", {})
        except Exception as e:
            status, msg, data = "error", str(e), {}

        results_by_group.setdefault(group, []).append((label, name, status, msg, data))
        summary["total"] += 1
        summary[status]   = summary.get(status, 0) + 1

    # Build HTML
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fails = summary["fail"] + summary["error"]
    overall       = "HEALTHY" if fails == 0 else ("DEGRADED" if fails <= 3 else "CRITICAL")
    overall_color = "#22c55e" if overall == "HEALTHY" else ("#f59e0b" if overall == "DEGRADED" else "#ef4444")

    groups_html = ""
    for group, items in results_by_group.items():
        rows = ""
        for label, name, status, msg, data in items:
            sc   = STATUS_COLOR.get(status, "#6b7280")
            icon = STATUS_ICON.get(status, "?")

            data_rows = ""
            if data:
                for k, v in data.items():
                    if v is None or v == [] or v == {}: continue
                    val = _json.dumps(v, ensure_ascii=False)[:200] if isinstance(v, (dict, list)) else str(v)
                    data_rows += f"<tr><td style='padding:3px 8px;color:#94a3b8;font-size:12px'>{k}</td><td style='padding:3px 8px;font-size:12px;word-break:break-all'>{val}</td></tr>"
            data_html = f"<table style='width:100%;border-collapse:collapse;margin-top:6px'>{data_rows}</table>" if data_rows else ""

            rows += f"""<tr style='border-bottom:1px solid #1e293b'>
              <td style='padding:12px 16px;width:40px;text-align:center;font-size:18px'>{icon}</td>
              <td style='padding:12px 16px'>
                <div style='font-weight:600;color:#e2e8f0'>{label}</div>
                <div style='color:{sc};font-size:13px;margin-top:2px'>{msg}</div>
                {data_html}
              </td>
              <td style='padding:12px 16px;width:80px;text-align:center'>
                <span style='background:{sc}22;color:{sc};padding:3px 10px;
                  border-radius:12px;font-size:12px;font-weight:700;border:1px solid {sc}44'>
                  {status.upper()}
                </span>
              </td>
            </tr>"""

        groups_html += f"""<div style='margin-bottom:32px'>
          <h2 style='color:#94a3b8;font-size:13px;font-weight:700;letter-spacing:2px;
            text-transform:uppercase;margin-bottom:12px;padding-left:4px'>{group}</h2>
          <div style='background:#0f172a;border:1px solid #1e293b;border-radius:12px;overflow:hidden'>
            <table style='width:100%;border-collapse:collapse'>{rows}</table>
          </div></div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AGI Full Audit</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #020817; color: #e2e8f0;
    font-family: 'SF Mono', 'Fira Code', monospace; min-height:100vh; padding:40px 24px; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  .badge {{ display:inline-block; padding:6px 18px; border-radius:999px; font-size:13px;
    font-weight:800; letter-spacing:1px; background:{overall_color}22; color:{overall_color};
    border:1px solid {overall_color}55; margin-bottom:16px; }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:40px; }}
  .stat {{ background:#0f172a; border:1px solid #1e293b; border-radius:10px;
    padding:16px; text-align:center; }}
  .stat-num {{ font-size:28px; font-weight:800; }}
  .stat-label {{ font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:1px; margin-top:4px; }}
</style>
</head>
<body>
<div class="container">
  <div style="margin-bottom:40px">
    <div class="badge">{overall}</div>
    <div style="font-size:28px;font-weight:800;color:#f1f5f9;margin-bottom:4px">AGI Command Center</div>
    <div style="font-size:20px;font-weight:800;color:#64748b;margin-bottom:8px">Full System Audit</div>
    <div style="color:#475569;font-size:13px">Generated: {now}</div>
  </div>
  <div class="stats">
    <div class="stat"><div class="stat-num" style="color:#e2e8f0">{summary['total']}</div><div class="stat-label">Total Checks</div></div>
    <div class="stat"><div class="stat-num" style="color:#22c55e">{summary['pass']}</div><div class="stat-label">Passed</div></div>
    <div class="stat"><div class="stat-num" style="color:#f59e0b">{summary['warn']}</div><div class="stat-label">Warnings</div></div>
    <div class="stat"><div class="stat-num" style="color:#ef4444">{fails}</div><div class="stat-label">Failed</div></div>
  </div>
  {groups_html}
  <div style="text-align:center;color:#1e293b;font-size:11px;margin-top:40px">AGI TestLab v2.0</div>
</div>
</body></html>"""

    from flask import Response
    return Response(html, mimetype="text/html")



@app.route("/api/testlab/screenshots/<path:filename>")
def serve_screenshot(filename):
    """Serve a screenshot file from /tmp/cc_visual_test/ by filename."""
    from flask import send_from_directory
    screenshot_dir = "/tmp/cc_visual_test"
    return send_from_directory(screenshot_dir, filename)


@app.route("/api/testlab/screenshots")
def list_screenshots():
    """List all available screenshots from the last cc_visual run."""
    from pathlib import Path
    shot_dir = Path("/tmp/cc_visual_test")
    if not shot_dir.exists():
        return jsonify({"status": "ok", "screenshots": []})
    files = sorted(shot_dir.glob("*.png"))
    return jsonify({
        "status": "ok",
        "count": len(files),
        "screenshots": [
            {
                "name": f.name,
                "url": f"/api/testlab/screenshots/{f.name}",
                "size_kb": round(f.stat().st_size / 1024, 1)
            }
            for f in files
        ]
    })

if __name__ == "__main__":
    port = int(os.environ.get("TESTLAB_PORT", 9200))
    print(f"Universal TestLab running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


