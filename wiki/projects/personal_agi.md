# Personal AGI — Test Status

*Updated: 2026-02-22 23:32*

## Summary

| Suite | Result | Updated |
|-------|--------|---------|
| OK System Health | 3/3 pass, 0 warn, 0 fail | 2026-02-22 18:32 |
| WARN Pipeline Integrity | 4/6 pass, 2 warn, 0 fail | 2026-02-22 18:32 |
| OK UX & Text Quality | 3/3 pass, 0 warn, 0 fail | 2026-02-22 18:32 |
| WARN E2E Scenarios | 3/4 pass, 1 warn, 0 fail | 2026-02-22 18:32 |
| OK Monitoring | 4/4 pass, 0 warn, 0 fail | 2026-02-22 18:32 |
| WARN LLM Decision Judge | 0/1 pass, 1 warn, 0 fail | 2026-02-22 18:32 |
| WARN CC & Memory Health | 11/12 pass, 1 warn, 0 fail | 2026-02-22 18:31 |

## Details

OK System Health

- OK health_check: HTTP 200 — http://localhost:9100/api/health
- OK process_monitor: pgrep: 4 процесс(ов) PID=50439
- OK sqlite_inspector: last=0.0ч назад

WARN Pipeline Integrity

- OK sqlite_inspector: last=-5.0ч назад
- WARN pipeline_completeness: Потеряно 1 (0.1%) — в норме
- OK idempotency: За 24ч: 19 уникальных уведомлений
- OK canary_check: Last cycle: 0.2 min ago
- OK dead_letter_check: No lost events in last 24h
- WARN ooda_phase_balance: Low action ratio: 0.000 (min 0.01)
  > Last 20 runs: 6 events in, 0 actions out | 5 runs had events, 0 produced actions

OK UX & Text Quality

- OK text_quality: Все 30 текстов чисты
- OK telegram_callback_check: No pending actions (system idle)
- OK command_center_api_check: CC API 4 methods OK | overview_persons=1886, pending_count=15, sync_has_gmail=True, dronor_status=healthy

WARN E2E Scenarios

- OK health_check: HTTP 200 — http://localhost:9100/api/health
- OK sqlite_inspector: last=0.0ч назад | rows=4583
- WARN kg_health: Person: 1886 | Org: 297 | Comm: 5926 | Name-дублей: 4
  > Дублей по имени: 4
- OK telegram_ping: Доставлено (msg_id=90)

OK Monitoring

- OK watcher_freshness: Gmail=0мин назад | GDrive=0мин назад
- OK daemon_errors: Лог чистый
- OK cars_activity: Решений: 1211 за 24ч | Циклов: 3462 | Последний: 2026-02-22T18:31
- OK pending_aging: Pending: 0 | Зависших >48ч: 0

WARN LLM Decision Judge

- WARN llm_judge: LLM judge: 0 bad, 4 warn / 7 — Most decisions are reasonable, but several dismissals rely on volume and assumpt

WARN CC & Memory Health

- OK memory_block_freshness: All 3 blocks fresh (within 7d)
- OK memory_writers_active: All 4 memory writers active within 48h
- OK kg_freshness: KG freshness OK - updated 0 day(s) ago
- OK cc_memory_renderer: All 3 blocks clean
- OK cc_log_leakage: All 50 decisions clean
- OK cc_pending_duplicates: All 0 pending actions are unique
- OK pending_text_quality: No pending actions to check
- OK pending_buttons_check: 0 actions with buttons — all within limits
- OK connector_config_check: All 9 connectors fully configured
- WARN oauth_token_health: OAuth token expires in 0.7 hours
  > Expires: 2026-02-22T19:12:21.995162Z
- OK daemon_config_expert_refs: All 4 expert refs in daemon_config are valid
- OK daemon_activity_check: Daemon active: 72 decisions/hour, last 27min ago

