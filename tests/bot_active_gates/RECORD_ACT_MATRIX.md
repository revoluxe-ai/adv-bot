# Shop-runner RECORD vs ACT matrix

Источник списка корутин: `tests/test_wb_shop_run_coroutines.py` (`_build_coroutines_manager_mock.methods`).

Легенда:

- **RECORD** — ingestion / persistence без мутации WB ad state (целевое: работает при `bot_active=False`)
- **ACT** — мутация WB (только `bot_active=True`)
- **P0** — обязательный gate-тест в `tests/bot_active_gates/`

| Coroutine | Class | P0 ACT | Gate test |
|-----------|-------|--------|-----------|
| `update_advs_data_from_wb_to_pg` | RECORD | | |
| `update_cards_data_from_wb_to_pg` | RECORD | | |
| `update_common_sale_stat` | RECORD | | xfail RECORD |
| `update_full_adv_stat` | RECORD | | |
| `update_clusters_adv_stats_today` | RECORD | | |
| `update_clusters_adv_stats_history` | RECORD | | |
| `refresh_stats_freshness_cache` | RECORD | | |
| `adv_settings_auto_update` | ACT | | yes P1 |
| `update_minus_phrases_in_advs` | ACT | P0 | yes |
| `update_cluster_bids` | ACT | P0 | yes |
| `cache_current_cluster_bids` | RECORD | | read WB → Redis |
| `preload_min_bids_cache_miss` | RECORD | | cache warm |
| `preload_min_bids_cache_old` | RECORD | | cache warm |
| `handle_stats_stale_emergency` | ACT | | mutates keywords/bids |
| `update_plan_fact_stats` | RECORD | | |
| `auto_budget_watchdog` | ACT | | start/pause + budget |
| `update_top_key_in_advs` | ACT | P0 | yes (whitelist) |
| `update_common_bid_in_search_adv` | ACT | P0 | yes |
| `increment_fact_data_stats` | RECORD | | |
| `auto_shelf_bid_increment_stats` | ACT | | review |
| `auto_shelf_bid_control` | ACT | P0 | yes (shelf) |
| `white_list_tail_trimmer` | ACT | P0 | yes (whitelist) |
| `auto_reset_bid_for_auto_adv` | ACT | | |
| `update_individual_keyword_target_places` | ACT | P0 | yes (target place) |
| `change_adv_strategy` | ACT | | PG strategy only |

## P0 ACT (пользовательские 4 + расширение)

1. Common search bid — `update_common_bid_in_search_adv`
2. Target place — `update_individual_keyword_target_places`, v3 via `adv_settings_auto_update`
3. Whitelist — `update_top_key_in_advs`, `white_list_tail_trimmer`
4. Shelf bid — `auto_shelf_bid_control`
5. Cluster bids — `update_cluster_bids`
6. Minus phrases — `update_minus_phrases_in_advs`
7. CPM bidder — `update_cpm_bid` (not in WBShop.run list but in manager)

Примечание: `update_cpm_bid` и `update_keywords_stamp` есть в `CoroutinesManager`, но не в списке `WBShop.run()` — учитывать при follow-up.
