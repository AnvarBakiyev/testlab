"""
core/base.py — Единственный контракт всей платформы.

Любой модуль, любой тест, любой проект — всё возвращает TestResult.
Если это правило соблюдается — платформа работает.
"""
from dataclasses import dataclass, field
from typing import Literal, Optional
import time


@dataclass
class TestResult:
    status: Literal["pass", "warn", "fail"]
    msg: str
    detail: str = ""
    data: dict = field(default_factory=dict)
    duration_ms: int = 0
    # Для отчётов и wiki — откуда результат
    module: str = ""
    suite: str = ""
    project: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "msg": self.msg,
            "detail": self.detail,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "module": self.module,
            "suite": self.suite,
            "project": self.project,
        }

    @property
    def is_ok(self) -> bool:
        return self.status in ("pass", "warn")


@dataclass
class SuiteResult:
    suite_id: str
    suite_name: str
    project: str
    tests: list[TestResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    @property
    def status(self) -> Literal["pass", "warn", "fail"]:
        statuses = [t.status for t in self.tests]
        if "fail" in statuses:
            return "fail"
        if "warn" in statuses:
            return "warn"
        return "pass"

    @property
    def summary(self) -> str:
        total = len(self.tests)
        passed = sum(1 for t in self.tests if t.status == "pass")
        warned = sum(1 for t in self.tests if t.status == "warn")
        failed = sum(1 for t in self.tests if t.status == "fail")
        return f"{passed}/{total} pass, {warned} warn, {failed} fail"

    def to_dict(self) -> dict:
        return {
            "suite_id": self.suite_id,
            "suite_name": self.suite_name,
            "project": self.project,
            "status": self.status,
            "summary": self.summary,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "tests": [t.to_dict() for t in self.tests],
        }
