"""daemon_import_check — smoke test: agi_daemon.py must import cleanly.

Catches NameError at startup before daemon runs. Runs import in subprocess
to avoid polluting the testlab process and to match real daemon startup.
"""
import subprocess
import sys
import os
from core.base import TestResult

APPS_DIR = '/Users/anvarbakiyev/dronor/apps'


def run(config: dict) -> TestResult:
    result = subprocess.run(
        [sys.executable, '-c', 'import agi_daemon'],
        capture_output=True,
        text=True,
        cwd=APPS_DIR,
        timeout=30,
    )
    if result.returncode == 0:
        return TestResult(
            'pass',
            'agi_daemon.py imports cleanly',
            '',
        )
    error_lines = (result.stderr or result.stdout).strip().splitlines()
    short = error_lines[-1] if error_lines else 'unknown error'
    return TestResult(
        'fail',
        f'agi_daemon import failed: {short}',
        result.stderr or result.stdout,
    )
