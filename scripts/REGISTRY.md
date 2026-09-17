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
| Adv-bot historical state extractor | scripts/adv_bot_historical_state_extractor.py | WORKS | COVERED | NO | 2026-08-25T21:44:04Z | 2026-08-25T22:40:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:9d269aa9e95afe64da03f8c8f5c07231da26c50e | DILERA battle run Job ops-script-adv-hist-dilera-20260825-223759 COMPLETE; PRIMARY zip 181d077f…; supplier_id→shop bab6bc8e…; gaps=[] |
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
| Users CSV export | scripts/users_csv_exporter/csv_export.py | WORKS | NONE | NO | - | 2026-08-14T12:47:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:c1e1fa7c523cdcec81ea23aaf7d8b2dc8e08248a | Job ops-script-users-csv-20260814-123657 Complete exit=0; all_users.xlsx 129957B sha256 670f02cba87457967b0b26c50032d3a26cc51ca466743ebd9c5bac8ff60ddb15 |
| WB API read-only preflight/collect | scripts/wb_api_readonly_ops/run.py | WORKS | PARTIAL | NO | 2026-08-21T10:54:00Z | 2026-08-21T15:40:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:4451a5645f9256c1978af1b64420b84a00a540eb | collect Job ops-script-wb-collect-a1-20260821-153424 OOO-A1 PARTIAL; LOCAL_ARTIFACT_HANDOFF=PASS; L0 zip abf3c048…; Stage-A limits — see SCRIPTS_REPORT |
| A1 glue topology Web review | scripts/a1_glue_topology_web_review_collect.py | WORKS | PARTIAL | NO | 2026-09-06T15:11:00Z | 2026-09-06T15:15:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:332d565754f549aaa3e0465e06e2dfc74c20f3e4 | Job ops-script-a1-glue-topology-20260906-151200 COMPLETE; PRIMARY zip ac26eb01…; spend dedupe fix; PRICE_API_GAP |
| A1 promo-adjusted DRR / cash ad cost | scripts/a1_promo_adjusted_drr_collect.py | WORKS | NONE | NO | - | 2026-09-07T01:28:04Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:2f6d3026dbfe27c04d42a3bc357764c093720b90 | Job ops-script-a1-promo-drr-20260907-012426 COMPLETE; PRIMARY zip a22f8cfa…; CASH_FLOW_ONLY; promo_adjusted=GAP |
| A1 current performance / DRR snapshot | scripts/a1_current_performance_drr_snapshot.py | WORKS | NONE | NO | - | 2026-09-08T02:48:08Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:349ef965a7b1af7b70f452c0f082af54ef6085ab | Job ops-script-a1-perf-drr-20260908-054700 COMPLETE; PRIMARY zip 9e6fbb1e…; CASH_FLOW_ONLY; wb_cabinet 401 verified |
| A1 strict read-only contract collector | scripts/a1_strict_read_only_contract_collect.py | WORKS | PARTIAL | NO | 2026-09-08T15:55:27Z | - | - | Targeted unit tests 7 passed; exact 00–07 contract ZIP + .sha256; no production writes |
| A1 cabinet-401 RUN GO contract collector | scripts/a1_cabinet401_run_go_contract_collect.py | UNKNOWN | PARTIAL | NO | - | - | - | Strict read-only cabinet 401 envelope; eight requested NMIDs; primary ZIP + SHA; FBO/FBS remains explicit GAP |
| A1 cabinet-401 RUN GO contract collector v2 | scripts/a1_cabinet401_run_go_contract_collect_v2.py | UNKNOWN | PARTIAL | NO | - | - | - | Strict read-only contract; isolated worker process per collector prevents asyncpg event-loop reuse; FBO/FBS remains explicit GAP |
| A1 current state gap collector | scripts/a1_current_state_gap_collect.py | WORKS | PARTIAL | NO | 2026-09-14T04:19:09Z | 2026-09-14T04:42:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:99611ce70986a790c428525635b48e6b5927b208 | Job ops-script-a1-gap-20260914-0738; PRIMARY sha 9fba48db…; LOCAL_ARTIFACT_HANDOFF=PASS; runtime CPO CH schema GAP |
| A1 SKU factual ad economics collect | scripts/a1_sku_factual_ad_economics_collect.py | WORKS | NONE | NO | 2026-09-10T12:05:00Z | 2026-09-10T12:18:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:9d2a5b1f6ba0078f706ff35d98da8b6b64e58ebb | Job ops-script-prokraft-sku266109990-202609101215; nmid 266109990; PRIMARY sha 0d8c38c0…; gaps=[] |
| A1 V3 post-import verify collect | scripts/a1_v3_post_import_verify_collect.py | UNKNOWN | NONE | NO | 2026-09-10T19:30:00Z | - | - | PG+Redis V3+WB live; READ_ONLY post-import verification |
| Whole-shop factual economics | scripts/a1_whole_shop_economics_collect.py | WORKS | NONE | NO | 2026-09-12T03:30:00Z | 2026-09-12T03:39:00Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:9c192d82af120121cfe9228ee748e55adc06ef1f | Job ops-script-whole-shop-573-20260912-0332; PRIMARY whole_shop_economics.json; side ZIP e31354d7…; enrich gap on store_windows_drr_10 |
| Whole store daily DRR dynamics | scripts/a1_whole_store_daily_drr_collect.py | WORKS | NONE | NO | - | 2026-09-13T10:16:35Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:fc6bfe2a2 | Job ops-script-store-daily-drr-573-20260913-1109; PRIMARY whole_store_daily_drr.json sha 64c836d1…; 28D DRR 2.53%; TODAY_OPEN 11.6% |
| Client management scope reconcile | scripts/a1_client_management_scope_reconcile_collect.py | UNKNOWN | NONE | NO | - | - | - | WB 573; 6-SKU WB/PG/bot/V3/economics reconciliation; READ_ONLY |
| ProKraft delayed advertising-effect evidence collector | scripts/a1_prokraft_delayed_ad_effect_collect.py | WORKS | NONE | NO | - | 2026-09-14T04:41:55Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:64ba33eb8c34967b0dd412fbfc29e85af4e822c8 | Job ops-script-prokraft-delay-halo-20260914-0457; ZIP sha 908f3849…; artifact PASS; integrity GAP on page metadata, campaign identity, and whole-store control semantics |
| ProKraft historical SPP dynamics collector | scripts/a1_prokraft_spp_dynamics_collect.py | WORKS | PARTIAL | NO | 2026-09-14T16:35:00Z | 2026-09-14T16:55:01Z | harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:d0d0a09e50bdddc36088e73b361f9b242e6e547d | Job ops-script-prokraft-spp-20260914-1955; primary ZIP sha 84e99292…; 898 rows, 29-day coverage, artifact PASS; intervention/pre-post ranking GAP |
| A1 controlled ad expansion v1 | scripts/a1_controlled_ad_expansion_v1.py | WORKS | COVERED | NO | 2026-09-08T05:45:00Z | - | - | DRY_RUN default; explicit --execute; allowlisted top-up/start adapters; PRICE/GLUE/CARD=0 |
| Generic multi-client advertising preflight | scripts/multi_client_ad_preflight_collect.py | UNKNOWN | PARTIAL | NO | - | - | - | Parameterized read-only identity envelope; primary ZIP + SHA; FBO/FBS/reservations and funding remain explicit GAP |
| Generic multi-client CPC topology | scripts/multi_client_cpc_topology_collect.py | UNKNOWN | PARTIAL | NO | - | - | - | Explicit shop/cabinet/nmID/adv_id; topology-only strict read-only ZIP + SHA; no stock/economics/DRR |

| Verify local env | scripts/verify-local-env.ps1 | UNKNOWN | NONE | NO | - | - | - | local/ops ps1; not default Job |

## Support (not Job entrypoints)

Tracked only as notes; not run via `ops-script-runner` unless Owner promotes:

* `scripts/set_path.py` — path bootstrap
* `scripts/template_script.py` — authoring template
* `scripts/__init__.py` and package `__init__.py` / helper modules under `send_message/utils`, `get_users/filters`, etc.
* `tools/wb_api_master_map.py` — offline API Master inventory map
  (path × method × family) from local `generated/<family>/vN/swagger`;
  no network / no codegen / no shop_id. Usage:
  `poetry run python tools/wb_api_master_map.py --output .tmp/wb-api-master-map/inventory.json`
  Optional `--markdown`, `--family`, `--force-version`, `--swagger-file`.

## Infra pointers

* Prepare: `/opsx-scripts-prepare`
* Operate: `/opsx-scripts`
* Display SoT: `.cursor/commands/opsx-human-label-display.md`
* Workflow: `.github/workflows/deploy_scripts.yml` (branch `scripts`, tag `scripts`; CI push GHCR only)
* Cluster Job image (Harbor proxy-cache pull-through): `harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:<commit-sha>`
* Job template: `k8s/jobs/ops-script-runner.yaml` (`__HOLD_SECONDS__` default 900)
* Artifact cp helper: `scripts/ops_script_job_cp.ps1` (retry kubectl cp + sha256 gate)
