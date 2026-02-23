"""
core/runner.py — Исполнитель тест-сьютов.
Получает project_config, загружает модули, запускает тесты, возвращает SuiteResult.
"""
import importlib
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from core.base import TestResult, SuiteResult
from core import notifier


def run_suite(project_config: dict, suite_id: str) -> SuiteResult:
    suite_cfg = project_config["test_suites"][suite_id]
    project_id = project_config["id"]
    base_path = Path(project_config["base_path"])
    result = SuiteResult(
        suite_id=suite_id,
        suite_name=suite_cfg["name"],
        project=project_id,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    for module_cfg in suite_cfg["modules"]:
        module_name = module_cfg["module"]
        config = {**module_cfg.get("config", {}), "_base_path": str(base_path)}
        test = _run_module(module_name, config)
        test.module = module_name
        test.suite = suite_id
        test.project = project_id
        result.tests.append(test)
    result.finished_at = datetime.now(timezone.utc).isoformat()

    # Алерт в Telegram если есть настройка и пали тесты
    notif_cfg = project_config.get("notifications", {})
    if notif_cfg.get("telegram_chat_id"):
        notifier.notify_if_needed(
            result=result,
            token_file=notif_cfg.get(
                "token_file",
                str(Path.home() / "Desktop/credentials/telegram_token.txt")
            ),
            chat_id=str(notif_cfg["telegram_chat_id"]),
        )

    return result


def run_all_suites(project_config: dict) -> list:
    return [run_suite(project_config, sid)
            for sid in project_config["test_suites"]]


def _run_module(module_name: str, config: dict) -> TestResult:
    t0 = time.monotonic()
    try:
        full_name = f"modules.{module_name}"
        mod = importlib.import_module(full_name)
        importlib.reload(mod)  # Always reload — picks up file changes without server restart
        result = mod.run(config)
    except Exception:
        result = TestResult(
            status="fail",
            msg=f"Module {module_name} crashed",
            detail=traceback.format_exc()[-600:],
        )
    result.duration_ms = int((time.monotonic() - t0) * 1000)
    return result
