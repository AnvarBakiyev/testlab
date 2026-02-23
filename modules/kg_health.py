"""
modules/kg_health.py — здоровье Knowledge Graph.

Запускает Kuzu через subprocess + os._exit(0) (требование Kuzu, иначе segfault).
Testlab работает на Mac, поэтому subprocess работает напрямую.

config:
  kg_path: путь к knowledge.db
  min_persons: default 100
  min_orgs: default 10
  script_path: временный файл для скрипта (default /tmp/testlab_kg.py)
"""
import subprocess
import json
from pathlib import Path
from core.base import TestResult


KUZU_SCRIPT_TEMPLATE = '''
import kuzu, os, sys, json
db = kuzu.Database("{kg_path}", read_only=True)
conn = kuzu.Connection(db)
data = {{}}
r = conn.execute("MATCH (p:Person) RETURN count(p) AS cnt")
data["persons"] = r.get_next()[0] if r.has_next() else 0
r = conn.execute("MATCH (o:Organization) RETURN count(o) AS cnt")
data["orgs"] = r.get_next()[0] if r.has_next() else 0
r = conn.execute("MATCH (c:Communication) RETURN count(c) AS cnt")
data["comms"] = r.get_next()[0] if r.has_next() else 0
r = conn.execute("MATCH (p:Person) WITH p.name AS n, count(*) AS cnt WHERE cnt > 1 RETURN count(*)")
data["name_dupes"] = r.get_next()[0] if r.has_next() else 0
# DRO-21: orphan nodes checks
r = conn.execute("MATCH (p:Person) WHERE NOT EXISTS {{ MATCH (p)-[:KNOWS]-() }} AND NOT EXISTS {{ MATCH (p)-[:WORKS_AT]-() }} RETURN count(p)")
data["orphan_persons"] = r.get_next()[0] if r.has_next() else 0
r = conn.execute("MATCH (o:Organization) WHERE NOT EXISTS {{ MATCH ()-[:WORKS_AT]->(o) }} RETURN count(o)")
data["orphan_orgs"] = r.get_next()[0] if r.has_next() else 0
print(json.dumps(data), flush=True)
sys.stdout.flush()
os._exit(0)
'''


def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    kg_path = config.get("kg_path", str(base / "local_data/personal_agi/knowledge.db"))
    min_persons = config.get("min_persons", 100)
    min_orgs = config.get("min_orgs", 10)
    script_path = config.get("script_path", "/tmp/testlab_kg.py")

    if not Path(kg_path).exists():
        return TestResult(status="fail", msg=f"KG не найден: {kg_path}")

    # Пишем скрипт в файл — надёжнее чем -c с вложенными кавычками
    script_content = KUZU_SCRIPT_TEMPLATE.format(kg_path=kg_path)
    Path(script_path).write_text(script_content)

    try:
        proc = subprocess.run(
            ["/usr/local/bin/python3", script_path],  # system python lacks kuzu
            capture_output=True, text=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        return TestResult(status="fail", msg="Kuzu timeout (>60s)")
    except Exception as e:
        return TestResult(status="fail", msg=f"subprocess error: {e}")

    stdout = proc.stdout.strip()
    if not stdout:
        return TestResult(
            status="fail",
            msg="Kuzu не вернул данные",
            detail=proc.stderr[-300:]
        )

    try:
        d = json.loads(stdout)
    except Exception as e:
        return TestResult(
            status="fail",
            msg=f"Не удалось парсить JSON: {e}",
            detail=stdout[:300]
        )

    max_orphan_persons = config.get("max_orphan_persons", 50)
    max_orphan_orgs = config.get("max_orphan_orgs", 20)

    issues = []
    if d["persons"] < min_persons:
        issues.append(f"Person: {d['persons']} < {min_persons}")
    if d["orgs"] < min_orgs:
        issues.append(f"Org: {d['orgs']} < {min_orgs}")
    if d["name_dupes"] > 0:
        issues.append(f"Дублей по имени: {d['name_dupes']}")
    if d.get("orphan_persons", 0) > max_orphan_persons:
        issues.append(f"Orphan persons: {d['orphan_persons']} > {max_orphan_persons}")
    if d.get("orphan_orgs", 0) > max_orphan_orgs:
        issues.append(f"Orphan orgs: {d['orphan_orgs']} > {max_orphan_orgs}")

    msg = (f"Person: {d['persons']} | Org: {d['orgs']} | "
           f"Comm: {d['comms']} | Name-дублей: {d['name_dupes']} | "
           f"Orphan persons: {d.get('orphan_persons', '?')}, orgs: {d.get('orphan_orgs', '?')}")

    if issues:
        return TestResult(status="warn", msg=msg, detail=" | ".join(issues))

    return TestResult(status="pass", msg=msg)
