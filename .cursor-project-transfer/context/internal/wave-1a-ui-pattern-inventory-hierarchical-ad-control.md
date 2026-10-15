---
cursor:
  subagentId: "bc-b4430ca2-fc86-5212-9188-08a2bc1ed732"
---

# WAVE 1A — Existing UI pattern inventory (task 4.2 prep)

**Repo:** `/agent/repos/adv-bot`  
**OpenSpec change:** `hierarchical-ad-control-settings`  
**Task 4.2 expectation (read-only):** «Advertising Control + Diagnostics/Test using same resolver; no writes» (`owner-contract.md`, `tasks.md` §4.2). Domain lives in `app/modules/ad_control_settings/`; **no Telegram/web UI wired yet**.

---

## Executive answers

### 1) User-facing UI stack

| Layer | Role |
|-------|------|
| **Telegram / aiogram 3** | Primary product UI — shops, campaign pickers, per-campaign settings, diagnostics |
| **FastAPI** | Transport shell for Telegram webhook + health (`client_bot_run.py`); not an HTML admin |
| **ABSENT** | Jinja templates, Vue/React SPA, browser admin for WB Sky settings |

**Entrypoints**

- `client_bot_run.py` — `FastAPI` lifespan + webhook or `start_polling()` → `create_client_bot_dispatcher()` → `global_router` → `common_router`
- `app/client_bot/dispatcher_factory.py` — `create_client_bot_dispatcher`
- `app/client_bot/global_router.py` — middleware (Gate, Phone, Channel), scenes (bonus, user balance)
- `app/client_bot/common_routers.py` — aggregates all feature routers
- `app/client_bot/bot.py` — `get_bot()` / aiogram `Bot`
- `error_collector/main.py` — separate FastAPI (ops), not user settings UI

### 2) Existing V3 settings UI (exact paths)

V3 controls are **campaign-scoped**, embedded in `AdvSettingMenu` keyboard when `adv_setting.bot_active` and paid UI access:

| Feature | Keyboard entry | Handlers | Write path |
|---------|----------------|----------|------------|
| V3 tick report (diagnostics, read Redis) | `keyboard/v3_tick_report_button.py`, `v3_tick_report_ui.py` | `app/modules/shop_runner/service_manager/v3_tick_report_ui/telegram/handlers.py` | Read-only |
| V3 calibration step cap | `keyboard/v3_calibration_step_ui.py` | `app/modules/v3_calibration_step_setting/telegram_handler.py` | PG `AdvSetting` update |
| V3 rollout aggressiveness | `keyboard/v3_rollout_aggressiveness_ui.py` | `app/modules/shop_runner/service_manager/v3_rollout_aggressiveness_toggle/telegram/handlers.py` | PG `AdvSetting.aggressiveness` |
| V3 Raise MAX CPO (sales plan) | `app/modules/sales_plan_settings/telegram/keyboards.py` | `setting_handlers/toggle_v3_raise_max_cpo.py` | PG `AdvSetting.substitute_fact_cpo_for_max` |
| Keyword V3 profile block (diagnostics in keyword list) | `views/keyword_v3_profile_ui.py` + loader | `services/keyword_v3_profile_loader.py`, used from `views/messages/messages.py` (`KeywordSettingMessage`) | Read-only |
| Keyword V3 decision trace (admin debug) | `keyword_v3_decision_trace_ui/telegram/` | `handlers.py`, `messages.py` | Read-only Redis loader |
| Card A/B hold (V3 gate) | `card_ab_hold/telegram/handlers.py` | same module | Mixed (settings + polls) |

Orchestration comment: `keyboard/keyboard.py` L404 — «V3-only runtime (D3): no version-toggle UI».

### 3) Closest patterns

| Need | Closest existing |
|------|------------------|
| **Shop settings form** | `ShopMenu` (`app/modules/shop_menu/message.py`) + `shop_settings.py` FSM for `WBCabinet.default_max_cpm`; shop keyboard `build_shop_main_keyboard` |
| **Campaign list / table** | `AdvCompanyChoicing` + `get_advs_keyboard_with_paginator` (`views/messages/messages.py`, `views/keyboards.py`); handlers `adv_setting/adv_setting.py`, `start/start.py` (`ChoiceAdvPaginator`) |

### 4) Validation errors & permission denials

| Mechanism | Where |
|-----------|--------|
| Inline user messages | FSM handlers (`shop_settings.py`, `v3_calibration_step_setting/telegram_handler.py`, `time_settings/router.py` `callback.answer(alert=...)`) |
| Global errors | `user_interface/handlers/exceptions.py` — `ApiForbiddenError` → «Нет доступов к данному магазину»; network, `CardNotFoundInDB`, message-too-long |
| Campaign access | `adv_setting.py` — `CABINET_ACCESS_DENIED_MESSAGE`, `ADV_ACCESS_DENIED_MESSAGE`, `READ_ONLY_TOKEN_BOT_ACTIVE_MESSAGE` |
| Admin-only UI | `keyword_v3_decision_trace_ui` — `_require_admin` → «Нет доступа»; `IsBotAdminFilter` on `admin_panel.py` |
| Paid/free gating | `ui_access.py` `UiAccessResolver`; keyboard rows hidden when `UiAccessMode.FREE` |
| Excel/schema validation | `services/adv_excel_roundtrip/schema.py` → `ValueError` with Russian messages (roundtrip flow) |

### 5) Pagination / filter helpers

| Helper | Location | Page size |
|--------|----------|-----------|
| `get_advs_keyboard_with_paginator` | `views/keyboards.py` | `AdvCompanyChoicing.on_page` = 20 |
| `ChoiceAdvPaginator` callback | `views/callbacks.py` | FSM `filter_advs` keyword filter |
| `get_shops_list_keyboard` / `ShopsListPage` | `handlers/shop_choice_message.py` | `SHOPS_PER_PAGE` |
| Keyword list pages | `adv_keyword_messages/adv_keyword_messages.py` | `_on_page = 24` |
| Admin partner list | `admin_panel.py` | `_PARTNER_LIST_PAGE_SIZE = 8` |
| Auto-shelf bid viewer | `auto_shelf_bid_control_menu.py` + render helpers | `bid_point_viewer_page_count` |
| Keyword V3 decision trace | paginated screen in formatter tests | `tests/unit/client_bot/test_keyword_v3_decision_trace_ui.py` |

---

## Pattern inventory (structured rows)

### A. Navigation & shop-level

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/modules/shop_menu/message.py` | aiogram | (message render via `ShopMenu`); callbacks from `build_shop_main_keyboard` | `ShopMenu`, `build_shop_main_keyboard` | `TokenInfoService`, `UiAccessResolver`, `Pricer`, Redis billing/balance | `TextWithKeyboard` subclass | `WBUserCabinet`, `WBCabinet`, `UiAccessMode`, FSM shop id | Read-mostly; shop actions delegate to handlers | `tests/client_bot/user_interface/handlers/test_shop_mass_adv_ops_menu.py`, `test_onboarding_shops_list_page.py` | **HIGH** shop panel shell |
| `app/client_bot/user_interface/handlers/shop_settings.py` | aiogram | `ChangeShopDefaultMaxCPM` → FSM `ShopDefaultMaxCPM.waiting_for_new_default_max_cpm` | `change_shop_default_max_cpm`, `set_shop_default_max_cpm` | — | `ChangeShopDefaultMaxCPMMessage` | FSM + `WBCabinet.default_max_cpm` | Direct PG `update(WBCabinet)` | NONE dedicated; covered indirectly via integration | **HIGH** shop numeric form |
| `app/client_bot/user_interface/handlers/shop_choice_message.py` | aiogram | `ShowShopsList`, shop pick callbacks | `ShopsListPage` | token status set | `TextWithKeyboard` | `list[WBUserCabinet]` + page | Read-only | `tests/client_bot/user_interface/test_onboarding_shops_list_page.py` | **MEDIUM** multi-shop list |
| `app/client_bot/user_interface/handlers/ui_mode_toggle.py` | aiogram | `UiModeToggle` | `toggle_ui_mode_handler` | `UiModeService` (Redis) | re-render `ShopMenu` | admin-only FREE/PAID preview | Redis write | `tests/client_bot/user_interface/handlers/test_ui_mode_toggle.py` | **LOW** (admin debug access mode) |
| `app/client_bot/user_interface/handlers/start/start.py` | aiogram | `/start`, `ShopMassAdvOpsMenu`, `ChoiceAdvPaginator`, shop open | `shop_menu_process`, `open_shop_mass_adv_ops_menu`, paginator handlers | various | `ShopMenu`, `AdvCompanyChoicing` | FSM | Mixed | `tests/client_bot/test_callback_start_registration.py`, `test_start_registration.py` | **HIGH** routing hub |

### B. Campaign list / table / row actions

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/views/messages/messages.py` | aiogram | (screen) | `AdvCompanyChoicing` | `redis_manager.check_last_24_hours` | `TextWithKeyboardPagination` | `list[AdvSetting]`, page, `filter_advs` in FSM | Read-only list | integration `tests/integration/test_default_settings_integration.py` (AdvCompanyChoicing paths) | **HIGH** campaign table |
| `app/client_bot/user_interface/views/keyboards.py` | aiogram | `ChoiceAdvPaginator`, `Adv(action=select)` | `get_advs_keyboard_with_paginator` | — | Inline keyboard rows per campaign | slice of `AdvSetting` | Read-only | via adv_setting tests | **HIGH** paginated rows |
| `app/client_bot/user_interface/handlers/adv_setting/adv_setting.py` | aiogram | `Adv`, `ChoiceAdvPaginator`, `TurnBot`, filter FSM | `adv_setting` module routers | `apply_paid_auto_management_transition`, `TokenInfoService`, `WBShopDataManager` | `AdvSettingMenu`, `AutoManagementLanding` | `AdvSetting`, `WBUserCabinet` | PG + services for bot on/off | `tests/client_bot/user_interface/handlers/test_adv_setting.py` | **HIGH** per-campaign entry |
| `app/client_bot/user_interface/views/messages/main_adv_setting_menu/adv_setting_menu.py` | aiogram | opened via `Adv` callback | `AdvSettingMenu` | Redis managers, `PlanFactReader`, `RedisCampaignActivityReasonManager` | `TextWithKeyboardAndImage` | `AdvSetting` + loaded metrics DTOs | Read-only display (settings via other handlers) | `tests/client_bot/test_adv_setting_menu_v3_obnovl.py`, `test_adv_setting_menu_traffic_clicks.py` | **HIGH** campaign detail + status diagnostics |
| `app/client_bot/user_interface/handlers/connect_existing_advs.py` | aiogram | `ConnectExistingAdvs` FSM chain | `connect_existing_advs_start`, many states | `get_connect_existing_candidates` | text + inline keyboards | FSM candidate lists | PG upsert `AdvSetting` | NONE in `tests/client_bot` (module tests elsewhere) | **MEDIUM** WB-sourced campaign rows |
| `app/client_bot/user_interface/handlers/get_shop_for_admin.py` | aiogram | admin text UUID / numeric adv_id | `AdminsGetShopFilter`, `AdminsGetAdvByIdFilter` | — | `ShopMenu` / `AdvSettingMenu` | admin jump | Read-only navigation | NONE | **LOW** admin shortcut |

### C. Campaign settings forms & toggles (advertising-adjacent)

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/modules/sales_plan_settings/telegram/` | aiogram | `SalesPlanSettingsMenu` | `main_handler.plane_settings_menu_handler` | — | `SalesPlanSettingsMenuMessage` | `AdvSetting` by `adv_id` | Sub-handlers PG update | NONE in client_bot folder | **MEDIUM** nested settings submenu |
| `app/modules/sales_plan_settings/telegram/setting_handlers/toggle_v3_raise_max_cpo.py` | aiogram | `V3RaiseMaxCpoToggle` | `toggle_v3_raise_max_cpo_handler` | — | re-open menu message | `AdvSetting.substitute_fact_cpo_for_max` | Direct PG update | NONE | **MEDIUM** per-feature toggle row |
| `app/client_bot/user_interface/handlers/time_settings/router.py` | aiogram | `TS` callback prefix | many handlers + `_edit_message_content` | `TimeSettingsRepository` | `render.py` screens A–P | `TimeSettingsSession` / `TimeSettingsState` | PG `AdvTimeSettings` | `tests/client_bot/time_settings/test_persistence.py` | **MEDIUM** complex form + in-place edit |
| `app/client_bot/user_interface/handlers/campaign_activity.py` | aiogram | campaign activity callbacks | FSM limit editors | `load_total_spend_snapshot` | `CampaignActivityMenu` | `AdvSetting` budget fields | PG update | NONE | **MEDIUM** structured limits form |
| `app/client_bot/user_interface/handlers/auto_shelf_bid_control_menu.py` | aiogram | `callbacks` + FSM | shelf bid handlers | `AutoShelfBidControlTelegramService` | render modules | service view DTOs | Service → PG/WB | NONE | **MEDIUM** diagnostics + settings |
| `app/modules/white_list_mode_settings/telegram/` | aiogram | `WhiteListModeMenu` | `main_handler` | — | `main_message` | `AdvSetting` | PG | NONE | **LOW** |
| `app/modules/predict_ctr_exponent_settings/telegram/handlers.py` | aiogram | module callbacks | handlers | — | — | `AdvSetting` | PG | NONE | **LOW** |
| `app/modules/wb_adv_updater/modules/bidder/tg_bot_handlers/on_off_controller.py` | aiogram | bidder callbacks | on/off handlers | bidder services | — | `AdvSetting` | WB + PG | NONE | **LOW** legacy bidder |

### D. Async loaders & diagnostic / status rendering

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/modules/shop_runner/service_manager/v3_tick_report_ui/telegram/handlers.py` | aiogram | `V3TickReportOpen/Refresh/Back` | `open_v3_tick_report`, etc. | `V3TickReportRedisCache` | `format_v3_tick_report_text` | `V3TickReportSnapshot` | **Read-only** | `tests/unit/client_bot/test_v3_tick_report_back_callback.py` | **HIGH** diagnostics screen (no writes) |
| `app/modules/shop_runner/service_manager/keyword_v3_decision_trace_ui/telegram/messages.py` | aiogram | `KeywordV3DecisionTraceOpen` | `KeywordV3DecisionTraceScreen` | `load_keyword_decision_trace_view` | `format_keyword_decision_trace_screen` | loader ViewData | **Read-only** | `tests/unit/client_bot/test_keyword_v3_decision_trace_ui.py` | **HIGH** resolver-style diagnostic UI |
| `app/client_bot/user_interface/services/keyword_v3_profile_loader.py` | aiogram (consumer) | — | — | `diagnose_keyword_v3_data` | `keyword_v3_profile_ui.format_keyword_v3_profile_block` | `KeywordV3ProfileData`, `KeywordV3DataDiagnostic` | Read-only | NONE dedicated | **HIGH** inline diagnostic lines |
| `app/client_bot/user_interface/views/messages/main_adv_setting_menu/adv_setting_menu.py` | aiogram | — | `_status_suffix` | `RedisCampaignActivityReasonManager` | caption text | `CampaignActivityReason` + `reason_code_to_display_text` | Read-only | menu tests | **HIGH** reason-code status suffixes |
| `app/client_bot/user_interface/views/messages/v3_tick_report_informer.py` | pure formatter | — | — | — | text builder | `V3TickReportSnapshot` | Read-only | NONE | **HIGH** skip-reason / phase mapping |
| `app/modules/ad_control_settings/domain/diagnostics_builder.py` | — | — | — | domain only | — | diagnostics DTOs | N/A (no UI) | unit tests under `tests/unit/.../ad_control*` | **HIGH** target backend for 4.2 (not wired) |

### E. Permission checks & access

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/admin_access.py` | aiogram filter | — | `is_bot_admin`, `IsBotAdminFilter` | — | — | telegram id | — | start registration tests patch ADMINS | **HIGH** |
| `app/client_bot/ui_access.py` | resolver | — | `UiAccessResolver.resolve_shop_ui_access` | PG `AdvSetting.bot_active` | — | `UiAccessMode` | — | used in menu tests | **HIGH** paid feature gating |
| `app/client_bot/middlewars/gate.py` | middleware | all updates | `GateMiddleware` | — | — | User.passed_gate | — | `tests/client_bot/test_gate.py` | **MEDIUM** onboarding gate |
| `app/client_bot/user_interface/handlers/admin_panel.py` | aiogram | admin callbacks + FSM | many `@router.*(IsBotAdminFilter())` | partner PG | inline keyboards | admin FSM states | PG admin writes | `tests/client_bot/user_interface/handlers/test_admin_panel.py` | **LOW** unrelated admin |

### F. Bulk / Excel / shop-wide advertising controls

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/handlers/adv_excel_roundtrip.py` | aiogram | `ExportShopAdvExcel`, `ImportShopAdvExcel` | export/import handlers | `adv_excel_roundtrip` service | — | shop scope | PG via writer | `tests/unit/client_bot/test_adv_excel_ui_parity.py` | **MEDIUM** shop-wide settings transport |
| `app/modules/shop_menu/message.py` | aiogram | `ShopMassAdvOpsMenu` | keyboard only; handlers in `start.py` | — | mass ops submenu | shop | varies by op | `test_shop_mass_adv_ops_menu.py` | **MEDIUM** shop-level campaign ops |

### G. Message / UI framework primitives

| PATH | FRAMEWORK | ROUTE | HANDLER | SERVICE | TEMPLATE/COMPONENT | STATE MODEL | WRITE PATH | TEST COVERAGE | REUSABILITY |
|------|-----------|-------|---------|---------|-------------------|-------------|------------|---------------|-------------|
| `app/client_bot/user_interface/message_templates/templates.py` | aiogram | — | `TextWithKeyboard`, `TextWithKeyboardPagination` | — | base classes | text + keyboard | send_message | — | **HIGH** |
| `app/client_bot/user_interface/handlers/time_settings/router.py` | aiogram | — | `_edit_message_content`, `_safe_edit_reply_markup` | — | edit-in-place pattern | — | — | — | **MEDIUM** for single-message diagnostics |
| `app/client_bot/middlewars/immediate_callback_answer.py` | middleware | all callbacks | ACK before handler | — | — | — | — | `test_immediate_callback_answer.py` | **MEDIUM** UX for slow loaders |

---

## ABSENT (searched)

| Item | Search |
|------|--------|
| **Advertising Control / hierarchical ad_control Telegram UI** | `ad_control`, `AdControl`, `hierarchical` under `app/client_bot` — **0 hits** |
| **Web admin / Jinja settings pages** | `FastAPI`/`APIRouter` in `app/` — none; `templates/` only OpenSpec/specify templates; `static/` only `api_setting.png` |
| **Vue/React frontend** | `frontend/` only `manual_phrase_positions_update/.../telegram` |
| **Product-scope control UI** | `product_control` in `app/client_bot` — **0 hits** |
| **Task 4.2 implementation** | Only planning artifacts; domain in `app/modules/ad_control_settings/` |

---

## Test coverage map (client_bot / UI-adjacent)

| Area | Tests |
|------|-------|
| Campaign menu / V3 caption | `tests/client_bot/test_adv_setting_menu_v3_obnovl.py` |
| V3 decision trace formatting | `tests/unit/client_bot/test_keyword_v3_decision_trace_ui.py` |
| V3 calibration FSM | `tests/unit/test_v3_calibration_step_setting_handler.py` |
| Time settings persistence | `tests/client_bot/time_settings/test_persistence.py` |
| Adv setting handlers | `tests/client_bot/user_interface/handlers/test_adv_setting.py` |
| Admin panel | `tests/client_bot/user_interface/handlers/test_admin_panel.py` |
| Shops list pagination | `tests/client_bot/user_interface/test_onboarding_shops_list_page.py` |
| ad_control domain (no UI) | `tests/unit/wb_sky_control_plane/test_ad_control_changeset_validate.py`, ad_control_settings unit tests |

---

## Reuse guidance for 4.2 (factual, not design)

- **Shop panel:** extend `ShopMenu` / `build_shop_main_keyboard` pattern (shop-scoped callback prefix, return to shop).
- **Campaign table:** clone `AdvCompanyChoicing` + paginator; FSM filter pattern for search.
- **Read-only diagnostics:** mirror `KeywordV3DecisionTraceScreen` (loader → formatter → `TextWithKeyboard`) and/or `v3_tick_report` (new message + Refresh); align with owner-contract **no writes**.
- **Reason codes:** mirror `reason_code_to_display_text` + `_status_suffix` in `adv_setting_menu.py`.
- **Access:** shop user vs `is_bot_admin` for debug surfaces; `UiAccessResolver` for paid controls (4.2 diagnostics may still be visible in free mode if product dictates — not decided in code yet).
- **Backend:** call `ad_control_settings` resolver/diagnostics_builder (domain), not `AdControlChangeSet` apply (dry-run only in slice B).
