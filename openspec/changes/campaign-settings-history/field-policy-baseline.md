# Field Policy Baseline - campaign-settings-history

This is the reviewed initial classification for all current registered settings-owned source fields. It is normative input for the field registry and inventory tests.

History policy: state and metadata are included in the canonical history payload/hash; excluded fields are never silently ignored and require the reason category below.

Excel policy: existing editable behavior is preserved initially. RO aliases are explicit human-facing projection aliases. Synthetic plan/fact/spend/export diagnostics are Excel-only and never enter the settings hash.

## AdvSetting

history.state: aggressiveness, auction_adv_target_status, auction_boost_all_phrase_mode, auto_add_only_relevant_phrase, auto_adv_target_status, auto_budget_daily_limit, auto_budget_total_limit, auto_budget_watchdog_enabled, auto_common_budget, auto_shelf_bid_control_enabled, auto_shelf_bid_control_strategy, auto_update_exponent, auto_update_minus_phrases, auto_update_strategy, auto_update_target_place, auto_update_white_list, bidder_active, bidder_coroutine_type, bidder_for_auto, bidder_mode, bidder_step, black_phrases, boost, bot_active, card_ab_hold_allowed_phrases_snapshot, card_ab_hold_confirmed_auto_bid, card_ab_hold_confirmed_auto_participation, card_ab_hold_confirmed_keywords_json, card_ab_hold_confirmed_target_places_json, card_ab_hold_mode, card_ab_hold_warmup_duration_hours, clusters_mode, common_budget_daily_limit, common_budget_total_limit, exponent_predict_ctr, hide_small_query_keywords, hide_zero_views_keywords, individual_keywords_target_place_mode, keyword_calibration_max_step, max_balance_adding_for_day, max_cpc, max_cpm, max_place, max_price_for_order, min_block_position, min_target_position, min_views_for_ml_predict, new_auto_min_ctr_mode, orders_source_for_auto_mode, pass_days, plan_for_sales_for_day, predict_ctr_mode, raise_plan_on_promobonuses, rec_system_mode, relevant_phrases, reset_place, sales_predict_method, search_auto_budget_daily_limit, search_auto_budget_total_limit, strategy, substitute_fact_cpo_for_max, target_ctr_mode, target_ctr_mode_strategy, target_position_mode, target_price_for_order, updater_common_bid_in_search_adv_active_status, use_cluster_stats_in_freshness, use_common_budget, use_incremental_stats, white_list_mode

history.metadata: _search_adv_id, adv_id, id, name, nmids, type, wb_cabinet_id

history.excluded: active_status, automatic_version, card_ab_hold_degraded, card_ab_hold_emergency_educated, card_ab_hold_emergency_latch, card_ab_hold_generation, card_ab_hold_pending_intent_json, card_ab_hold_phase, card_ab_hold_sync_status, card_ab_hold_warmup_started_at, card_ab_hold_wb_sync_idempotency_key, cpm, hard_min_ctr, last_update, parsing_active, wb_bid_type, wb_placement_recommendations, wb_placement_search

## KeywordSetting

history.state: hard_status, relevant, strategy_mode, target_place

history.metadata: text

history.excluded: added_clicks, added_views, adv_setting_id, auto_block, id, predict_ctr

## AutoShelfBidControlSettings

history.state: currency, max_bid_minor, min_bid_distance_minor, retest_interval_days, target_test_impressions, target_test_observation_minutes, test_share

history.metadata: nmid

history.excluded: created_at, id, updated_at

## AdvTimeSettings

history.state: date_enabled, date_end, date_start, schedule_enabled, timezone

history.metadata: none

history.excluded: adv_setting_id, created_at, id, updated_at

## AdvTimeWeekMask

history.state: hours_mask

history.metadata: dow

history.excluded: adv_setting_id

## Exclusion reasons

- AdvSetting active_status, wb_bid_type, wb_placement_search, wb_placement_recommendations, cpm: WB-observed physical campaign state; reserved for a separate WB campaign-state contour.
- AdvSetting automatic_version, hard_min_ctr: legacy/deprecated technical fields.
- AdvSetting parsing_active, last_update: operational/runtime bookkeeping.
- AdvSetting card_ab_hold_degraded, card_ab_hold_phase, card_ab_hold_warmup_started_at, card_ab_hold_generation, card_ab_hold_wb_sync_idempotency_key, card_ab_hold_pending_intent_json, card_ab_hold_sync_status, card_ab_hold_emergency_latch, card_ab_hold_emergency_educated: workflow/health/safety runtime state. Durable user-confirmed configuration remains represented by included hold configuration fields.
- KeywordSetting id and adv_setting_id: technical relational identity; canonical keyword identity is text within the owning campaign.
- KeywordSetting predict_ctr, added_clicks, added_views: derived/statistical; auto_block: runtime automation state.
- AutoShelf/AdvTime ids, owner foreign keys, created_at, updated_at: technical persistence metadata.

## Excel initial projection policy

AdvSetting editable: aggressiveness, auto_add_only_relevant_phrase, auto_budget_daily_limit, auto_budget_total_limit, auto_budget_watchdog_enabled, auto_common_budget, auto_shelf_bid_control_enabled, auto_update_exponent, auto_update_strategy, auto_update_target_place, auto_update_white_list, bidder_coroutine_type, bidder_for_auto, bidder_step, bot_active, clusters_mode, common_budget_daily_limit, common_budget_total_limit, exponent_predict_ctr, hide_small_query_keywords, hide_zero_views_keywords, individual_keywords_target_place_mode, keyword_calibration_max_step, max_cpm, max_place, max_price_for_order, min_views_for_ml_predict, orders_source_for_auto_mode, plan_for_sales_for_day, predict_ctr_mode, raise_plan_on_promobonuses, rec_system_mode, reset_place, sales_predict_method, search_auto_budget_daily_limit, search_auto_budget_total_limit, strategy, substitute_fact_cpo_for_max, target_ctr_mode, target_ctr_mode_strategy, target_position_mode, target_price_for_order, updater_common_bid_in_search_adv_active_status, use_common_budget, use_incremental_stats, white_list_mode

AdvSetting read-only aliases: id -> adv_setting_id, adv_id -> adv_id, _search_adv_id -> search_adv_id, nmids -> nmid:first

All other AdvSetting source fields are excel=excluded unless emitted as separately declared synthetic diagnostic columns.

KeywordSetting target-place workbook: target_place is editable; id -> keyword_id, text -> keyword, target_place -> current_target_place. All other KeywordSetting source fields are excel=excluded.

AutoShelf editable aliases: max_bid_minor -> auto_shelf_max_bid_rub, min_bid_distance_minor -> auto_shelf_min_bid_distance_rub, target_test_impressions -> auto_shelf_target_test_impressions, target_test_observation_minutes -> auto_shelf_target_test_observation_minutes, test_share -> auto_shelf_test_share. currency, retest_interval_days, nmid, ids/timestamps are currently excel=excluded.

AdvTimeSettings and AdvTimeWeekMask: all source fields currently excel=excluded.

## Deterministic coverage assertion

Current inventory counts: AdvSetting=95, KeywordSetting=11, AdvTimeSettings=9, AdvTimeWeekMask=3, AutoShelfBidControlSettings=11.

Implementation MUST reconstruct each registered source inventory and fail on any set difference against the registry. Every field MUST have history policy and Excel policy; every excluded policy MUST carry a non-empty reason.

BASELINE_POLICY_STATUS: COMPLETE
