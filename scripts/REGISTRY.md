# scripts/ readiness registry

Ledger for `/opsx-scripts` (daily) and `/opsx-scripts-prepare` (infra).

Do not set `battle_tested=YES` without Owner `RECORD_BATTLE GO` + evidence.

## Schema

| path | runnable | tests | battle_tested | last_local_at | last_cluster_at | last_image_ref | notes |
|------|----------|-------|---------------|---------------|-----------------|----------------|-------|
| `scripts/<entrypoint>` | `UNKNOWN` \| `WORKS` \| `BROKEN` | `NONE` \| `PARTIAL` \| `COVERED` | `NO` \| `YES` | ISO UTC or `-` | ISO UTC or `-` | image ref or `-` | short |

## Entrypoints

| path | runnable | tests | battle_tested | last_local_at | last_cluster_at | last_image_ref | notes |
|------|----------|-------|---------------|---------------|-----------------|----------------|-------|
| scripts/backfill_l2.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/backfill_mv_for_keyword_clusters.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/delete_user_by_telegram_id.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/enable_individual_keywords_for_new_tariff_cabinets.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/export_last_wb_movements.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/export_non_zero_balance_users.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/export_single_article_campaigns_stats.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/fill_bid_decision.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/get_dialogs_from_tg_export.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/get_users/get_users.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/get_worst_adv/get_users_for_shop_id.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/insert_adv_deltas.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/INSTALL_ERROR_MONITORING.sh | UNKNOWN | NONE | NO | - | - | - | shell; Job template is python-oriented |
| scripts/Invoke-ProdDbMigrateThenRollout.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |
| scripts/migrate_black_phrases_redis_to_postgres.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/resource_gap.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/run_billing_debug_cabinet.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/send_message/send_message_all_users.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/send_message/single_messages.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/set_false_for_non_qualifying_users.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/set_old_user_passed_gate.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/set_relevant_if_white_phrase.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/set_sales_plan.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/set_shop_id_for_all_wbtokens.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/start_campaigns_by_nmids.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/sync-local-env-from-k8s.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |
| scripts/test_path.py | UNKNOWN | NONE | NO | - | - | - | path smoke |
| scripts/test_pg_conn.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/translit_yaml.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/users_communicate_module/main_user_generator.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/users_csv_exporter/csv_export.py | UNKNOWN | NONE | NO | - | - | - | |
| scripts/verify-local-env.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |

## Support (not Job entrypoints)

Tracked only as notes; not run via `ops-script-runner` unless Owner promotes:

* `scripts/set_path.py` — path bootstrap
* `scripts/template_script.py` — authoring template
* `scripts/__init__.py` and package `__init__.py` / helper modules under `send_message/utils`, `get_users/filters`, etc.

## Infra pointers

* Prepare: `/opsx-scripts-prepare`
* Operate: `/opsx-scripts`
* Workflow: `.github/workflows/deploy_scripts.yml` (branch `scripts`, tag `scripts`)
* Job template: `k8s/jobs/ops-script-runner.yaml`
