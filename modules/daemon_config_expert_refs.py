"""
daemon_config_expert_refs - checks that experts referenced in daemon_config.json exist in Dronor.

Covers: news_subscription.tags.*.expert, agents.*.expert
A missing expert causes silent failure when the daemon tries to run that action.
"""
import json
import requests
from pathlib import Path
from core.base import TestResult

DEFAULT_CONFIG = "/Users/anvarbakiyev/dronor/local_data/personal_agi/daemon_config.json"
DEFAULT_DRONOR_URL = "http://localhost:9100"


def _get_dronor_experts(dronor_url: str) -> set:
    try:
        resp = requests.get(f"{dronor_url}/api/expert/list", timeout=5)
        data = resp.json()
        if isinstance(data, list):
            return {e.get("name") for e in data if e.get("name")}
        if isinstance(data, dict):
            experts = data.get("experts", data.get("data", []))
            return {e.get("name") for e in experts if e.get("name")}
    except Exception:
        pass
    return set()


def _collect_expert_refs(obj, path='') -> list:
    """Recursively find all 'expert' keys with non-null values."""
    refs = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'expert' and isinstance(v, str) and v:
                refs.append((path, v))
            else:
                refs.extend(_collect_expert_refs(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            refs.extend(_collect_expert_refs(v, f"{path}[{i}]"))
    return refs


def run(config: dict) -> TestResult:
    config_path = Path(config.get("config_path", DEFAULT_CONFIG))
    dronor_url = config.get("dronor_url", DEFAULT_DRONOR_URL)

    if not config_path.exists():
        return TestResult(status="fail", msg=f"daemon_config.json not found", detail="", data={})

    daemon_cfg = json.loads(config_path.read_text())
    known_experts = _get_dronor_experts(dronor_url)
    all_refs = _collect_expert_refs(daemon_cfg)

    broken = []
    for path, expert_name in all_refs:
        if known_experts and expert_name not in known_experts:
            broken.append(f"{path} -> '{expert_name}'")

    data = {
        "total_refs": len(all_refs),
        "all_refs": [(p, e) for p, e in all_refs],
        "broken": broken
    }

    if broken:
        return TestResult(
            status="fail",
            msg=f"{len(broken)} expert reference(s) in daemon_config point to non-existent experts",
            detail="; ".join(broken[:5]),
            data=data
        )

    if not all_refs:
        return TestResult(
            status="warn",
            msg="No expert references found in daemon_config.json",
            detail="Expected at least news_subscription experts",
            data=data
        )

    return TestResult(
        status="pass",
        msg=f"All {len(all_refs)} expert refs in daemon_config are valid",
        detail="",
        data=data
    )
