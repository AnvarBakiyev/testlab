"""
modules/cars_activity.py — AGI принимал решения за N часов?

Если daemon не принял ни одного решения за 24ч — что-то не так.

config:
  db: путь к daemon_state.db
  window_hours: окно проверки (default: 24)
  min_decisions: мин. решений до warn (default: 1)
"""
import sqlite3
from pathlib import Path
from core.base import TestResult


def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    db_path = base / config["db"]
    window_hours = config.get("window_hours", 24)
    min_decisions = config.get("min_decisions", 1)

    if not db_path.exists():
        return TestResult(status="fail", msg=f"БД не найдена: {db_path.name}")

    try:
        conn = sqlite3.connect(str(db_path))

        # Сколько решений за окно
        decisions = conn.execute(
            "SELECT COUNT(*) FROM daemon_decisions "
            "WHERE timestamp > datetime('now', ? || ' hours')",
            (f"-{window_hours}",)
        ).fetchone()[0]

        # Сколько циклов запуска за то же время
        runs = conn.execute(
            "SELECT COUNT(*) FROM daemon_runs "
            "WHERE started_at > datetime('now', ? || ' hours')",
            (f"-{window_hours}",)
        ).fetchone()[0]

        # Последний запуск
        last_run = conn.execute(
            "SELECT started_at FROM daemon_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()

        conn.close()

        last_str = last_run[0][:16] if last_run else "нет данных"

        if decisions < min_decisions:
            return TestResult(
                status="fail",
                msg=f"Решений за {window_hours}ч: {decisions} (лимит {min_decisions}). Циклов: {runs}",
                detail=f"Последний запуск: {last_str}"
            )

        return TestResult(
            status="pass",
            msg=f"Решений: {decisions} за {window_hours}ч | Циклов: {runs} | Последний: {last_str}"
        )

    except Exception as e:
        return TestResult(status="fail", msg=f"SQLite error: {e}")
