"""
modules/dronor_expert.py — Any Dronor expert as a test.
config: expert, params={}, expect={}, expect_not={}, timeout=30
"""
import json
import requests
from core.base import TestResult

def run(config: dict) -> TestResult:
    expert = config["expert"]
    params = config.get("params", {})
    expect = config.get("expect", {})
    expect_not = config.get("expect_not", {})
    url = config.get("dronor_url", "http://localhost:9100")
    timeout = config.get("timeout", 30)
    try:
        resp = requests.post(f"{url}/api/expert/run",
                             json={"expert_name": expert, "params": params},
                             timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return TestResult(status="fail", msg=f"{expert}: timeout {timeout}s")
    except Exception as e:
        return TestResult(status="fail", msg=f"{expert}: HTTP error — {e}")
    if data.get("status") == "error":
        return TestResult(status="fail", msg=f"{expert}: execution error",
                          detail=str(data.get("error", ""))[:300])
    result = data.get("result", {})
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            result = {"raw": result}
    failures = []
    for k, v in expect.items():
        actual = result.get(k) if isinstance(result, dict) else None
        if actual != v:
            failures.append(f"{k}: ожидали={v!r} получили={actual!r}")
    for k, v in expect_not.items():
        actual = result.get(k) if isinstance(result, dict) else None
        if actual == v:
            failures.append(f"{k}: не должен быть {v!r}")
    if failures:
        return TestResult(status="fail",
                          msg=f"{expert}: {len(failures)} assertions failed",
                          detail=" | ".join(failures), data={"result": result})
    return TestResult(status="pass", msg=f"{expert}: OK", data={"result": result})
