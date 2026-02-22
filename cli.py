import sys
import json
from pathlib import Path

TESTLAB_ROOT = Path(__file__).parent
if str(TESTLAB_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTLAB_ROOT))

from core.config import load_project
from core.runner import run_suite, run_all_suites
from core import reporter, wiki

STATUS_EMOJI = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}


def print_result(sr):
    e = STATUS_EMOJI[sr.status]
    print("")
    print(f"[{e}] {sr.suite_name} [{sr.project}] -- {sr.summary}")
    for t in sr.tests:
        te = STATUS_EMOJI[t.status]
        print(f"  [{te}] {t.module}: {t.msg} ({t.duration_ms}ms)")
        if t.detail and t.status != "pass":
            for line in t.detail[:300].splitlines():
                print(f"      {line}")


def main():
    args = sys.argv[1:]

    if not args or "--list" in args:
        registry = json.loads((TESTLAB_ROOT / "projects.json").read_text())
        print("\nProjects:")
        for p in registry["projects"]:
            cfg = json.loads((TESTLAB_ROOT / p["config"]).read_text())
            suites = list(cfg["test_suites"].keys())
            joined = ", ".join(suites)
            print(f"  {p['id']} -- {p['name']} [{joined}]")
        return

    project_id = args[0]
    suite_id = args[1] if len(args) > 1 else None
    if suite_id == "all":
        suite_id = None  # "all" = запустить все сьюты

    cfg = load_project(project_id)
    if cfg is None:
        print(f"Project not found: {project_id}")
        sys.exit(1)

    if suite_id:
        result = run_suite(cfg, suite_id)
        print_result(result)
        reporter.save_json(result, TESTLAB_ROOT)
        wiki.update_project_wiki(cfg, [result])
        sys.exit(0 if result.status in ("pass", "warn") else 1)
    else:
        results = run_all_suites(cfg)
        for r in results:
            print_result(r)
        for r in results:
            reporter.save_json(r, TESTLAB_ROOT)
        wiki.update_project_wiki(cfg, results)
        sys.exit(1 if any(r.status == "fail" for r in results) else 0)


if __name__ == "__main__":
    main()
