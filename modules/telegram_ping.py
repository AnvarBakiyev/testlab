"""
modules/telegram_ping.py — Telegram доступен и отвечает?

Отправляет тестовое сообщение, проверяет что API вернул message_id.
Testlab работает на Mac, поэтому читает токен из файла напрямую.

config:
  token_file: путь к token файлу (от домашней папки)
  chat_id: чат для отправки
  config_file: альтернативный источник chat_id (достаёт из daemon_config.json)
"""
import time
import requests
from pathlib import Path
from core.base import TestResult


def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))

    # Токен: сначала base-релативный, затем home-релативный
    token_rel = config.get("token_file", "Desktop/credentials/telegram_token.txt")
    token_file = base / token_rel
    if not token_file.exists():
        token_file = Path.home() / token_rel
    if not token_file.exists():
        # Фоллбэк: альтернативное имя
        alt = base / "Desktop/credentials/telegram_bot_token.txt"
        if alt.exists():
            token_file = alt
        else:
            return TestResult(status="fail", msg=f"Токен не найден: {token_file.name}")

    token = token_file.read_text().strip()
    if not token:
        return TestResult(status="fail", msg="Токен пустой")

    # chat_id: явный параметр > daemon_config.json
    chat_id = str(config.get("chat_id", "")).strip()
    if not chat_id:
        config_file = base / config.get(
            "config_file", "local_data/personal_agi/daemon_config.json"
        )
        if config_file.exists():
            import json
            cfg = json.loads(config_file.read_text())
            chat_id = str(cfg.get("notifications", {}).get("telegram_chat_id", ""))

    if not chat_id:
        return TestResult(status="fail", msg="chat_id не найден")

    try:
        test_text = f"[TESTLAB] ping {int(time.time())}"
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": test_text},
            timeout=10
        )

        if resp.status_code != 200:
            return TestResult(
                status="fail",
                msg=f"sendMessage failed: HTTP {resp.status_code}",
                detail=resp.text[:200]
            )

        msg_id = resp.json().get("result", {}).get("message_id")
        return TestResult(
            status="pass",
            msg=f"Доставлено (msg_id={msg_id})"
        )

    except requests.Timeout:
        return TestResult(status="fail", msg="Telegram API timeout (>10s)")
    except Exception as e:
        return TestResult(status="fail", msg=f"Ошибка: {e}")
