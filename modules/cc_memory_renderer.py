"""
cc_memory_renderer — checks core_memory.json blocks for raw JSON artifacts.
Artifacts in content fields render as machine text in Command Center Memory page.
"""
import json
import re
from pathlib import Path
from core.base import TestResult

DEFAULT_PATH = "/Users/anvarbakiyev/dronor/local_data/personal_agi/core_memory.json"

ARTIFACT_PATTERNS = [
    (r'\{["\']\w', "JSON object"),
    (r'"[a-z_]+"\s*:', "JSON key"),
    (r'\\n', "escaped newline literal"),
    (r"'[a-z_]+'\s*:", "Python dict key"),
    (r"\bTrue\b|\bFalse\b|\bNone\b", "Python literal"),
]


def run(config: dict) -> TestResult:
    path = Path(config.get("memory_path", DEFAULT_PATH))
    warn_threshold = int(config.get("warn_threshold", 1))
    fail_threshold = int(config.get("fail_threshold", 3))

    if not path.exists():
        return TestResult(status="fail", msg=f"core_memory.json not found: {path}", detail="", data={})

    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return TestResult(status="fail", msg=f"JSON parse error: {e}", detail="", data={})

    blocks = data.get("blocks", {})
    violations = []
    for block_name, block in blocks.items():
        if not isinstance(block, dict):
            continue
        content = block.get("content", "")
        if not isinstance(content, str):
            continue
        for pattern, label in ARTIFACT_PATTERNS:
            if re.search(pattern, content):
                violations.append(f"block '{block_name}': {label}")

    total = len(violations)
    data_out = {"blocks_checked": len(blocks), "violations": violations}

    if total >= fail_threshold:
        return TestResult(status="fail", msg=f"{total} artifact violations in {len(blocks)} blocks", detail="; ".join(violations[:2]), data=data_out)
    if total >= warn_threshold:
        return TestResult(status="warn", msg=f"{total} artifact(s) in {len(blocks)} blocks", detail="; ".join(violations[:2]), data=data_out)
    return TestResult(status="pass", msg=f"All {len(blocks)} blocks clean", detail="", data=data_out)
