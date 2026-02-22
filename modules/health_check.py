"""
modules/health_check.py — HTTP endpoint alive?
config: url, timeout=5, expect_status=200
"""
import requests
from core.base import TestResult

def run(config: dict) -> TestResult:
    url = config["url"]
    timeout = config.get("timeout", 5)
    expect = config.get("expect_status", 200)
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == expect:
            return TestResult(status="pass", msg=f"HTTP {resp.status_code} — {url}",
                              data={"status_code": resp.status_code})
        return TestResult(status="fail",
                          msg=f"HTTP {resp.status_code} (ожидали {expect}) — {url}")
    except requests.exceptions.Timeout:
        return TestResult(status="fail", msg=f"Timeout {timeout}s — {url}")
    except requests.exceptions.ConnectionError:
        return TestResult(status="fail", msg=f"Connection refused — {url}")
    except Exception as e:
        return TestResult(status="fail", msg=f"Error: {e}")
