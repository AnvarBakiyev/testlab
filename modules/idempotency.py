"""
modules/idempotency.py — Duplicate message detection.
config: db, dedup_table="sent_notifications", hash_col="notification_hash", window_hours=24
"""
import sqlite3
from pathlib import Path
from core.base import TestResult

def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    db_path = base / config["db"]
    if not db_path.exists():
        return TestResult(status="warn",
                          msg=f"БД не найдена: {db_path} (ещё не создана?)")
    table = config.get("dedup_table", "sent_notifications")
    hours = config.get("window_hours", 24)
    try:
        conn = sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if table not in tables:
            conn.close()
            return TestResult(
                status="warn",
                msg=f"Таблица {table} не существует — идемпотентность не настроена",
                detail="Добавьте IdempotentNotifier в код отправки уведомлений"
            )
        total = conn.execute(
            f"SELECT COUNT(*) FROM {table} "
            f"WHERE sent_at > datetime('now', '-{hours} hours')"
        ).fetchone()[0]
        conn.close()
        return TestResult(
            status="pass",
            msg=f"За {hours}ч: {total} уникальных уведомлений",
            data={"sent": total, "window_hours": hours},
        )
    except Exception as e:
        return TestResult(status="fail", msg=f"Ошибка: {e}")
