"""
E2E: Core Memory screen — core_memory.json exists and has required sections.
"""
import os
import json

AGI_BASE = os.path.expanduser("/Users/anvarbakiyev/dronor/local_data/personal_agi")
REQUIRED_KEYS = ["user", "values", "goals"]

def run(cfg: dict):
    from core.base import TestResult
    try:
        path = os.path.join(AGI_BASE, "core_memory.json")
        if not os.path.exists(path):
            return TestResult("fail", "core_memory.json not found",
                              detail=f"Expected at: {path}")

        with open(path) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return TestResult("fail", "core_memory.json is not a JSON object",
                              data={"type": type(data).__name__})

        existing_keys = list(data.keys())
        missing = [k for k in REQUIRED_KEYS if k not in data]

        if missing:
            return TestResult("warn",
                f"Core Memory missing sections: {missing}",
                detail=f"Found: {existing_keys}",
                data={"missing": missing, "found": existing_keys})

        size_kb = os.path.getsize(path) // 1024
        return TestResult("pass",
            f"Core Memory OK — {len(existing_keys)} sections, {size_kb}KB",
            data={"sections": existing_keys, "size_kb": size_kb})
    except json.JSONDecodeError as e:
        return TestResult("fail", f"core_memory.json is corrupt: {e}")
    except Exception as e:
        return TestResult("fail", f"Core Memory check crashed: {e}")
