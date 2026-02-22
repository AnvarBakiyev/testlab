"""
connector_config_check - checks that all connectors have required expert fields configured.

Finds connectors where expert_deep_scan or expert_quick_sync is None/missing.
Also verifies that referenced experts actually exist in Dronor.
"""
import json
import requests
from pathlib import Path
from core.base import TestResult

DEFAULT_CONNECTORS = "/Users/anvarbakiyev/dronor/local_data/personal_agi/connectors.json"
DEFAULT_DRONOR_URL = "http://localhost:9100"


def _get_dronor_experts(dronor_url: str) -> set:
    """Fetch list of expert names from Dronor API."""
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


def run(config: dict) -> TestResult:
    connectors_path = Path(config.get("connectors_json", DEFAULT_CONNECTORS))
    dronor_url = config.get("dronor_url", DEFAULT_DRONOR_URL)
    check_experts_exist = config.get("check_experts_exist", True)

    if not connectors_path.exists():
        return TestResult(
            status="fail",
            msg=f"connectors.json not found: {connectors_path}",
            detail="",
            data={}
        )

    data = json.loads(connectors_path.read_text())
    connectors = data.get("connectors", [])

    if not connectors:
        return TestResult(status="warn", msg="No connectors found in config", detail="", data={})

    # Fetch known experts from Dronor
    known_experts = set()
    if check_experts_exist:
        known_experts = _get_dronor_experts(dronor_url)

    missing_deep = []       # connector has no expert_deep_scan configured
    missing_quick = []      # connector has no expert_quick_sync configured
    broken_refs = []        # expert name set but doesn't exist in Dronor

    for conn in connectors:
        cid = str(conn.get("id", "unknown"))
        deep = conn.get("expert_deep_scan")
        quick = conn.get("expert_quick_sync")

        if not deep:
            missing_deep.append(cid)
        elif known_experts and deep not in known_experts:
            broken_refs.append(f"{cid}.expert_deep_scan={deep}")

        if not quick:
            missing_quick.append(cid)
        elif known_experts and quick not in known_experts:
            broken_refs.append(f"{cid}.expert_quick_sync={quick}")

    total = len(connectors)
    data_out = {
        "total": total,
        "missing_deep": missing_deep,
        "missing_quick": missing_quick,
        "broken_refs": broken_refs,
    }

    # Broken refs = FAIL (expert named but doesn't exist — silent crash)
    if broken_refs:
        return TestResult(
            status="fail",
            msg=f"{len(broken_refs)} connector(s) reference non-existent experts",
            detail="; ".join(broken_refs[:3]),
            data=data_out
        )

    # Missing deep = WARN (Deep Scan button will show error)
    if missing_deep:
        return TestResult(
            status="warn",
            msg=f"{len(missing_deep)}/{total} connectors missing expert_deep_scan",
            detail="Missing: " + ", ".join(missing_deep),
            data=data_out
        )

    # Missing quick = WARN
    if missing_quick:
        return TestResult(
            status="warn",
            msg=f"{len(missing_quick)}/{total} connectors missing expert_quick_sync",
            detail="Missing: " + ", ".join(missing_quick),
            data=data_out
        )

    return TestResult(
        status="pass",
        msg=f"All {total} connectors fully configured",
        detail="",
        data=data_out
    )
