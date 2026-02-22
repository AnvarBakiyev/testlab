"""
modules/daemon_errors.py — CRITICAL/ERROR в логе daemon.

Читает последние N строк лог и ищет ошибки.
Если CRITICAL — fail.
Если много ERROR — warn.

config:
  log_file: путь к лог-файлу
  tail_lines: сколько строк с конца читать (default: 200)
  max_errors: макс. ERROR до warn (default: 3)
"""
from pathlib import Path
from collections import deque
from core.base import TestResult


def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    log_path = base / config["log_file"]
    tail_lines = config.get("tail_lines", 200)
    max_errors = config.get("max_errors", 3)

    if not log_path.exists():
        return TestResult(status="fail", msg=f"Лог не найден: {log_path.name}")

    # Читаем последние N строк без загрузки всего файла в память
    try:
        lines = deque(log_path.open(encoding="utf-8", errors="replace"), maxlen=tail_lines)
    except Exception as e:
        return TestResult(status="fail", msg=f"Ошибка чтения лога: {e}")

    criticals = []
    errors = []

    for line in lines:
        line = line.strip()
        if "CRITICAL" in line:
            criticals.append(line[-120:])  # последние 120 символов достаточно
        elif " ERROR " in line:
            errors.append(line[-120:])

    if criticals:
        return TestResult(
            status="fail",
            msg=f"{len(criticals)} CRITICAL в последних {tail_lines} строках лога",
            detail="\n".join(criticals[:3])
        )

    if len(errors) > max_errors:
        return TestResult(
            status="warn",
            msg=f"{len(errors)} ERROR в последних {tail_lines} строках лога",
            detail="\n".join(errors[:3])
        )

    msg = f"Лог чистый"
    if errors:
        msg = f"{len(errors)} ERROR (в норме)"
    return TestResult(status="pass", msg=msg)
