#!/usr/bin/env python3
"""
AGI Command Center - Full Audit Runner
Runs all audit modules and generates HTML report.
"""
import sys
import json
import importlib.util
from pathlib import Path
from datetime import datetime

MODULES_DIR = Path(__file__).parent / 'modules'
REPORT_OUT = Path('/Users/anvarbakiyev/Desktop/agi_audit_report.html')

AUDIT_SUITE = [
    # --- Pending Actions ---
    ('pending_duplicates_deep',  'Pending: Duplicate Actions',     'Pending Actions'),
    ('pending_age_audit',        'Pending: Stale Actions (Age)',   'Pending Actions'),
    ('pending_orphans_audit',    'Pending: Data Integrity',        'Pending Actions'),
    ('draft_quality_audit',      'Pending: Draft Quality',         'Pending Actions'),
    # --- CARS & Feedback ---
    ('cars_distribution_audit',  'CARS: Score Distribution',       'CARS & Feedback'),
    ('feedback_loop_audit',      'CARS: Feedback Loop',            'CARS & Feedback'),
    # --- Pipeline & Events ---
    ('events_pipeline_audit',    'Events: Pipeline Health',        'Pipeline & Events'),
    # --- Daemon ---
    ('daemon_health_audit',      'Daemon: Health & Throughput',    'Daemon'),
    # --- System ---
    ('auto_reply_audit',         'Auto-Reply: System Health',      'System'),
    ('knowledge_db_audit',       'Knowledge: DB Integrity',        'System'),
    # --- Memory (existing) ---
    ('memory_block_freshness',   'Memory: Block Freshness',        'Memory'),
    ('memory_writers_active',    'Memory: Writers Active',         'Memory'),
    ('update_kg_wiring',         'Memory: KG Wiring',              'Memory'),
    ('connector_config_check',   'Connectors: Config Check',       'Connectors'),
    ('daemon_activity_check',    'Daemon: Activity Check',         'Daemon'),
]

def load_module(name):
    path = MODULES_DIR / f'{name}.py'
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_module(name, label):
    try:
        mod = load_module(name)
        if mod is None:
            return {'status': 'skip', 'msg': f'Module file not found: {name}.py', 'details': None}
        result = mod.run({})
        return {'status': result.status, 'msg': result.msg,
                'details': result.details if hasattr(result, 'details') else None}
    except Exception as e:
        return {'status': 'error', 'msg': str(e), 'details': None}

def status_color(s):
    return {'pass': '#22c55e', 'fail': '#ef4444', 'warn': '#f59e0b',
            'error': '#a855f7', 'skip': '#6b7280'}.get(s, '#6b7280')

def status_icon(s):
    return {'pass': '✅', 'fail': '❌', 'warn': '⚠️', 'error': '💥', 'skip': '⏭️'}.get(s, '?')

def build_html(results_by_group, summary):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total = summary['total']
    passed = summary['pass']
    failed = summary['fail']
    warned = summary['warn']
    errors = summary['error']

    overall = 'HEALTHY' if failed == 0 and errors == 0 else ('DEGRADED' if failed <= 3 else 'CRITICAL')
    overall_color = '#22c55e' if overall == 'HEALTHY' else ('#f59e0b' if overall == 'DEGRADED' else '#ef4444')

    groups_html = ''
    for group, items in results_by_group.items():
        rows = ''
        for label, name, res in items:
            sc = status_color(res['status'])
            icon = status_icon(res['status'])
            details_html = ''
            if res['details']:
                try:
                    d = res['details']
                    if isinstance(d, dict):
                        rows_detail = ''.join(
                            f'<tr><td style="padding:3px 8px;color:#94a3b8;font-size:12px">{k}</td>'
                            f'<td style="padding:3px 8px;font-size:12px;word-break:break-all">'
                            f'{json.dumps(v, ensure_ascii=False)[:200] if not isinstance(v, (str,int,float,bool)) else v}</td></tr>'
                            for k, v in d.items() if v is not None and v != [] and v != {}
                        )
                        if rows_detail:
                            details_html = f'<table style="width:100%;border-collapse:collapse;margin-top:6px">{rows_detail}</table>'
                except:
                    pass

            rows += f'''
            <tr style="border-bottom:1px solid #1e293b">
              <td style="padding:12px 16px;width:40px;text-align:center;font-size:18px">{icon}</td>
              <td style="padding:12px 16px">
                <div style="font-weight:600;color:#e2e8f0">{label}</div>
                <div style="color:{sc};font-size:13px;margin-top:2px">{res['msg']}</div>
                {details_html}
              </td>
              <td style="padding:12px 16px;width:80px;text-align:center">
                <span style="background:{sc}22;color:{sc};padding:3px 10px;
                  border-radius:12px;font-size:12px;font-weight:700;border:1px solid {sc}44">
                  {res['status'].upper()}
                </span>
              </td>
            </tr>'''

        groups_html += f'''
        <div style="margin-bottom:32px">
          <h2 style="color:#94a3b8;font-size:13px;font-weight:700;letter-spacing:2px;
            text-transform:uppercase;margin-bottom:12px;padding-left:4px">{group}</h2>
          <div style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;overflow:hidden">
            <table style="width:100%;border-collapse:collapse">{rows}</table>
          </div>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AGI Command Center — Audit Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #020817; color: #e2e8f0; font-family: 'SF Mono', 'Fira Code', monospace;
    min-height: 100vh; padding: 40px 24px; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  .header {{ margin-bottom: 40px; }}
  .badge {{ display: inline-block; padding: 6px 18px; border-radius: 999px;
    font-size: 13px; font-weight: 800; letter-spacing: 1px;
    background: {overall_color}22; color: {overall_color};
    border: 1px solid {overall_color}55; margin-bottom: 16px; }}
  .title {{ font-size: 28px; font-weight: 800; color: #f1f5f9; margin-bottom: 6px; }}
  .subtitle {{ color: #475569; font-size: 13px; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 40px; }}
  .stat {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 10px;
    padding: 16px; text-align: center; }}
  .stat-num {{ font-size: 28px; font-weight: 800; }}
  .stat-label {{ font-size: 11px; color: #64748b; text-transform: uppercase;
    letter-spacing: 1px; margin-top: 4px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="badge">{overall}</div>
    <div class="title">AGI Command Center</div>
    <div class="title" style="color:#64748b;font-size:20px">Full System Audit</div>
    <div class="subtitle" style="margin-top:8px">Generated: {now}</div>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-num" style="color:#e2e8f0">{total}</div>
      <div class="stat-label">Total Checks</div></div>
    <div class="stat"><div class="stat-num" style="color:#22c55e">{passed}</div>
      <div class="stat-label">Passed</div></div>
    <div class="stat"><div class="stat-num" style="color:#f59e0b">{warned}</div>
      <div class="stat-label">Warnings</div></div>
    <div class="stat"><div class="stat-num" style="color:#ef4444">{failed + errors}</div>
      <div class="stat-label">Failed</div></div>
  </div>

  {groups_html}

  <div style="text-align:center;color:#1e293b;font-size:11px;margin-top:40px">
    AGI TestLab v2.0 — Personal AGI Audit Suite
  </div>
</div>
</body>
</html>'''

def main():
    print('\n🔍 AGI Command Center — Full Audit')
    print('=' * 50)

    results_by_group = {}
    summary = {'total': 0, 'pass': 0, 'fail': 0, 'warn': 0, 'error': 0, 'skip': 0}

    for name, label, group in AUDIT_SUITE:
        sys.stdout.write(f'  Running {label}... ')
        sys.stdout.flush()
        res = run_module(name, label)
        icon = status_icon(res['status'])
        print(f'{icon} {res["status"].upper()} — {res["msg"]}')

        if group not in results_by_group:
            results_by_group[group] = []
        results_by_group[group].append((label, name, res))

        summary['total'] += 1
        summary[res['status']] = summary.get(res['status'], 0) + 1

    print('\n' + '=' * 50)
    print(f'  Results: {summary["pass"]} pass, {summary["warn"]} warn, '
          f'{summary["fail"]} fail, {summary["error"]} error, {summary.get("skip",0)} skip')

    html = build_html(results_by_group, summary)
    REPORT_OUT.write_text(html, encoding='utf-8')
    print(f'\n📄 Report saved: {REPORT_OUT}')
    print('   Open it in your browser.\n')

if __name__ == '__main__':
    main()
