# Personal AGI — Test Status

*Updated: 2026-02-22 23:15*

## Summary

| Suite | Result | Updated |
|-------|--------|---------|
| OK System Health | 3/3 pass, 0 warn, 0 fail | 2026-02-22 18:15 |
| WARN Pipeline Integrity | 5/6 pass, 1 warn, 0 fail | 2026-02-22 18:00 |
| OK UX & Text Quality | 3/3 pass, 0 warn, 0 fail | 2026-02-22 18:00 |
| WARN E2E Scenarios | 3/4 pass, 1 warn, 0 fail | 2026-02-22 17:42 |
| OK Monitoring | 4/4 pass, 0 warn, 0 fail | 2026-02-22 18:15 |
| OK LLM Decision Judge | 1/1 pass, 0 warn, 0 fail | 2026-02-22 17:24 |
| OK CC & Memory Health | 9/9 pass, 0 warn, 0 fail | 2026-02-22 17:35 |

## Details

OK System Health

- OK health_check: HTTP 200 — http://localhost:9100/api/health
- OK process_monitor: pgrep: 4 процесс(ов) PID=50439
- OK sqlite_inspector: last=0.0ч назад

WARN Pipeline Integrity

- OK sqlite_inspector: last=-5.0ч назад
- WARN pipeline_completeness: Потеряно 50 (3.3%) — в норме
- OK idempotency: За 24ч: 13 уникальных уведомлений
- OK canary_check: Last cycle: 0.1 min ago
- OK dead_letter_check: No lost events in last 24h
- OK ooda_phase_balance: Balance OK: 105 events → 29 actions

OK UX & Text Quality

- OK text_quality: Все 30 текстов чисты
- OK telegram_callback_check: No pending actions (system idle)
- OK command_center_api_check: CC API 4 methods OK | overview_persons=1886, pending_count=9, sync_has_gmail=True, dronor_status=healthy

WARN E2E Scenarios

- OK health_check: HTTP 200 — http://localhost:9100/api/health
- OK sqlite_inspector: last=0.0ч назад | rows=4485
- WARN kg_health: Person: 1886 | Org: 297 | Comm: 5926 | Name-дублей: 4
  > Дублей по имени: 4
- OK telegram_ping: Доставлено (msg_id=86)

OK Monitoring

- OK watcher_freshness: Gmail=0мин назад | GDrive=0мин назад
- OK daemon_errors: Лог чистый
- OK cars_activity: Решений: 1211 за 24ч | Циклов: 3424 | Последний: 2026-02-22T18:14
- OK pending_aging: Pending: 0 | Зависших >48ч: 0

OK LLM Decision Judge

- OK llm_judge: LLM judge: 7/7 OK — All decisions are sound—routine memory maintenance operations and appropriate dismissals of non-acti

OK CC & Memory Health

- OK memory_block_freshness: All 3 blocks fresh (within 7d)
- OK memory_writers_active: All 4 memory writers active within 48h
- OK kg_freshness: KG freshness OK - updated 0 day(s) ago
- OK cc_memory_renderer: All 3 blocks clean
- OK cc_log_leakage: All 50 decisions clean
- OK cc_pending_duplicates: All 0 pending actions are unique
- OK pending_text_quality: No pending actions to check
- OK pending_buttons_check: 0 actions with buttons — all within limits
- OK connector_config_check: All 9 connectors fully configured

