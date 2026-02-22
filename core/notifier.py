"""
core/notifier.py — Telegram-алерты при падении тестов.

Дедупликация: hash всех fail-сообщений хранится в results/_alert_state.json.
Если те же ошибки — не шлём. Если новые или сьют восстановился — отправляем.
"""
import hashlib
import json
import requests
from pathlib import Path

from core.base import SuiteResult

ALERT_STATE_FILE = Path(__file__).parent.parent / "results" / "_alert_state.json"


def _load_state() -> dict:
    if ALERT_STATE_FILE.exists():
        try:
            return json.loads(ALERT_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    ALERT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STATE_FILE.write_text(json.dumps(state, indent=2))


def _fail_hash(result: SuiteResult) -> str:
    fails = sorted(t.msg for t in result.tests if t.status == "fail")
    raw = f"{result.suite_id}|{'|'.join(fails)}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _format_message(result: SuiteResult) -> str:
    fails = [t for t in result.tests if t.status == "fail"]
    warns = [t for t in result.tests if t.status == "warn"]
    total = len(result.tests)
    failed_count = len(fails)

    # Без Markdown чтобы избежать проблем с экранированием спецсимволов
    lines = [
        f"TESTLAB FAIL [{result.suite_name}]",
        f"Suite: {result.suite_id} | Project: {result.project}",
        f"Result: {failed_count}/{total} failed",
        "",
    ]
    for t in fails:
        lines.append(f"FAIL {t.module}: {t.msg}")
        if t.detail:
            lines.append(f"  >> {t.detail[:120]}")
    if warns:
        lines.append("")
        for t in warns:
            lines.append(f"WARN {t.module}: {t.msg}")
    return "\n".join(lines)


def notify_if_needed(result: SuiteResult, token_file: str, chat_id: str) -> bool:
    """
    Отправляет алерт если есть fail и ошибки новые.
    Сбрасывает стате если сьют восстановился.
    """
    if result.status != "fail":
        state = _load_state()
        if result.suite_id in state:
            del state[result.suite_id]
            _save_state(state)
        return False

    current_hash = _fail_hash(result)
    state = _load_state()

    if state.get(result.suite_id) == current_hash:
        return False  # Те же ошибки, не шлём

    # Ищем токен
    token_path = Path(token_file)
    if not token_path.exists():
        token_path = Path.home() / "Desktop" / "credentials" / "telegram_token.txt"
    if not token_path.exists():
        return False

    token = token_path.read_text().strip()
    message = _format_message(result)

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        if resp.status_code == 200:
            state[result.suite_id] = current_hash
            _save_state(state)
            return True
    except Exception:
        pass

    return False
