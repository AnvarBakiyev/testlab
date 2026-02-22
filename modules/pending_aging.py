"""
modules/pending_aging.py — зависшие pending_actions.

Ищет задачи со статусом PENDING которые не двигались > N часов.
Зависшие задачи = принятое решение не получено, система застряла.

config:
  db: путь к pending_actions.db
  stale_hours: через сколько часов задача считается зависшей (default: 48)
  max_stale: макс зависших до warn (default: 0)
"""
import sqlite3
from pathlib import Path
from core.base import TestResult


def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    db_path = base / config["db"]
    stale_hours = config.get("stale_hours", 48)
    max_stale = config.get("max_stale", 0)

    if not db_path.exists():
        return TestResult(status="fail", msg=f"БД не найдена: {db_path.name}")

    try:
        conn = sqlite3.connect(str(db_path))

        # Всего в статусе PENDING
        total_pending = conn.execute(
            "SELECT COUNT(*) FROM pending WHERE status = 'PENDING'"
        ).fetchone()[0]

        # Зависшие: PENDING и не двигались > stale_hours
        stale = conn.execute(
            "SELECT COUNT(*) FROM pending "
            "WHERE status = 'PENDING' "
            "AND created_at < datetime('now', ? || ' hours')",
            (f"-{stale_hours}",)
        ).fetchone()[0]

        # Самые старые — для detail
        oldest = conn.execute(
            "SELECT action_type, created_at, description "
            "FROM pending WHERE status = 'PENDING' "
            "ORDER BY created_at ASC LIMIT 3"
        ).fetchall()

        conn.close()

        oldest_str = "\n".join(
            f"  [{r[1][:16]}] {r[0]}: {r[2][:60]}" for r in oldest
        )

        if stale > max_stale:
            return TestResult(
                status="warn" if stale <= 5 else "fail",
                msg=f"Зависших >{stale_hours}ч: {stale} | Всего pending: {total_pending}",
                detail=f"Старые:\n{oldest_str}"
            )

        return TestResult(
            status="pass",
            msg=f"Pending: {total_pending} | Зависших >{stale_hours}ч: {stale}"
        )

    except Exception as e:
        return TestResult(status="fail", msg=f"SQLite error: {e}")
