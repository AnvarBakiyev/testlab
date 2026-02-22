# Personal AGI — Test Status

*Updated: 2026-02-22 22:20*

## Summary

| Suite | Result | Updated |
|-------|--------|---------|
| OK System Health | 3/3 pass, 0 warn, 0 fail | 2026-02-22 17:20 |
| OK Pipeline Integrity | 6/6 pass, 0 warn, 0 fail | 2026-02-22 17:06 |
| OK UX & Text Quality | 3/3 pass, 0 warn, 0 fail | 2026-02-22 17:06 |
| WARN E2E Scenarios | 3/4 pass, 1 warn, 0 fail | 2026-02-22 17:16 |
| OK Monitoring | 4/4 pass, 0 warn, 0 fail | 2026-02-22 17:20 |
| OK LLM Decision Judge | 1/1 pass, 0 warn, 0 fail | 2026-02-22 17:13 |
| OK CC & Memory Health | 8/8 pass, 0 warn, 0 fail | 2026-02-22 17:13 |

## Details

OK System Health

- OK health_check: HTTP 200 — http://localhost:9100/api/health
- OK process_monitor: pgrep: 4 процесс(ов) PID=50439
- OK sqlite_inspector: last=0.0ч назад

OK Pipeline Integrity

- OK sqlite_inspector: last=-5.0ч назад
- OK pipeline_completeness: Все 1265 записей обработаны
- OK idempotency: За 24ч: 13 уникальных уведомлений
- OK canary_check: Last cycle: 0.2 min ago
- OK dead_letter_check: No lost events in last 24h
- OK ooda_phase_balance: Balance OK: 14 events → 7 actions

OK UX & Text Quality

- OK text_quality: Все 30 текстов чисты
- OK telegram_callback_check: No pending actions (system idle)
- OK command_center_api_check: CC API 4 methods OK | overview_persons=1884, pending_count=9, sync_has_gmail=True, dronor_status=healthy

WARN E2E Scenarios

- OK health_check: HTTP 200 — http://localhost:9100/api/health
- OK sqlite_inspector: last=0.0ч назад | rows=4430
- WARN kg_health: Person: 1886 | Org: 297 | Comm: 5926 | Name-дублей: 11
  > Дублей по имени: 11
- OK telegram_ping: Доставлено (msg_id=76)

OK Monitoring

- OK watcher_freshness: Gmail=0мин назад | GDrive=0мин назад
- OK daemon_errors: Лог чистый
- OK cars_activity: Решений: 1139 за 24ч | Циклов: 3317 | Последний: 2026-02-22T17:19
- OK pending_aging: Pending: 0 | Зависших >48ч: 0

OK LLM Decision Judge

- OK llm_judge: LLM judge: 7/7 OK — All decisions are reasonable—memory maintenance operations are standard, and dismissals appropriatel

OK CC & Memory Health

- OK memory_block_freshness: All 3 blocks fresh (within 7d)
- OK memory_writers_active: All 4 memory writers active within 48h
- OK kg_freshness: KG freshness OK - updated 0 day(s) ago
- OK cc_memory_renderer: All 3 blocks clean
- OK cc_log_leakage: All 50 decisions clean
- OK cc_pending_duplicates: All 0 pending actions are unique
- OK pending_text_quality: No pending actions to check
- OK pending_buttons_check: 0 actions with buttons — all within limits

