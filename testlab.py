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


if __name__ == "__main__":
    port = int(os.environ.get("TESTLAB_PORT", 9200))
    print(f"Universal TestLab running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
