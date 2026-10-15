---
cursor:
  subagentId: "bc-756debf6-0cae-5e5c-b4d0-6b9aa5916a22"
---

# WB Sky — campaign settings architecture inventory (READ-ONLY)

**Authority SHA:** `23c0671f372f0435b13a3573ec8990b4303b3e4a`  
**Ref:** `origin/stage` — `Merge pull request #448 from revoluxe-ai/cursor/cloud-project-bootstrap-8b4b` (2026-10-05 16:38:29 +0000)  
**Local HEAD:** `751e7bd2965a2d35941c5827a13cfab0ad6fc588` (≠ `origin/stage`; all citations below are `origin/stage` blobs)

---

## Executive answer: is Excel the only mutation UI?

**No.** Excel is one of several **human-facing** bulk editors. Production **PostgreSQL** campaign settings are also written by:

- **Telegram bot** handlers (toggles, numeric inputs, keyword UI, schedule UI, shelf menu, A/B Hold UI, sales-plan handlers, etc.).
- **shop-runner** automation (`ServiceManager`, `auto_updater_v3`, legacy `setting_auto_updater*`, keyword maintenance services).
- **Background/domain services** invoked from bot or runner (`adv_creator`, `relevant_phrase_manager`, `auto_shelf_bid_control_repository`, …).

There is **no** `FastAPI`/HTTP settings API in `app/` on this SHA (`git grep FastAPI` → empty).

Some bot flows mutate **Wildberries live bids** via WB API (`change_cpm`, parts of `change_auto_bid`) **without** persisting those values as `AdvSetting` columns — distinct from PG “settings” authority in `openspec/specs/campaign-settings-history/spec.md`.

---

## Closed changes (reference only — not reopened)

| Change | What it already owns (on `origin/stage`) |
|--------|------------------------------------------|
| `campaign-settings-history` | Promoted spec `openspec/specs/campaign-settings-history/spec.md`; modules `app/modules/campaign_settings_contract/`, `app/modules/campaign_settings_history/`; Excel registry parity tests |
| `ai-package-campaign-settings-snapshot` | Spec `openspec/specs/ai-package-campaign-settings-snapshot`; `CampaignSettingsSnapshotV1`, `PgCampaignSettingsReader`, `campaign_settings_assembler` (read-only export) |
| `ai-package-keyword-performance-history` | Keyword performance history (not PG settings write path) |
| `ai-package-full-export` | ZIP exporter wiring; `campaign_settings_snapshot` card |
| `shop-wide-common-sales-collection` / `shop-wide-campaign-data-collection` | Shop-wide **read** collection; not settings mutation |

---

## Capability matrix

### 1. Excel import/export (campaign settings / bids / keywords / budgets)

| | |
|--|--|
| **Status** | **PARTIAL** |
| **Owner** | `app/client_bot/user_interface/services/adv_excel_roundtrip/` (+ handler `handlers/adv_excel_roundtrip.py`); keyword `target_place` workbook: `cpm_target_place_workbook.py` + `handlers/cpm_builder.py` |
| **Code paths** | Export: `export_build:build_adv_excel_rows` → `excel_io:write_adv_excel_workbook`; Import: `import_apply:apply_adv_excel_rows` (handler `adv_excel_roundtrip.py` ~L191); Target-place: `apply_target_place_workbook` / `apply_target_place_rows_in_session` (`cpm_target_place_workbook.py`) |
| **Contract** | `schema.py`: `EXCEL_TEMPLATE_VERSION = 8`; columns from `campaign_settings_contract.excel_*`; spec requirement “Excel is a human-facing projection” in `openspec/specs/campaign-settings-history/spec.md` §Excel |
| **Missing / invariant** | **Two Excel surfaces:** shop-wide adv workbook (per active `AdvSetting` row + shelf columns) vs per-campaign **target_place** workbook (`KeywordSetting.target_place` only). Registry classifies `KeywordSetting` Excel fields, but main roundtrip does **not** export/import keyword rows. `card_ab_hold_mode` explicitly **excluded** from Excel apply (`import_apply.py` module doc; decision `card-ab-hold-write-path-ownership` §9). Budget **top-up** / WB wallet not in Excel path on this slice |
| **Risk** | Operators may assume one Excel covers all registry-“editable” keyword fields; drift if new fields added only to registry but not to a workbook UX |
| **Next action** | Document dual-workbook matrix in runbook; parity test already guards main template ↔ registry |

**Writable via main adv Excel (`apply_adv_excel_rows`):** `EDITABLE_ADV_SETTING_COLUMNS` → `setattr(adv, field, val)` on `AdvSetting`; shelf fields via `AutoShelfBidControlSettings` create/update (`_get_or_create_default_shelf_settings`, `session.add`); special case `max_price_for_order` + `substitute_fact_cpo_for_max` (`sales_plan_settings.v3_raise_max_cpo`). Commits: `await session.commit()` end of `apply_adv_excel_rows`.

---

### 2. Campaign settings field registry

| | |
|--|--|
| **Status** | **READY** (domain contract); **PARTIAL** (no single “mutation capability map” for bot/runner) |
| **Owner** | `app/modules/campaign_settings_contract/` — `registry.py`, `canonical.py`, `inventory.py`; ADR `openspec/decisions/campaign-settings-contract-ownership/decision.md` |
| **Code paths** | Public API: `campaign_settings_contract.__init__` exports `REGISTERED_SOURCES`, `ExcelPolicy`, `HistoryPolicy`, `excel_editable_fields`, `build_canonical_settings_snapshot`, `validate_registry*`, `discover_runtime_orm_sources` |
| **Contract** | Registered sources (inventory): `AdvSetting`, `KeywordSetting`, `AdvTimeSettings`, `AdvTimeWeekMask`, `AutoShelfBidControlSettings` (`inventory.py` `_REGISTERED_SOURCE_FILES`). `SCHEMA_VERSION = 1` (`canonical.py`). Tests: `tests/unit/test_campaign_settings_contract_registry.py`, `test_campaign_settings_excel_registry_parity.py`, `test_campaign_settings_excel_characterization.py` |
| **Missing** | Registry defines **history + Excel policy**, not **which Telegram/worker entrypoints** may write each field; no central write-gate layer |
| **Risk** | New ORM field can pass registry CI but be writable from an unexpected handler without registry linkage |
| **Next action** | Keep inventory gate mandatory on ORM changes; optional future: write-path catalog test (out of scope for closed change) |

---

### 3. Current settings read model (live PG state, not history)

| | |
|--|--|
| **Status** | **PARTIAL** — multiple parallel read models |
| **Authority** | PostgreSQL per `campaign-settings-history` spec + `campaign-settings-contract-ownership` decision |
| **Canonical aggregate (history + hash)** | `PostgresCampaignSettingsReader.load_cabinet` → `CampaignSettingsSources` → `build_canonical_settings_snapshot` (`pg_reader.py`, `collector.py`, `canonical.py`) — **read-only**, used by history collector |
| **History collector runtime** | `campaign_settings_history.runtime:collect_one_locked_cabinet`; CLI `python -m app.modules.campaign_settings_history` (`cli.py`, `updater.py`) — **does not write PG** |
| **AI Package export read** | `PgCampaignSettingsReader.load_adv_settings` → `campaign_settings_assembler` → `CampaignSettingsSnapshotV1` (`ai_package_v1/readers/pg_campaign_settings_reader.py`, `export/campaign_settings_assembler.py`) — **AdvSetting-centric** detailed snapshot; **not** identical to full multi-source canonical blob |
| **Bot / runner UI** | Ad-hoc `select(AdvSetting)` / `session.get` across handlers (e.g. `adv_setting.py`, menus) — **no shared “current settings service”** |
| **Contract** | `openspec/specs/campaign-settings-history/spec.md` (PG authority); `openspec/specs/ai-package-campaign-settings-snapshot` (export DTO); `CampaignSettingsSnapshotV1` / `SCHEMA_VERSION` in `domain/campaign_settings_snapshot_v1.py` |
| **Missing** | Single product read API merging all registered sources for UI; explicit seam doc between canonical history snapshot vs AI snapshot vs raw ORM |
| **Risk** | Consumers mix Redis tick DTOs / AI export / raw ORM (called out in archived `ai-package-campaign-settings-snapshot` proposal) |
| **Next action** | For new readers, prefer `PostgresCampaignSettingsReader` + canonical builder or AI assembler — document choice per consumer |

**Explicitly NOT current-settings authority:** ClickHouse `campaign_settings_history` table (`clickhouse_repository.py`); change events are append-only history.

---

### 4. Production PG write entrypoints (proved on `origin/stage`)

Grouped by entry surface. Symbols are commit paths to PG unless noted.

#### 4a. Excel (human bulk)

| Entry | Symbol / file |
|-------|----------------|
| Shop adv workbook import | `handlers/adv_excel_roundtrip.py` → `import_apply.apply_adv_excel_rows` |
| Keyword target_place workbook | `handlers/cpm_builder.py` → `cpm_target_place_workbook.apply_target_place_workbook` → `apply_target_place_rows_in_session` |

#### 4b. Telegram — `AdvSetting` (`update(AdvSetting)` or setattr+commit)

Files with `update(AdvSetting)`:

- `client_bot/.../adv_setting/adv_setting.py` (incl. `apply_campaign_defaults`, `TurnBot`, minus phrases, etc.)
- Toggles: `auto_add_only_relevant_phrase_toggle.py`, `auto_budget_watchdog_toggle.py`, `auto_common_budget_toggle.py`, `auto_update_exponent_toggle.py`, `bidder_coroutine_type_toggle/handlers.py`, `common_bid_toggle.py`, `common_budget_mode_toggle.py`, `incremental_stats_toggle.py`, `orders_source_toggle.py`, `predict_ctr_mode_toggle.py`, `rec_system_mode_toggle.py`, `reset_place_setting.py`, `sales_predict_method_toggle.py`, `target_position_mode_toggle.py`, `white_list_mode_toggle.py`
- `connect_existing_advs.py`
- Modules: `bidder_step_setting/telegram_handler.py`, `hide_zero_views_toggle/telegram/handlers.py`, `v3_calibration_step_setting/telegram_handler.py`, `sales_plan_settings/telegram/setting_handlers/*`, `shop_runner/auction_boost_mode_settings/telegram/handlers.py`, `v3_rollout_aggressiveness_toggle/telegram/handlers.py`
- `adv_creator/backend/main_manager.py`
- `relevant_phrase_manager/relevant_phrase_manager.py`
- **shop-runner Telegram:** `old_modules/auto_updater_target_place/telegram/handlers.py`, `white_list_updater/.../telegram/handlers.py`
- **A/B Hold Telegram:** `auto_updater_v3/card_ab_hold/telegram/handlers.py` (`setattr` + `commit` in `disable_card_ab_hold_in_session`); `confirm_handlers.py` (keyword snapshot attr)

Additional setattr without `update()`:

- `campaign_activity.py` — daily limit attrs on `AdvSetting` + `commit`
- `wb_shop_data_manager.py` — `promo_fraction` overlay on `AdvSetting`

#### 4c. Telegram — `KeywordSetting`

- `update(KeywordSetting)`: `add_white_phrases.py`, `keyword_relevant_setting.py`, `adv_setting/utils/keyword_updater.py`
- `keyword_settings.py` — multiple `session.commit()` paths (keyword config UI)
- `cpm_builder.py` — inline target_place edits (non-workbook)
- `cpm_target_place_workbook.py` — workbook apply

#### 4d. Telegram — schedule (`AdvTimeSettings` / `AdvTimeWeekMask`)

- `client_bot/.../time_settings/repository.py` — `pg_insert` upserts; wired from `time_settings/router.py`

#### 4e. Telegram + runner — shelf bid (`AdvSetting` flags + `AutoShelfBidControlSettings`)

- `auto_shelf_bid_control_menu.py` → `auto_shelf_bid_control_repository.py` (`session.add`, updates `adv.auto_shelf_bid_control_*`)
- Excel import path (4a) also creates/updates shelf rows

#### 4f. shop-runner workers (no Telegram)

| Area | File(s) |
|------|---------|
| Service manager core | `shop_runner/service_manager/manager.py` — `update(AdvSetting)`, `update(KeywordSetting)` |
| Auto updater V3 | `services/auto_updater_v3/applier.py` — `KeywordSetting` strategy_mode; `tick_ledger.py`; `target_place_sync.py` (read-heavy) |
| Card A/B Hold | `card_ab_hold/epoch_write.py`, `epoch_pipelines.py`, `setup_apply.py`, `hold_guards.py`, `keyword_tp_bulk.py`, `emergency.py` |
| Legacy auto updaters | `setting_auto_updater/setting_auto_updater.py`, `first_key_updater`, `auto_white_list_updater`, `setting_auto_updater_v2/.../target_place_*_executor.py`, `white_list_*_executor.py` |
| Keyword maintenance | `white_list_trimmer.py`, `delete_keywords_from_wl_by_mean_auto_ctr_manager.py`, `keywords_target_place_updater/keyword_target_place_updater.py` (ORM setattr + `commit`) |

#### 4g. Domain services (invoked from bot/runner)

- `adv_creator/backend/main_manager.py`
- `relevant_phrase_manager/relevant_phrase_manager.py`

#### 4h. WB API only (not PG settings authority)

- `change_cpm.py` — `BidderWBApi.update_cpm` (no PG commit for CPM)
- `change_auto_bid.py` — bid flow (load `AdvSetting`; WB path in file body beyond excerpt)

---

### 5. Campaign-settings writers (cross-cutting)

| | |
|--|--|
| **Status** | **PARTIAL** — many owners, no facade |
| **Owner pattern** | Each feature module owns its write slice (Telegram handler or shop-runner service) |
| **Contract** | Implicit: SQLAlchemy models in `app/modules/common_slaves/wildberries/models/`; registry classifies fields but does not route writes |
| **Missing** | Central write router; unified audit of who may set each `SemanticRole.SETTING` field |
| **Risk** | Excel + V3 applier + manual UI can touch overlapping fields (e.g. `target_place`, plan/CPO fields) without single coordination layer |
| **Next action** | When adding fields, update registry + identify all write files via `git grep` on field name |

---

## Evidence index (high-signal `origin/stage` paths)

| Topic | Path |
|-------|------|
| Excel apply | `app/client_bot/user_interface/services/adv_excel_roundtrip/import_apply.py:185` `apply_adv_excel_rows` |
| Excel schema v8 | `app/client_bot/user_interface/services/adv_excel_roundtrip/schema.py` |
| Registry | `app/modules/campaign_settings_contract/registry.py` |
| Canonical snapshot | `app/modules/campaign_settings_contract/canonical.py` `SCHEMA_VERSION`, `build_canonical_settings_snapshot` |
| PG read aggregate | `app/modules/campaign_settings_history/pg_reader.py` `PostgresCampaignSettingsReader` |
| History runtime | `app/modules/campaign_settings_history/runtime.py` |
| AI read export | `app/modules/ai_package_v1/readers/pg_campaign_settings_reader.py`, `export/campaign_settings_assembler.py` |
| Contract ADR | `openspec/decisions/campaign-settings-contract-ownership/decision.md` |
| Promoted spec | `openspec/specs/campaign-settings-history/spec.md` |

---

## Summary status table

| Capability | Status |
|------------|--------|
| Main adv Excel roundtrip (AdvSetting + shelf) | PARTIAL (scoped; no keywords row; AB hold out) |
| Target-place Excel workbook | READY (narrow KeywordSetting.target_place) |
| Field registry + CI inventory | READY |
| Excel ↔ registry parity | READY (unit tests on `origin/stage`) |
| Canonical current-state read (history pipeline) | READY |
| Unified current-settings read for product UI | GAP |
| AI Package settings snapshot read | PARTIAL (AdvSetting-focused assembler vs full canonical) |
| Production write entrypoints | PARTIAL (many; Telegram + runner + Excel; no HTTP API) |
| Write capability map from registry | GAP |
