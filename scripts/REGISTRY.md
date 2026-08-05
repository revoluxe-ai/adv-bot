# scripts/ readiness registry

Ledger for `/opsx-scripts` (daily) and `/opsx-scripts-prepare` (infra).

Human display: `Title (path)` — see `.cursor/commands/opsx-human-label-display.md`.

Do not set `battle_tested=YES` without Owner `RECORD_BATTLE GO` + evidence.

## Schema

| title | path | runnable | tests | battle_tested | last_local_at | last_cluster_at | last_image_ref | notes |
|-------|------|----------|-------|---------------|---------------|-----------------|----------------|-------|
| short human name | `scripts/<entrypoint>` | `UNKNOWN` \| `WORKS` \| `BROKEN` | `NONE` \| `PARTIAL` \| `COVERED` | `NO` \| `YES` | ISO UTC or `-` | ISO UTC or `-` | image ref or `-` | short |

## Entrypoints

| title | path | runnable | tests | battle_tested | last_local_at | last_cluster_at | last_image_ref | notes |
|-------|------|----------|-------|---------------|---------------|-----------------|----------------|-------|
| Backfill L2 | scripts/backfill_l2.py | UNKNOWN | NONE | NO | - | - | - | |
| Backfill MV for keyword clusters | scripts/backfill_mv_for_keyword_clusters.py | UNKNOWN | NONE | NO | - | - | - | |
| Delete user by Telegram id | scripts/delete_user_by_telegram_id.py | UNKNOWN | NONE | NO | - | - | - | |
| Enable individual keywords for new tariff cabinets | scripts/enable_individual_keywords_for_new_tariff_cabinets.py | UNKNOWN | NONE | NO | - | - | - | |
| Export last WB movements | scripts/export_last_wb_movements.py | UNKNOWN | NONE | NO | - | - | - | |
| Export non-zero balance users | scripts/export_non_zero_balance_users.py | UNKNOWN | NONE | NO | - | - | - | |
| Export single-article campaign stats | scripts/export_single_article_campaigns_stats.py | UNKNOWN | NONE | NO | - | - | - | |
| Fill bid decision | scripts/fill_bid_decision.py | UNKNOWN | NONE | NO | - | - | - | |
| Get dialogs from TG export | scripts/get_dialogs_from_tg_export.py | UNKNOWN | NONE | NO | - | - | - | |
| Get users | scripts/get_users/get_users.py | UNKNOWN | NONE | NO | - | - | - | |
| Get users for shop (worst adv) | scripts/get_worst_adv/get_users_for_shop_id.py | UNKNOWN | NONE | NO | - | - | - | |
| Insert adv deltas | scripts/insert_adv_deltas.py | UNKNOWN | NONE | NO | - | - | - | |
| Install error monitoring | scripts/INSTALL_ERROR_MONITORING.sh | UNKNOWN | NONE | NO | - | - | - | shell; Job template is python-oriented |
| Prod DB migrate then rollout | scripts/Invoke-ProdDbMigrateThenRollout.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |
| Migrate black phrases Redis to Postgres | scripts/migrate_black_phrases_redis_to_postgres.py | UNKNOWN | NONE | NO | - | - | - | |
| Resource gap | scripts/resource_gap.py | UNKNOWN | NONE | NO | - | - | - | |
| Billing debug cabinet | scripts/run_billing_debug_cabinet.py | UNKNOWN | NONE | NO | - | - | - | |
| Send message to all users | scripts/send_message/send_message_all_users.py | UNKNOWN | NONE | NO | - | - | - | |
| Send single messages | scripts/send_message/single_messages.py | UNKNOWN | NONE | NO | - | - | - | |
| Set false for non-qualifying users | scripts/set_false_for_non_qualifying_users.py | UNKNOWN | NONE | NO | - | - | - | |
| Set old user passed gate | scripts/set_old_user_passed_gate.py | UNKNOWN | NONE | NO | - | - | - | |
| Set relevant if white phrase | scripts/set_relevant_if_white_phrase.py | UNKNOWN | NONE | NO | - | - | - | |
| Set sales plan | scripts/set_sales_plan.py | UNKNOWN | NONE | NO | - | - | - | |
| Set shop id for all WB tokens | scripts/set_shop_id_for_all_wbtokens.py | UNKNOWN | NONE | NO | - | - | - | |
| Start campaigns by nmids | scripts/start_campaigns_by_nmids.py | UNKNOWN | NONE | NO | - | - | - | |
| Sync local env from k8s | scripts/sync-local-env-from-k8s.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |
| Path smoke | scripts/test_path.py | UNKNOWN | NONE | NO | - | - | - | path smoke |
| Test PG connection | scripts/test_pg_conn.py | UNKNOWN | NONE | NO | - | - | - | |
| Translit YAML | scripts/translit_yaml.py | UNKNOWN | NONE | NO | - | - | - | |
| Main user generator | scripts/users_communicate_module/main_user_generator.py | UNKNOWN | NONE | NO | - | - | - | |
| Users CSV export | scripts/users_csv_exporter/csv_export.py | WORKS | NONE | NO | - | 2026-08-04T02:35:30Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:7dcf1cc5bc85da2da95e220220e4748238d2c597 | Job Complete; all_users.xlsx 129991B copied; PYTHONPATH+/hold in template |
| WB API read-only preflight/collect | scripts/wb_api_readonly_ops/run.py | WORKS | PARTIAL | NO | 2026-08-05T06:50:00Z | 2026-08-05T07:29:30Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:b1e6b2f8f59fed5f87ac80bb736577ce95fa8380 | Job ops-script-wb-ro-collect-20260805-072757 exit0; ORDERS 1188 + sales 801; overall PARTIAL (norms); local zip OK during hold |

| Verify local env | scripts/verify-local-env.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |

## Support (not Job entrypoints)

Tracked only as notes; not run via `ops-script-runner` unless Owner promotes:

* `scripts/set_path.py` — path bootstrap
* `scripts/template_script.py` — authoring template
* `scripts/__init__.py` and package `__init__.py` / helper modules under `send_message/utils`, `get_users/filters`, etc.

## Infra pointers

* Prepare: `/opsx-scripts-prepare`
* Operate: `/opsx-scripts`
* Display SoT: `.cursor/commands/opsx-human-label-display.md`
* Workflow: `.github/workflows/deploy_scripts.yml` (branch `scripts`, tag `scripts`)
* Job template: `k8s/jobs/ops-script-runner.yaml`
