"""
E2E: Dronor API health — CC can reach localhost:9100.
"""
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

DRONOR_API = "http://localhost:9100"
ACCEPTED_STATUSES = {"ok", "healthy"}

def run(cfg: dict):
    from core.base import TestResult
    try:
        req = Request(f"{DRONOR_API}/api/health")
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        status = data.get("status", "")
        if status not in ACCEPTED_STATUSES:
            return TestResult("warn",
                f"Dronor API responded but status='{status}'",
                data=data)

        return TestResult("pass",
            f"Dronor API reachable — status={status}",
            data={"status": status})
    except URLError as e:
        return TestResult("fail",
            f"Dronor API unreachable: {e} — CC cannot run any experts",
            detail="Check that Dronor is running on port 9100")
    except Exception as e:
        return TestResult("fail", f"Dronor API check crashed: {e}")
