# Personal AGI — Test Status

*Updated: 2026-02-22 21:20*

## Summary

| Suite | Result | Updated |
|-------|--------|---------|
| OK System Health | 3/3 pass, 0 warn, 0 fail | 2026-02-22 16:20 |
| OK Pipeline Integrity | 6/6 pass, 0 warn, 0 fail | 2026-02-22 16:00 |
| OK UX & Text Quality | 3/3 pass, 0 warn, 0 fail | 2026-02-22 16:00 |
| WARN E2E Scenarios | 3/4 pass, 1 warn, 0 fail | 2026-02-22 13:14 |
| OK Monitoring | 4/4 pass, 0 warn, 0 fail | 2026-02-22 16:20 |
| WARN LLM Decision Judge | 0/1 pass, 1 warn, 0 fail | 2026-02-22 15:10 |

## Details

OK System Health

- OK health_check: HTTP 200 — http://localhost:9100/api/health
- OK process_monitor: pgrep: 4 процесс(ов) PID=50439
- OK sqlite_inspector: last=0.0ч назад

OK Pipeline Integrity

- OK sqlite_inspector: last=-5.0ч назад
- OK pipeline_completeness: Все 1084 записей обработаны
- OK idempotency: За 24ч: 13 уникальных уведомлений
- OK canary_check: Last cycle: 0.3 min ago
- OK dead_letter_check: No lost events in last 24h
- OK ooda_phase_balance: Balance OK: 4 events → 2 actions

OK UX & Text Quality

- OK text_quality: Все 30 текстов чисты
- OK telegram_callback_check: No pending actions (system idle)
- OK command_center_api_check: CC API 4 methods OK | overview_persons=1884, pending_count=9, sync_has_gmail=True, dronor_status=healthy

WARN E2E Scenarios

- OK health_check: HTTP 200 — http://localhost:9100/api/health
- OK sqlite_inspector: last=0.0ч назад | rows=3912
- WARN kg_health: Person: 1886 | Org: 297 | Comm: 5926 | Name-дублей: 11
  > Дублей по имени: 11
- OK telegram_ping: Доставлено (msg_id=57)

OK Monitoring

- OK watcher_freshness: Gmail=0мин назад | GDrive=0мин назад
- OK daemon_errors: Лог чистый
- OK cars_activity: Решений: 1099 за 24ч | Циклов: 3186 | Последний: 2026-02-22T16:19
- OK pending_aging: Pending: 0 | Зависших >48ч: 0

WARN LLM Decision Judge

- WARN llm_judge: LLM judge: 0 bad, 4 warn / 7 — Pattern of aggressive dismissals with very high confidence (0.98-0.99) raises co

