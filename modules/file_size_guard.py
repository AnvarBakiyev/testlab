"""
modules/file_size_guard.py — guards critical files from growing beyond limits.

config:
  checks: list of {path, max_lines, label}
  _base_path: project base path
"""
from pathlib import Path
from core.base import TestResult


def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    checks = config.get("checks", [])

    if not checks:
        return TestResult(status="fail", msg="No checks configured")

    failures = []
    warnings = []
    lines_info = []

    for check in checks:
        file_path = base / check["path"]
        max_lines = check["max_lines"]
        label = check.get("label", check["path"])

        if not file_path.exists():
            failures.append(f"{label}: file not found")
            continue

        line_count = sum(1 for _ in file_path.open(encoding="utf-8", errors="ignore"))
        lines_info.append(f"{label}: {line_count} lines")

        if line_count > max_lines:
            failures.append(f"{label}: {line_count} > {max_lines} lines — needs refactoring")
        elif line_count > max_lines * 0.85:
            warnings.append(f"{label}: {line_count} lines (approaching limit {max_lines})")

    summary = " | ".join(lines_info)

    if failures:
        return TestResult(
            status="fail",
            msg=summary,
            detail=" | ".join(failures)
        )
    if warnings:
        return TestResult(
            status="warn",
            msg=summary,
            detail=" | ".join(warnings)
        )
    return TestResult(status="pass", msg=summary)
