"""
modules/process_monitor.py — Process running?
config: process (pgrep pattern), pid_file (optional, relative to base_path)
"""
import subprocess
from pathlib import Path
from core.base import TestResult

def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    process = config.get("process", "")
    pid_file = config.get("pid_file", "")
    results = []
    issues = []
    if process:
        r = subprocess.run(["pgrep", "-f", process], capture_output=True, text=True)
        pids = r.stdout.strip().split()
        if pids:
            results.append(f"pgrep: {len(pids)} процесс(ов) PID={pids[0]}")
        else:
            issues.append(f"Процесс не найден: {process}")
    if pid_file:
        pid_path = base / pid_file
        if pid_path.exists():
            pid = int(pid_path.read_text().strip())
            r = subprocess.run(["kill", "-0", str(pid)], capture_output=True)
            if r.returncode == 0:
                results.append(f"pid_file: PID={pid} жив")
            else:
                issues.append(f"PID {pid} мёртв")
        else:
            results.append("pid_file: не найден")
    if issues:
        return TestResult(status="fail", msg=" | ".join(issues),
                          detail=" | ".join(results))
    return TestResult(status="pass", msg=" | ".join(results))
