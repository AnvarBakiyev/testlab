"""
modules/watcher_freshness.py — Gmail и GDrive watcher живые?

Проверяет что sync_state файлы обновлялись недавно.
Если файл не обновлялся >N часов — watcher умер тихо.

config:
  files: list of {path, label, freshness_hours}
"""
import json
import time
from pathlib import Path
from core.base import TestResult


def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    files = config.get("files", [])

    if not files:
        return TestResult(status="fail", msg="Не указаны файлы для проверки")

    issues = []
    results = []

    for entry in files:
        path = base / entry["path"]
        label = entry["label"]
        limit_hours = entry.get("freshness_hours", 2)

        if not path.exists():
            issues.append(f"{label}: файл не найден")
            continue

        age_hours = (time.time() - path.stat().st_mtime) / 3600

        if age_hours > limit_hours * 2:
            issues.append(f"{label}: не обновлялся {age_hours:.1f}ч (лимит {limit_hours}ч)")
        elif age_hours > limit_hours:
            results.append(f"warn:{label}={age_hours:.1f}ч")
        else:
            results.append(f"{label}={age_hours:.0f}мин назад" if age_hours < 1
                           else f"{label}={age_hours:.1f}ч назад")

    if issues:
        return TestResult(
            status="fail",
            msg=" | ".join(issues),
            detail=" | ".join(results)
        )

    has_warn = any(r.startswith("warn:") for r in results)
    clean = [r.replace("warn:", "") for r in results]
    return TestResult(
        status="warn" if has_warn else "pass",
        msg=" | ".join(clean)
    )
