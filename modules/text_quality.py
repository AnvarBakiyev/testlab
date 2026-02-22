"""
modules/text_quality.py -- Text artifact detection.
config: texts (list) | source_db+source_query (SQLite) | source_expert (Dronor)
        check_artifacts=True
"""
import re
import sqlite3
import requests
from pathlib import Path
from core.base import TestResult

# Patterns that indicate technical artifacts leaking into user-facing text.
# Each tuple: (compiled_regex, human_label)
ARTIFACT_PATTERNS = [
    (re.compile(r'[{]["\']?\w+["\']?\s*:'), "JSON-object"),
    (re.compile(r'\b[a-z]{2,}_[a-z]{2,}\b'), "snake_case"),
    (re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}'), "ISO-timestamp"),
    (re.compile(r'\b(None|null|undefined|NaN)\b'), "code-literal"),
]


def run(config: dict) -> TestResult:
    texts = _collect(config)
    if not texts:
        return TestResult(status="warn", msg="No texts to check")

    issues = []
    if config.get("check_artifacts", True):
        for i, text in enumerate(texts):
            for pattern, label in ARTIFACT_PATTERNS:
                if pattern.search(text):
                    issues.append(f"[{i}] {label}: {text[:60]}")
                    break  # one issue per text is enough

    if issues:
        return TestResult(
            status="fail",
            msg=f"{len(issues)} texts with artifacts out of {len(texts)}",
            detail="\n".join(issues[:5]),
            data={"total": len(texts), "issues": len(issues)},
        )
    return TestResult(
        status="pass",
        msg=f"Checked {len(texts)} texts -- clean",
        data={"total": len(texts)},
    )


def sanitize(text: str) -> str:
    """Remove common technical artifacts from text."""
    text = re.sub(r'[{][^}]*}', '', text)
    text = re.sub(r'\b([a-z]+)_([a-z]+)\b', r'\1 \2', text)
    text = re.sub(r'\b(None|null|undefined)\b', '', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def _collect(config: dict) -> list:
    if "texts" in config:
        return config["texts"]

    if "source_db" in config and "source_query" in config:
        base = Path(config.get("_base_path", "/"))
        try:
            conn = sqlite3.connect(str(base / config["source_db"]))
            rows = conn.execute(config["source_query"]).fetchall()
            conn.close()
            return [r[0] for r in rows if r[0]]
        except Exception:
            return []

    if "source_expert" in config:
        try:
            resp = requests.post(
                "http://localhost:9100/api/expert/run",
                json={"expert_name": config["source_expert"],
                      "params": config.get("source_expert_params", {})},
                timeout=15,
            ).json()
            data = resp.get("result", {})
            return data.get("texts", []) if isinstance(data, dict) else []
        except Exception:
            return []

    return []
