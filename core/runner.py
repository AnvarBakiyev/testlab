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
    return result


def run_all_suites(project_config: dict) -> list:
    return [run_suite(project_config, sid)
            for sid in project_config["test_suites"]]


def _run_module(module_name: str, config: dict) -> TestResult:
    t0 = time.monotonic()
    try:
        mod = importlib.import_module(f"modules.{module_name}")
        result = mod.run(config)
    except Exception:
        result = TestResult(
            status="fail",
            msg=f"Module {module_name} crashed",
            detail=traceback.format_exc()[-600:],
        )
    result.duration_ms = int((time.monotonic() - t0) * 1000)
    return result
