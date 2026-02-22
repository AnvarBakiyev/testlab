"""
modules/command_center_api_check.py — Test Command Center Python API.

Imports the Api class from agi_command_center.py directly
and calls key methods, checking response structure.
No UI, no browser — pure Python API contract test.

Config:
  cc_path: str        — absolute path to agi_command_center.py
  min_persons: int    — minimum persons in KG overview (default 10)
  methods: list[str]  — which methods to test
"""
import sys
import json
import importlib.util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base import TestResult

DEFAULT_METHODS = ['get_overview', 'get_pending_actions', 'get_sync_state', 'dronor_health']


def _load_api_class(cc_path: str):
    spec = importlib.util.spec_from_file_location('agi_command_center', cc_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Api


def _parse(raw):
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return None
    return None


def run(config: dict) -> TestResult:
    cc_path = config.get('cc_path', '')
    min_persons = config.get('min_persons', 10)
    methods = config.get('methods', DEFAULT_METHODS)

    if not cc_path or not Path(cc_path).exists():
        return TestResult(status='fail', msg=f'agi_command_center.py not found: {cc_path}')

    try:
        ApiClass = _load_api_class(cc_path)
        api = ApiClass()
    except Exception as e:
        return TestResult(status='fail', msg=f'Failed to load Api class: {str(e)[:120]}')

    results = {}
    failures = []
    warnings = []

    if 'get_overview' in methods:
        try:
            data = _parse(api.get_overview())
            if data is None:
                failures.append('get_overview: None or unparseable')
            else:
                persons = data.get('total_persons', data.get('persons', 0))
                if persons < min_persons:
                    warnings.append(f'get_overview: only {persons} persons (min {min_persons})')
                results['overview_persons'] = persons
        except Exception as e:
            failures.append(f'get_overview: {str(e)[:80]}')

    if 'get_pending_actions' in methods:
        try:
            data = _parse(api.get_pending_actions())
            if data is None:
                failures.append('get_pending_actions: None or unparseable')
            else:
                results['pending_count'] = len(data) if isinstance(data, list) else '?'  
        except Exception as e:
            failures.append(f'get_pending_actions: {str(e)[:80]}')

    if 'get_sync_state' in methods:
        try:
            data = _parse(api.get_sync_state())
            if data is None:
                failures.append('get_sync_state: None or unparseable')
            else:
                has_gmail = 'gmail' in str(data).lower()
                if not has_gmail:
                    warnings.append('get_sync_state: no gmail key in response')
                results['sync_has_gmail'] = has_gmail
        except Exception as e:
            failures.append(f'get_sync_state: {str(e)[:80]}')

    if 'dronor_health' in methods:
        try:
            data = _parse(api.dronor_health())
            if data is None:
                warnings.append('dronor_health: None (Dronor may be offline)')
            else:
                status = data.get('status', '')
                if status not in ('ok', 'running', 'healthy'):
                    warnings.append(f'dronor_health: unexpected status "{status}"')
                results['dronor_status'] = status
        except Exception as e:
            warnings.append(f'dronor_health: {str(e)[:80]}')

    if failures:
        return TestResult(
            status='fail',
            msg=f'CC API: {len(failures)} methods failed',
            detail=' | '.join(failures[:3]),
            data={'results': results, 'failures': failures, 'warnings': warnings},
        )
    if warnings:
        return TestResult(
            status='warn',
            msg=f'CC API OK, warnings: {len(warnings)}',
            detail=' | '.join(warnings[:2]),
            data={'results': results, 'warnings': warnings},
        )
    summary = ', '.join(f'{k}={v}' for k, v in results.items())
    return TestResult(
        status='pass',
        msg=f'CC API {len(methods)} methods OK | {summary}',
        data={'results': results},
    )
