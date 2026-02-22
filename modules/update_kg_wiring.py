"""
Test: update_kg executor is wired to Dronor (not a stub).

Checks:
1. _exec_memory_update function exists in agi_daemon.py
2. update_kg branch calls _exec_memory_update (not stub)
3. Dronor memory experts exist: memory_updater, memory_auto_manager
4. LLM prompt contains update_kg instructions with details fields
"""
from dataclasses import dataclass
from typing import Any

@dataclass
class ModuleResult:
    status: str
    msg: str
    details: Any = None

DAEMON_PATH = "/Users/anvarbakiyev/dronor/daemon/agi_daemon.py"
DRONOR_URL = "http://localhost:9100"

REQUIRED_EXPERTS = ["memory_updater", "memory_auto_manager", "memory_reflection", "memory_learning_extractor"]

def run(config: dict) -> ModuleResult:
    import requests

    issues = []
    warnings = []

    # Check 1: function exists
    try:
        code = open(DAEMON_PATH).read()
    except FileNotFoundError:
        return ModuleResult("fail", f"agi_daemon.py not found at {DAEMON_PATH}")

    if "def _exec_memory_update" not in code:
        issues.append("_exec_memory_update function missing - stub not replaced")

    # Check 2: update_kg branch calls the function (not stub)
    if '"KG update noted"' in code:
        issues.append("update_kg is still a stub (KG update noted)")
    elif "_exec_memory_update(description, details)" not in code:
        issues.append("update_kg branch does not call _exec_memory_update")

    # Check 3: prompt contains update_kg instructions
    if "details.memory_expert" not in code and "memory_expert" not in code:
        warnings.append("Prompt has no update_kg instructions - LLM may pass empty details")

    # Check 4: Dronor experts exist
    try:
        missing = []
        for expert in REQUIRED_EXPERTS:
            r = requests.get(f"{DRONOR_URL}/api/expert/get/{expert}", timeout=5)
            if r.status_code != 200:
                missing.append(expert)
        if missing:
            issues.append(f"Missing Dronor experts: {missing}")
    except Exception as e:
        warnings.append(f"Dronor unreachable: {e}")

    if issues:
        return ModuleResult("fail", "; ".join(issues), {"warnings": warnings})
    if warnings:
        return ModuleResult("warn", "; ".join(warnings))
    return ModuleResult("pass", "update_kg wired to Dronor memory experts")
