# scripts/ readiness registry

Ledger for `/opsx-scripts` (daily) and `/opsx-scripts-prepare`.

Human display: `Title (path)` — see `.cursor/commands/opsx-human-label-display.md`.

Do not set `battle_tested=YES` without Owner `RECORD_BATTLE GO` + evidence.

## Schema

| title | path | runnable | tests | battle_tested | last_local_at | last_cluster_at | last_image_ref | notes |
|-------|------|----------|-------|---------------|----------------|-----------------|----------------|-------|
| short human name | `scripts/<entrypoint>` | `UNKNOWN` \| `WORKS` \| `BROKEN` | `NONE` \| `PARTIAL` \| `COVERED` | `NO` \| `YES` | ISO UTC or `-` | ISO UTC or `-` | image ref or `-` | short |

## Entrypoints

| title | path | runnable | tests | battle_tested | last_local_at | last_cluster_at | last_image_ref | notes |
|-------|------|----------|-------|---------------|----------------|-----------------|----------------|-------|
| A1 cabinet-401 RUN GO contract collector | scripts/a1_cabinet401_run_go_contract_collect.py | UNKNOWN | PARTIAL | NO | - | - | - | Strict read-only cabinet 401 compatibility envelope. |
| A1 cabinet-401 RUN GO contract collector v2 | scripts/a1_cabinet401_run_go_contract_collect_v2.py | UNKNOWN | PARTIAL | NO | - | - | - | Isolated-worker cabinet 401 compatibility envelope. |
| Client management scope reconcile | scripts/a1_client_management_scope_reconcile_collect.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| A1 controlled ad expansion v1 | scripts/a1_controlled_ad_expansion_v1.py | WORKS | COVERED | NO | 2026-09-08T05:45:00Z | - | - | Legacy ledger row; not available to resolver. |
| A1 current performance / DRR snapshot | scripts/a1_current_performance_drr_snapshot.py | WORKS | NONE | NO | - | 2026-09-08T02:48:08Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:349ef965a7b1af7b70f452c0f082af54ef6085ab | Legacy ledger row; not available to resolver. |
| A1 current state gap collector | scripts/a1_current_state_gap_collect.py | WORKS | PARTIAL | NO | 2026-09-14T04:19:09Z | 2026-09-14T04:42:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:99611ce70986a790c428525635b48e6b5927b208 | Legacy ledger row; not available to resolver. |
| A1 daily spend control reconciliation | scripts/a1_daily_spend_control_reconciliation.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| A1 existing campaign reuse inventory | scripts/a1_existing_campaign_reuse_inventory.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| A1 glue topology Web review | scripts/a1_glue_topology_web_review_collect.py | WORKS | PARTIAL | NO | 2026-09-06T15:11:00Z | 2026-09-06T15:15:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:332d565754f549aaa3e0465e06e2dfc74c20f3e4 | Legacy ledger row; not available to resolver. |
| ProKraft delayed advertising-effect evidence collector | scripts/a1_prokraft_delayed_ad_effect_collect.py | WORKS | NONE | NO | - | 2026-09-14T04:41:55Z | - | Legacy ledger row; not available to resolver. |
| ProKraft historical SPP dynamics collector | scripts/a1_prokraft_spp_dynamics_collect.py | WORKS | PARTIAL | NO | 2026-09-14T16:35:00Z | 2026-09-14T16:55:01Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:d0d0a09e50bdddc36088e73b361f9b242e6e547d | Legacy ledger row; not available to resolver. |
| A1 promo-adjusted DRR / cash ad cost | scripts/a1_promo_adjusted_drr_collect.py | WORKS | NONE | NO | - | 2026-09-07T01:28:04Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:2f6d3026dbfe27c04d42a3bc357764c093720b90 | Legacy ledger row; not available to resolver. |
| A1 SKU factual ad economics collect | scripts/a1_sku_factual_ad_economics_collect.py | WORKS | NONE | NO | - | 2026-09-10T12:18:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:9d2a5b1f6ba0078f706ff35d98da8b6b64e58ebb | Legacy ledger row; not available to resolver. |
| A1 strict read-only contract collector | scripts/a1_strict_read_only_contract_collect.py | WORKS | PARTIAL | NO | 2026-09-08T15:55:27Z | - | - | Exact 00-07 contract ZIP and checksum; no production writes. |
| A1 V3 post-import verify collect | scripts/a1_v3_post_import_verify_collect.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Whole-shop factual economics | scripts/a1_whole_shop_economics_collect.py | WORKS | NONE | NO | - | 2026-09-12T03:39:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:9c192d82af120121cfe9228ee748e55adc06ef1f | Legacy ledger row; not available to resolver. |
| Whole store daily DRR dynamics | scripts/a1_whole_store_daily_drr_collect.py | WORKS | NONE | NO | - | 2026-09-13T10:16:35Z | - | Legacy ledger row; not available to resolver. |
| Adv-bot historical state extractor | scripts/adv_bot_historical_state_extractor.py | WORKS | COVERED | NO | 2026-08-25T21:44:04Z | 2026-08-25T22:40:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:9d269aa9e95afe64da03f8c8f5c07231da26c50e | Legacy ledger row; not available to resolver. |
| Backfill L2 | scripts/backfill_l2.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Backfill MV for keyword clusters | scripts/backfill_mv_for_keyword_clusters.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Delete user by Telegram id | scripts/delete_user_by_telegram_id.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Enable individual keywords for new tariff cabinets | scripts/enable_individual_keywords_for_new_tariff_cabinets.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Export last WB movements | scripts/export_last_wb_movements.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Export non-zero balance users | scripts/export_non_zero_balance_users.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Export single-article campaign stats | scripts/export_single_article_campaigns_stats.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Fill bid decision | scripts/fill_bid_decision.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Get dialogs from TG export | scripts/get_dialogs_from_tg_export.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Get users | scripts/get_users/get_users.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Get users for shop (worst adv) | scripts/get_worst_adv/get_users_for_shop_id.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Insert adv deltas | scripts/insert_adv_deltas.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Install error monitoring | scripts/INSTALL_ERROR_MONITORING.sh | UNKNOWN | NONE | NO | - | - | - | shell; Job template is python-oriented |
| Prod DB migrate then rollout | scripts/Invoke-ProdDbMigrateThenRollout.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |
| Main user generator | scripts/users_communicate_module/main_user_generator.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Migrate black phrases Redis to Postgres | scripts/migrate_black_phrases_redis_to_postgres.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Generic multi-client advertising preflight | scripts/multi_client_ad_preflight_collect.py | UNKNOWN | PARTIAL | NO | - | - | - | Parameterized read-only identity envelope; explicit coverage gaps remain. |
| Generic multi-client CPC topology | scripts/multi_client_cpc_topology_collect.py | WORKS | PARTIAL | NO | 2026-09-17T20:25:06Z | 2026-09-17T20:25:06Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:57984c0250abee172f4c8b736807504e3a105fc7 | Legacy ledger row; not available to resolver. |
| Path smoke | scripts/test_path.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Resource gap | scripts/resource_gap.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Billing debug cabinet | scripts/run_billing_debug_cabinet.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Send message to all users | scripts/send_message/send_message_all_users.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Send single messages | scripts/send_message/single_messages.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Set false for non-qualifying users | scripts/set_false_for_non_qualifying_users.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Set old user passed gate | scripts/set_old_user_passed_gate.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Set relevant if white phrase | scripts/set_relevant_if_white_phrase.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Set sales plan | scripts/set_sales_plan.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Set shop id for all WB tokens | scripts/set_shop_id_for_all_wbtokens.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Start campaigns by nmids | scripts/start_campaigns_by_nmids.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Sync local env from k8s | scripts/sync-local-env-from-k8s.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |
| Translit YAML | scripts/translit_yaml.py | UNKNOWN | NONE | NO | - | - | - | Legacy ledger row; not available to resolver. |
| Users CSV export | scripts/users_csv_exporter/csv_export.py | WORKS | NONE | NO | - | 2026-08-14T12:47:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:c1e1fa7c523cdcec81ea23aaf7d8b2dc8e08248a | Legacy ledger row; not available to resolver. |
| Verify local env | scripts/verify-local-env.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |
| WB API read-only preflight/collect | scripts/wb_api_readonly_ops/run.py | WORKS | PARTIAL | NO | 2026-08-21T10:54:00Z | 2026-08-21T15:40:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:4451a5645f9256c1978af1b64420b84a00a540eb | Legacy ledger row; not available to resolver. |

## Support (not Job entrypoints)

Tracked only as notes; not run via `ops-script-runner` unless Owner promotes:

* `scripts/set_path.py` — path bootstrap
* `scripts/template_script.py` — authoring template
* `scripts/__init__.py` and package `__init__.py` / helper modules under `send_message/utils`, `get_users/filters`, etc.

## Infra pointers

* Prepare: `/opsx-scripts-prepare`
* Operate: `/opsx-scripts`
* Display SoT: `.cursor/commands/opsx-human-label-display.md`
* Workflow: `.github/workflows/deploy_scripts.yml` (branch `scripts`, tag `scripts`; CI push GHCR only)
* Cluster Job image (Harbor proxy-cache pull-through): `harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:<commit-sha>`
* Job template: `k8s/jobs/ops-script-runner.yaml` (`__HOLD_SECONDS__` default 900)
* Artifact cp helper: `scripts/ops_script_job_cp.ps1` (retry kubectl cp + sha256 gate)
