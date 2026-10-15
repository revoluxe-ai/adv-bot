---
cursor:
  subagentId: "bc-4be1f649-5b15-5606-93b1-559d473eb396"
---

# WB Sky task 4.2 — UI archaeology (adv-bot, READ ONLY)

Evidence date: repo scan `app/`, `tests/`; **0** `*.html` / `*.vue` / `*.jinja*` under repo.

## Executive answers

| # | Question | Answer |
|---|----------|--------|
| 1 | Web admin UI? | **No end-user web UI.** Product control surface is **Telegram (aiogram 3)**. `client_bot_run.py` exposes **FastAPI** only for webhook + `/health`/`/ready`/`/webhook-info` (not settings UI). Separate `error_collector/main.py` FastAPI for log aggregation. |
| 2 | Where V3 settings live? | Telegram: `AdvSettingMenu` + `keyboard/keyboard.py` (V3 buttons), modules `v3_calibration_step_setting/`, `v3_rollout_aggressiveness_toggle/`, `v3_tick_report_ui/`, `keyword_v3_decision_trace_ui/`, `sales_plan_settings/` (plan/CPO/V3 Raise), `keyword_v3_profile_*` in `client_bot/user_interface/services/` + `views/keyword_v3_profile_ui.py`. Excel bulk: `adv_excel_roundtrip/schema.py` (V3 columns). Runtime: `shop_runner/.../auto_updater_v3/*`. **No** `ad_control_settings` Telegram UI. |
| 3 | Shop settings edit path? | Callback → handler (`shop_settings.py`, `start.py`, `ShopMenu`) → `get_async_session_maker` PG session → `update()` on `WBCabinet` / `WBUserCabinet` / cabinet flags; mass settings via `adv_excel_roundtrip` → `apply_adv_excel_rows`. |
| 4 | Campaign list + pagination? | `start.select_shop` / `adv_setting` handlers → `messages.AdvCompanyChoicing` → `keyboards.get_adv_setting_keyboard` with `ChoiceAdvPaginator` (`page`, optional `reset_filter` in FSM). |
| 5 | Diagnostics/status screens? | Campaign menu text (`AdvSettingMenu`), V3 tick report (`V3TickReportOpen`), keyword V3 profile + decision trace (admin), `RedisCampaignActivityReasonManager`, `sales_state_display`, domain-only `AdControlDiagnosticsReportV1`. |
| 6 | Auth/permissions? | **Ownership:** `load_wb_user_cabinet_for_adv_in_session` / `_load_adv_settings_for_wb_user_cabinet_in_session` (telegram user ↔ cabinet). **Admin:** `is_bot_admin` / `IsBotAdminFilter` (`ADMINS` + `EXTRA_ADMIN_TELEGRAM_IDS`). **Entry gates:** `GateMiddleware`, `PhoneRequiredMiddleware`, `channel_subscription`. **Paid/free UI:** `UiAccessResolver`. **Structural freeze:** `is_ab_hold_structural_freeze` before writes. **Read-only WB token:** `TokenInfoService` blocks `bot_active` enable in `adv_setting.py`. |

---

## Reusable pattern records

Columns: PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY

### Shop-level settings

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/modules/shop_menu/message.py` | aiogram | N/A (callback-driven) | `ShopMenu`, `build_shop_main_keyboard` | `TokenInfoService`, `UiAccessResolver`, `Pricer`, PG read | `TextWithKeyboard` message class | `AdvSetting`, `WBCabinet`, `WBUserCabinet`, `UiAccessMode` | READ for render; links to write handlers | `tests/integration/modules/shop_menu/test_message.py`, `tests/client_bot/user_interface/test_onboarding_keyboards_callbacks.py`, `tests/integration/client_bot/test_shop_menu_tariff_pg_seam_close_external_gap.py` | **HIGH** — canonical shop hub for any shop-scoped control UI |
| `app/client_bot/user_interface/handlers/shop_settings.py` | aiogram | `callbacks.DeleteWbUserCabinet`, `ChangeShopDefaultMaxCPM` | `delete_wb_user_cabinet`, `change_shop_default_max_cpm`, `set_shop_default_max_cpm` | `get_shop_ids_with_complete_token_status` | `messages.ChangeShopDefaultMaxCPMMessage`, `ShopsListPage` | `states.ShopDefaultMaxCPM` | PG: `delete(WBUserCabinet)`, `update(WBCabinet.default_max_cpm)` | NOT_FOUND (dedicated unit file) | **HIGH** — FSM numeric validation + cabinet PG write pattern |
| `app/client_bot/user_interface/handlers/start/start.py` | aiogram | `callbacks.Shop` (activate), `ToggleCabinetActive` flow ~L1120 | `shop_menu_process`, cabinet toggle handler | `deactivate_cabinet_atomic_with_user_trackers`, `activate_cabinet` | `ShopMenu` | FSMContext | PG/cabinet activation services | `tests/integration/client_bot/test_start_pg_seam_close_external_gap.py` | **MEDIUM** — shop on/off, not advertising policy |
| `app/client_bot/user_interface/handlers/adv_excel_roundtrip.py` | aiogram | `ExportShopAdvExcel` / `ImportShopAdvExcel` callbacks | export/import handlers | `build_adv_excel_export`, `apply_adv_excel_rows`, `verify_user_owns_wb_user_cabinet` | `_ProgressReporter` (async status messages) | `states` import excel group | PG bulk `AdvSetting` via `import_apply` | `tests/unit/test_campaign_settings_excel_*` (schema/parity) | **HIGH** for multi-campaign settings tables (Excel, not HTML) |

### Campaign “tables” (inline keyboard lists)

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/views/messages/messages.py` | aiogram | N/A | `AdvCompanyChoicing` | PG `_get_wb_cabinet*` | extends `TextWithKeyboardPagination` | `AdvSetting` list, FSM `filter_advs` | READ_ONLY display | NOT_FOUND direct | **HIGH** — campaign list screen orchestration |
| `app/client_bot/user_interface/views/keyboards.py` | aiogram | N/A | `get_adv_setting_keyboard` | — | `InlineKeyboardMarkup` rows per `AdvSetting` | `ChoiceAdvPaginator`, `callbacks.Adv` | READ_ONLY | `tests/client_bot/user_interface/handlers/test_adv_setting.py` (indirect) | **HIGH** — row rendering + status in button text (`bot_active`, `active_status`) |
| `app/client_bot/user_interface/handlers/start/start.py` | aiogram | `ChoiceAdvPaginator` | `select_shop` | `_load_adv_settings_for_wb_user_cabinet_in_session` | `AdvCompanyChoicing` | `ChoiceAdvPaginator` (Pydantic CallbackData) | READ_ONLY | same as above | **HIGH** — pagination entry |

### Per-row / per-entity actions

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/views/callbacks.py` | aiogram | packed `callback_data` | `Adv`, `SettingKeywords`, `ChoiceAdvPaginator` | — | — | `CallbackData` subclasses | — | `tests/unit/client_bot/test_*_callbacks.py` (many) | **HIGH** — typed callback contract for row actions |
| `app/client_bot/user_interface/handlers/keyword_settings.py` | aiogram | `SettingKeywords`, keyword callbacks | multiple `@router.callback_query` | CH/PG loaders, `enrich_keywords_v3_list_profiles` | `KeywordSettingMessage` family | `last_keyword_setting_page` in FSM | PG `KeywordSetting` updates | `tests/unit/client_bot/test_keyword_v3_profile_ui.py`, integration keyword tests | **HIGH** — keyword row actions + paging |
| `app/client_bot/user_interface/handlers/adv_setting/adv_setting.py` | aiogram | `callbacks.Adv` select, turn on/off | `adv_setting` handlers | `apply_paid_auto_management_transition`, `backfill_v3_hard_statuses_and_states_consistency`, `PlanFactReader` | `AdvSettingMenu` | `AdvSetting`, `User` | PG `AdvSetting.bot_active`, related fields | `tests/client_bot/user_interface/handlers/test_adv_setting.py`, `tests/unit/client_bot/handlers/test_turn_adv_on_read_only_token.py` | **HIGH** — campaign-level control + access checks |

### Forms (FSM text input)

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/modules/sales_plan_settings/telegram/setting_handlers/change_max_price_for_order.py` | aiogram | `ChangePlanSetting` | `change_max_for_sales_for_day_handler`, `set_new_max_price_for_order` | `resolve_flag_after_max_cpo_decrease` | inline `message.answer` prompts | string state `"waiting_for_new_max_price_for_order"` | PG `AdvSetting.max_price_for_order`, `substitute_fact_cpo_for_max` | `tests/unit/sales_plan_settings/test_v3_raise_max_cpo.py` | **HIGH** — numeric FSM + side-effect messaging |
| `app/modules/v3_calibration_step_setting/telegram_handler.py` | aiogram | `V3CalibrationStepChange` | `change_v3_calibration_step`, `set_v3_calibration_step` | — | prompt messages | `FSM_V3_CALIBRATION_STEP_ADV_SETTING_ID`, `"waiting_for_v3_calibration_step"` | PG `AdvSetting.keyword_calibration_max_step` | `tests/unit/test_v3_calibration_step_setting_handler.py` | **HIGH** — V3-specific settings FSM |
| `app/client_bot/user_interface/handlers/time_settings/router.py` | aiogram | `TS` callbacks | many handlers + `validate_range` | `TimeSettingsRepository`, `render_screen` | `render.render_screen` | in-memory session in `state.py` | PG `AdvTimeSettings` via repository | NOT_FOUND under `tests/client_bot/time_settings` | **HIGH** — rich form UI (grid toggles) without HTML |
| `app/client_bot/user_interface/handlers/campaign_activity.py` | aiogram | budget limit callbacks | FSM handlers for daily/total limits | `load_total_spend_snapshot` | `messages.*` | `states` campaign activity | PG `AdvSetting` budget limit columns | NOT_FOUND dedicated | **MEDIUM** — advertising spend controls, not ad_control domain |

### Async loaders / progress

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/handlers/keyword_settings.py` | aiogram | keyword open | handlers using `ChatActionSender.typing` | profile loaders | — | — | READ | `test_keyword_v3_profile_loader.py` | **MEDIUM** — Telegram “loading” UX |
| `app/client_bot/user_interface/handlers/adv_excel_roundtrip.py` | aiogram | import | handlers | — | `_ProgressReporter` | — | WRITE bulk | NOT_FOUND | **HIGH** — long-running job progress pattern |
| `app/client_bot/user_interface/views/messages/main_adv_setting_menu/adv_setting_menu.py` | aiogram | menu open | `AdvSettingMenu.__call__` | many Redis/CH managers (`StatsFreshnessManager`, `PlanFactReader`, etc.) | `TextWithKeyboardAndImage` | `AdvSetting`, `ComplexAdv` | READ | `tests/unit/client_bot/test_adv_setting_menu_keyboard.py` | **HIGH** — aggregate async read for status block |

### Pagination / filtering

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/message_templates/templates.py` | aiogram | — | `TextWithKeyboardPagination.__call__` | — | abstract `on_page`, `keyboard` | — | READ | NOT_FOUND | **HIGH** — base class for paginated screens |
| `app/client_bot/user_interface/views/keyboards.py` | aiogram | — | `get_keywords_setting_keyboard` (and variants) | — | page slice `start_index:end_index` | `SettingKeywords.page`, `sort_mode` | READ | NOT_FOUND | **HIGH** — keyword list paging + filter modes |
| `app/client_bot/user_interface/handlers/adv_setting/adv_setting.py` | aiogram | `ChoiceAdvPaginator.filter(F.reset_filter)` | reset filter handler | FSM | `AdvCompanyChoicing` | `filter_advs` in FSM | READ | NOT_FOUND | **MEDIUM** — campaign name filter |
| `app/client_bot/user_interface/handlers/admin_panel.py` | aiogram | partner admin callbacks | `_PartnerAdminListState`, list render | `list_partner_stats` | inline keyboards | `_PartnerAdminListState` dataclass | READ (+ payout WRITE elsewhere) | `tests/client_bot/user_interface/handlers/test_admin_panel.py` | **MEDIUM** — admin list paging/sort pattern |
| `app/client_bot/user_interface/views/messages/auto_shelf_bid_control_render.py` | aiogram | — | `slice_bid_points_page`, `bid_point_viewer_page_count` | — | paginated bid viewer text | page index | READ | `tests/unit/test_auto_shelf_bid_control_render*.py` | **MEDIUM** — dense numeric table in message text |

### Validation errors

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/handlers/shop_settings.py` | aiogram | FSM message | `set_shop_default_max_cpm` | — | user-visible Russian errors | — | no write on error | NOT_FOUND | **HIGH** — inline validation before PG |
| `app/client_bot/user_interface/handlers/adv_setting/adv_setting.py` | aiogram | — | constants + early returns | `TokenInfoService` | `READ_ONLY_TOKEN_BOT_ACTIVE_MESSAGE`, `ADV_ACCESS_DENIED_MESSAGE` | — | fail-closed | `test_turn_adv_on_read_only_token.py` | **HIGH** — capability-based UI block |
| `app/client_bot/user_interface/handlers/time_settings/logic.py` | aiogram | — | `validate_range` | — | returned to router | — | READ | NOT_FOUND | **MEDIUM** — form validation helper |
| `app/modules/wb_sky_control_plane/kernel/ad_control_validate.py` | pure Python | N/A | `validate_ad_control_changeset` | domain registry | — | `AdControlChangeSetV1`, `ControlPlaneError` | READ_ONLY validate | `tests/unit/wb_sky_control_plane/test_ad_control_changeset_validate.py` | **HIGH** for future Advertising Control API/UI (no Telegram yet) |

### Diagnostic / status rendering

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/views/messages/main_adv_setting_menu/adv_setting_menu.py` | aiogram | menu | `AdvSettingMenu` | `RedisCampaignActivityReasonManager`, `sales_state_short_label`, `load_last_v3_action_display` | long text + keyboard | `SalesStates`, Redis DTOs | READ | `tests/unit/client_bot/test_adv_setting_menu_keyboard.py` | **HIGH** — campaign status dashboard in Telegram |
| `app/modules/shop_runner/service_manager/v3_tick_report_ui/telegram/handlers.py` | aiogram | `V3TickReportOpen/Refresh/Back` | `open_v3_tick_report`, etc. | `V3TickReportRedisCache` | `format_v3_tick_report_text` | FSM keys in `v3_tick_report_ui.py` | READ Redis | `tests/unit/auto_updater_v3/test_v3_tick_report_informer.py`, `tests/unit/client_bot/test_v3_tick_report_back_callback.py` | **HIGH** — V3 diagnostics screen |
| `app/client_bot/user_interface/services/keyword_v3_profile_loader.py` | aiogram | — | `load_keyword_v3_profile_data` | V3 contexts, CH | `format_keyword_v3_profile_block` | `KeywordV3ProfileData`, `KeywordV3DataDiagnostic` | READ | `tests/unit/client_bot/test_keyword_v3_profile_ui.py` | **HIGH** — per-keyword diagnostic block |
| `app/modules/shop_runner/service_manager/keyword_v3_decision_trace_ui/telegram/handlers.py` | aiogram | `KeywordV3DecisionTraceOpen` | `open_keyword_v3_decision_trace` | `keyword_decision_trace_loader` | `KeywordV3DecisionTraceScreen` | — | READ | `tests/unit/client_bot/test_keyword_v3_decision_trace_callbacks.py` | **HIGH** (admin-gated) — deep trace UI |
| `app/modules/ad_control_settings/domain/diagnostics_builder.py` | domain | N/A | `AdControlDiagnosticsBuilder.build` | resolver/headroom pure | — | `AdControlDiagnosticsReportV1` | READ_ONLY | `tests/unit/ad_control_settings/test_registry_and_headroom.py` | **HIGH** for task 4.2 backend diagnostics; **no UI consumer** |
| `app/modules/shop_runner/service_manager/old_modules/setting_auto_updater_v2/adv_control_system/sales_state/sales_state_display.py` | domain | N/A | `sales_state_short_label`, `SALES_STATE_META` | — | — | `SalesStates`, `SalesStateMeta` | READ | NOT_FOUND | **MEDIUM** — legacy sales state letters in menu |

### Permission checks

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/admin_access.py` | aiogram filter | — | `is_bot_admin`, `IsBotAdminFilter` | `settings.extra_admin_telegram_ids` | — | — | — | used in admin tests | **HIGH** — admin-only screens |
| `app/client_bot/ui_access.py` | service | — | `UiAccessResolver.resolve_shop_ui_access` | PG `AdvSetting.bot_active` | — | `UiAccessMode` | READ | `tests/client_bot/user_interface/handlers/test_ui_mode_toggle.py` | **HIGH** — paid vs free control visibility |
| `app/client_bot/user_interface/handlers/adv_setting/adv_setting.py` | aiogram | — | `load_wb_user_cabinet_for_adv_in_session`, `load_adv_for_owner_cabinet_in_session` | — | — | — | gate before WRITE | `test_adv_setting_write_path_hardening.py` | **HIGH** — owner scoping |
| `app/client_bot/middlewars/gate.py` | aiogram middleware | all updates | `GateMiddleware` | PG `User.passed_gate` | `get_gate_keyboard` | — | — | integration gate tests | **LOW** for advertising (entry gate) |
| `app/client_bot/user_interface/handlers/add_white_phrases.py` | aiogram | — | `load_adv_card_ab_hold_mode_in_session` + `is_ab_hold_structural_freeze` | — | — | `card_ab_hold_mode` | blocks WRITE | freeze-gate tests in card_ab_hold suite | **HIGH** — mutation policy UX |

### V3 settings UI (explicit)

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/modules/shop_runner/service_manager/v3_rollout_aggressiveness_toggle/telegram/handlers.py` | aiogram | `V3RolloutAggMenuOpen`, `V3RolloutAggSet` | `open_v3_rollout_menu`, set handler | `data_manager` refresh | `build_v3_rollout_submenu_markup` | FSM rollout keys | PG `AdvSetting.aggressiveness` | NOT_FOUND dedicated handler test | **HIGH** |
| `app/modules/v3_calibration_step_setting/telegram_handler.py` | aiogram | `V3CalibrationStepChange` | see Forms | — | `v3_calibration_step_ui` | — | PG calibration cap | `test_v3_calibration_step_setting_handler.py` | **HIGH** |
| `app/client_bot/user_interface/services/keyword_v3_ui_sort.py` | aiogram | — | `enrich_keywords_v3_list_profiles` | CH profiles | used in keyword list | — | READ | `tests/unit/test_v3_ui_sort.py` | **MEDIUM** |
| `app/client_bot/user_interface/views/messages/last_v3_action_informer.py` | aiogram | — | `load_last_v3_action_display` | Redis `LastV3UpdaterAction` | embedded in menu text | — | READ | docks + unit informer tests | **HIGH** |
| `docks/V3_UPDATER_VALIDATION.md` | docs | — | — | — | UI behavior spec | — | — | — | **HIGH** for product semantics |

### Advertising controls (existing, not `ad_control_settings`)

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/handlers/auto_shelf_bid_control_menu.py` | aiogram | `callbacks` ASB prefix | shelf bid handlers | `AutoShelfBidControlTelegramService` | `auto_shelf_bid_control_render.*` | FSM `states` | PG/Redis via manager | `tests/unit/test_auto_shelf_bid_control_menu_handler.py` | **MEDIUM** — shelf bid control UX |
| `app/client_bot/user_interface/handlers/auto_budget_watchdog_toggle.py` | aiogram | toggle callbacks | handler | activity control backend | menu buttons | `AdvSetting` flags | PG | integration `test_auto_adv_active_control.py` | **MEDIUM** — campaign activity |
| `app/modules/sales_plan_settings/telegram/` | aiogram | `SalesPlanSettingsMenu` | `plane_settings_menu_handler` + `setting_handlers/*` | plan/CPO modules | `SalesPlanSettingsMenuMessage` | FSM strings | PG plan fields | `tests/unit/sales_plan_settings/*` | **HIGH** — plan/max CPO advertising economics |
| `app/modules/wb_sky_control_plane/models/ad_control_changeset.py` | domain/API | N/A | N/A | `validate_ad_control_changeset` | N/A | `AdControlChangeSetV1`, shop/campaign ops | apply layer PG (no UI) | `tests/unit/wb_sky_control_plane/test_ad_control_*` | **HIGH** for 4.2 **transport**; UI **NOT_FOUND** |

### Telegram admin (non-advertising ops)

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/handlers/admin_panel.py` | aiogram | admin callbacks + FSM | `show_admin_panel`, `grant_user_gate_in_session`, partner payout flows | `partner_stats`, Redis cache keys | `InlineKeyboardMarkup` | `AdminGrantGate`, `AdminPartnerList`, … | PG `User`, payouts | `tests/client_bot/user_interface/handlers/test_admin_panel.py`, integration PG seam tests | **LOW** for advertising control (partners/gates) |
| `app/client_bot/user_interface/handlers/get_shop_for_admin.py` | aiogram | UUID message filter | `AdminsGetShopFilter`, jump to `ShopMenu` | PG lookup by shop UUID | — | — | READ | NOT_FOUND | **LOW** — admin navigation only |
| `app/modules/cabinet_bonus_manager/`, `app/modules/admin_user_balance/` | aiogram | `AdminPanel`, `AdminUserBalance` callbacks | (included via routers) | billing | — | — | WRITE balance | NOT_FOUND in this scan | **LOW** |

---

## Router composition (entry)

`app/client_bot/common_routers.py` — `common_router.include_routers(...)` wires V3 UI routers (`v3_tick_report_ui_router`, `v3_calibration_step_setting_router`, `keyword_v3_decision_trace_ui_router`, `SalesPlanSettingsMenuRouter`, etc.) plus core handlers (`adv_setting`, `shop_settings`, `time_settings`, `campaign_activity`, `auto_shelf_bid_control_menu`).

`app/client_bot/global_router.py` (not fully read) + `create_client_bot_dispatcher` attach middleware chain.

---

## Gaps for task 4.2 (Advertising Control + Diagnostics UI)

| Item | Status |
|------|--------|
| Telegram UI for `app/modules/ad_control_settings/**` | **NOT_FOUND** |
| Web/HTML campaign settings admin | **NOT_FOUND** |
| `ad_control` symbols under `app/client_bot/**` | **NOT_FOUND** (grep) |
| Diagnostics report rendering for `AdControlDiagnosticsReportV1` | Domain + tests only; **no formatter/handler** |

---

## Short signatures (evidence)

```python
# app/client_bot/admin_access.py
def is_bot_admin(telegram_id: int) -> bool: ...

# app/client_bot/user_interface/handlers/start/start.py
@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def select_shop(...) -> None: ...

# app/modules/wb_sky_control_plane/kernel/ad_control_validate.py
def validate_ad_control_changeset(changeset, shop_snapshots, campaign_snapshots): ...

# app/modules/ad_control_settings/domain/diagnostics.py
@dataclass(frozen=True, slots=True)
class AdControlDiagnosticsReportV1: ...
```
