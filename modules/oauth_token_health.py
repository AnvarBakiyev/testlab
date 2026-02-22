"""
oauth_token_health - checks Google OAuth token expiry status.

A expired token causes ALL Google connectors (Gmail, Drive, Contacts, Calendar)
to silently fail without clear error messages in the UI.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from core.base import TestResult

DEFAULT_TOKEN_PATH = "/Users/anvarbakiyev/dronor/local_data/personal_agi/google_oauth_token.json"
WARN_HOURS = 24   # warn if expires within 24h


def run(config: dict) -> TestResult:
    token_path = Path(config.get("token_path", DEFAULT_TOKEN_PATH))

    if not token_path.exists():
        return TestResult(
            status="fail",
            msg="google_oauth_token.json not found",
            detail="Google connectors cannot authenticate without this file",
            data={}
        )

    try:
        token = json.loads(token_path.read_text())
    except Exception as e:
        return TestResult(status="fail", msg=f"Cannot parse token file: {e}", detail="", data={})

    expiry_str = token.get("expiry")
    if not expiry_str:
        return TestResult(
            status="warn",
            msg="OAuth token has no expiry field",
            detail="Cannot determine if token is valid",
            data={"keys": list(token.keys())}
        )

    # Parse ISO format
    try:
        expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
    except Exception as e:
        return TestResult(status="warn", msg=f"Cannot parse expiry date: {expiry_str}", detail=str(e), data={})

    now = datetime.now(timezone.utc)
    delta = expiry - now
    hours_until_expiry = delta.total_seconds() / 3600
    days_expired = abs(delta.total_seconds()) / 86400

    data = {
        "expiry": expiry_str,
        "hours_until_expiry": round(hours_until_expiry, 1),
        "has_refresh_token": bool(token.get("refresh_token"))
    }

    if hours_until_expiry < 0:
        return TestResult(
            status="fail",
            msg=f"OAuth token EXPIRED {days_expired:.1f} days ago",
            detail=f"Expired: {expiry_str}. All Google connectors (Gmail, Drive, Contacts, Calendar) will fail silently.",
            data=data
        )

    if hours_until_expiry < WARN_HOURS:
        return TestResult(
            status="warn",
            msg=f"OAuth token expires in {hours_until_expiry:.1f} hours",
            detail=f"Expires: {expiry_str}",
            data=data
        )

    return TestResult(
        status="pass",
        msg=f"OAuth token valid for {hours_until_expiry:.0f} more hours",
        detail="",
        data=data
    )
