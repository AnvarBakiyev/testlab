"""
modules/sqlite_inspector.py — SQLite DB freshness & completeness.
config: db, table, timestamp_col="created_at", freshness_hours, min_rows, custom_query, custom_query_min
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from core.base import TestResult

def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    db_path = base / config["db"]
    if not db_path.exists():
        return TestResult(status="fail", msg=f"БД не найдена: {db_path}")
    try:
        conn = sqlite3.connect(str(db_path))
        results = []
        issues = []
        table = config.get("table")
        if table and config.get("freshness_hours"):
            hours = config["freshness_hours"]
            ts_col = config.get("timestamp_col", "created_at")
            row = conn.execute(f"SELECT MAX({ts_col}) FROM {table}").fetchone()
            if row and row[0]:
                last = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
                if h > hours * 2:
                    issues.append(f"Нет записей {h:.1f}ч (лимит {hours}ч)")
                elif h > hours:
                    results.append(f"warn:last={h:.1f}ч")
                else:
                    results.append(f"last={h:.1f}ч назад")
        if table and "min_rows" in config:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            results.append(f"rows={count}")
            if count < config["min_rows"]:
                issues.append(f"Мало строк: {count} < {config['min_rows']}")
        if config.get("custom_query"):
            val = conn.execute(config["custom_query"]).fetchone()[0]
            results.append(f"query={val}")
            if "custom_query_min" in config and val < config["custom_query_min"]:
                issues.append(f"Значение {val} < {config['custom_query_min']}")
        conn.close()
        if issues:
            return TestResult(status="fail", msg=" | ".join(issues),
                              detail=" | ".join(results))
        has_warn = any(r.startswith("warn:") for r in results)
        clean = [r.replace("warn:", "") for r in results]
        return TestResult(status="warn" if has_warn else "pass", msg=" | ".join(clean))
    except Exception as e:
        return TestResult(status="fail", msg=f"SQLite error: {e}", detail=str(e))
