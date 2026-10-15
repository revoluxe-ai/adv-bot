---
cursor:
  subagentId: "bc-32bdaafb-bc6f-532c-901a-2eb4845c2b03"
---

# separate-auto-search-cpo merge reconciliation

## Summary

| Field | Value |
|-------|-------|
| RECONCILED_HEAD | `176d681751d1632738d9030415443aa71cc74c8f` |
| PUSHED | NO |
| PYRIGHT_UNION | PASS |
| MANAGER_HOOKS | 3× `attach_leg_cpo`; shop-wide: `run_shop_wide_common_sale_stat_tick`, `collect_shop_wide_campaign_advertising` present |
| BLOCKER | none |

## Git

- Pre-merge tips verified: `origin/stage` = `23c0671f372f0435b13a3573ec8990b4303b3e4a`, `origin/separate-auto-search-cpo` = `784f468becfffcba5118592348adf914dc994d73`, merge-base = `b79534379971e94e0200b50ebc6787ea96455452`.
- Branch: `separate-auto-search-cpo` (tracks `origin/separate-auto-search-cpo`).
- Merge commit message: `merge: reconcile separate-auto-search-cpo onto origin/stage 23c0671f`.
- Status after commit: `## separate-auto-search-cpo...origin/separate-auto-search-cpo [ahead 47]`.

## pyrightconfig_strict.json

- Conflict resolved by **union** of disjoint include tails (feature CPO/keyword paths + stage CH migration / ai_package / campaign-settings entries).
- Non-include keys unchanged from merged result (identical on both sides); no non-include conflict.
- JSON validated via `python3` / `jq`.
- `include` count: 162.

### Last 40 include entries

```
app/common_coroutine/common_coroutine.py
app/modules/adv_creator/backend/main_manager.py
app/modules/billing/billing.py
app/modules/shop_runner/service_manager/services/v3_status_mode_backfill.py
app/modules/user_message_sender/__init__.py
app/modules/user_message_sender/message_for_not_pay_user_sender.py
app/modules/white_list_mode_settings/telegram/keyboards.py
app/modules/white_list_mode_settings/telegram/main_message.py
run_send_info_message_to_users_process.py
app/shared/domains/wb/utils/promo_plan_multiplier.py
app/shared/domains/wb/utils/promo_overlay.py
app/shared/domains/wb/utils/promo_accounting.py
app/shared/domains/wb/utils/auto_campaign_cost_activity.py
app/shared/domains/wb/utils/balance_source.py
app/modules/sales_plan_settings/raise_plan_on_promobonuses.py
app/modules/sales_plan_settings/telegram/setting_handlers/toggle_raise_plan_on_promobonuses.py
app/modules/common_slaves/wildberries/models/wb_campaign_promo_spend.py
app/modules/plan_fact/provider.py
app/modules/common_slaves/wildberries/models/wb_auto_budget_topup.py
app/modules/sales_plan_settings/telegram/callbacks.py
tools/wb_api_master_map.py
app/client_bot/user_interface/views/messages/adv_keyword_messages/adv_keyword_messages.py
app/modules/common_advs_stat/data_manager.py
app/modules/shop_runner/wb_stat_manager/clickhouse_manager/full_wb_adv_stat.py
app/shared/domains/wb/dto/wb_adv_dto.py
app/modules/shop_runner/wb_stat_manager/leg_cpo.py
app/modules/campaign_settings_contract
app/modules/campaign_settings_history
scripts/clickhouse_migration_control_plane
tests/unit/clickhouse_migration_contract_fixture.py
tests/unit/test_clickhouse_migration_legacy_baseline.py
tests/unit/test_clickhouse_migration_isolated_target_port.py
tests/unit/test_clickhouse_migration_coordinator_session.py
tests/unit/test_clickhouse_migration_corpus_acceptance.py
tests/unit/test_clickhouse_migration_pre_execution.py
tests/unit/test_clickhouse_migration_read_only_commands.py
tests/unit/test_clickhouse_migration_mutations.py
tests/unit/test_clickhouse_migration_final_acceptance.py
app/modules/ai_package_v1
tests/unit/ai_package_v1
```

## manager.py (auto-merge accepted)

### Shop-wide (stage)

- `run_shop_wide_common_sale_stat_tick` imported and awaited in `update_common_sale_stat` (~451–465).
- `collect_shop_wide_campaign_advertising` coroutine defined ~477+.

### attach_leg_cpo (feature) — 3 call sites

1. ~601–603 — AB hold pipeline candidates  
2. ~878 — auto-budget path after `get_complex_advs`  
3. ~1821 — auto shelf bid control candidates  

No manual edits to `manager.py`; auto-merge retained both symbol sets.
