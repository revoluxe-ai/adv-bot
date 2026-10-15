---
cursor:
  subagentId: "bc-4f4ebd8e-cfa7-525e-a8fc-0e23b7428dc2"
---

# Campaign-settings mutation paths (read-only inventory)

**Authority branch:** `origin/stage`  
**BASELINE SHA:** `23c0671f372f0435b13a3573ec8990b4303b3e4a` (unchanged after `git fetch origin stage`)

**Architecture note (inventory only):** Accepted decision `openspec/decisions/campaign-settings-contract-ownership/decision.md` — PostgreSQL is authority for *current* settings; registry in `app/modules/campaign_settings_contract/` is classification/normalization SoT, not a write path.

---

## EXCEL PATH summary

| Layer | Path | Role |
|-------|------|------|
| UI entry | `app/client_bot/user_interface/handlers/adv_excel_roundtrip.py` | Callbacks `ExportShopAdvExcel` / `ImportShopAdvExcel`; FSM `AdvExcelRoundtrip.waiting_for_workbook` |
| Shop menu | `app/modules/shop_menu/message.py` | Buttons wire to same callbacks |
| Export | `app/client_bot/user_interface/services/adv_excel_roundtrip/export_build.py` → `excel_io.write_adv_excel_workbook` | Builds rows for *active* campaigns (`active_adv.is_active_adv`) |
| Import I/O | `app/client_bot/user_interface/services/adv_excel_roundtrip/excel_io.py` | `read_adv_excel_upload` |
| Apply | `app/client_bot/user_interface/services/adv_excel_roundtrip/import_apply.py` | `apply_adv_excel_rows`, `verify_user_owns_wb_user_cabinet` |
| Schema | `app/client_bot/user_interface/services/adv_excel_roundtrip/schema.py` | `EXCEL_TEMPLATE_VERSION = 8`; editable/read-only sets from `campaign_settings_contract` (`excel_editable_fields`, `excel_read_only_fields`); `parse_edit_value`, headers `RO__*` / `EDIT__*` |

**What Excel writes (production PG):**

- `AdvSetting` columns in `EDITABLE_ADV_SETTING_COLUMNS` via `setattr(adv, field, val)` after `parse_edit_value`.
- `AutoShelfBidControlSettings` (by first `nmid`) when shelf enabled or any shelf column non-blank; may `session.add` defaults via `_get_or_create_default_shelf_settings`.
- Special: `max_price_for_order` → `resolve_flag_after_max_cpo_decrease` also sets `substitute_fact_cpo_for_max`.
- **Not written:** `card_ab_hold_mode` (excluded from editable registry; Telegram-only per `import_apply` docstring).

**Validation already in import:**

- Non-empty rows; template version match; access to `WBUserCabinet`; row `adv_setting_id` exists; same `wb_cabinet_id`; `is_active_adv` (`active_status` + `bot_active`).
- RO identity parity: `adv_id`, `search_adv_id`, `nmid` vs server.
- Per-cell `parse_edit_value` (types, enums, shelf rules); `plan_for_sales_for_day` / `target_price_for_order` / `max_price_for_order` ≥ 1.
- Shelf: single-NMID campaigns only.
- Fail-fast: `AdvExcelImportError` → global handler (no partial commit).

**Related Excel (not full campaign settings):**

- `app/client_bot/user_interface/handlers/cpm_builder.py` + `cpm_target_place_workbook.py` — keyword `target_place` workbook only (`KeywordSetting`).

---

## WRITERS table

`mutates production?` = writes intended to affect live bot/WB behavior (PG and/or WB). CH history is observability, not current-value authority.

| Path | Symbol | Store | Mutates production? |
|------|--------|-------|---------------------|
| `.../adv_excel_roundtrip/import_apply.py` | `apply_adv_excel_rows` | PG (`AdvSetting`, `AutoShelfBidControlSettings`) | Yes |
| `.../handlers/adv_excel_roundtrip.py` | `import_adv_excel_file`, `export_shop_adv_excel` | — (orchestration) | Via apply |
| `.../cpm_target_place_workbook.py` | `apply_target_place_workbook` | PG `KeywordSetting.target_place` | Yes |
| `app/client_bot/modules/default_settings/` | `apply_*_defaults_*`, `apply_defaults_to_adv_setting` | PG `AdvSetting` (in-memory then caller commits) | Yes |
| `app/client_bot/user_interface/handlers/*` (many) | `update(AdvSetting)` / ORM mutate + `commit` | PG | Yes — toggles, CPM, phrases, budgets, connect-existing, etc. |
| `app/modules/sales_plan_settings/telegram/setting_handlers/*` | plan/CPO toggles | PG `AdvSetting` | Yes |
| `app/client_bot/user_interface/handlers/time_settings/repository.py` | `pg_insert` upserts | PG `AdvTimeSettings`, `AdvTimeWeekMask` | Yes |
| `app/client_bot/user_interface/handlers/keyword_settings.py` | `change_keyword_hard_status_in_session` + v3 sync | PG `KeywordSetting` | Yes |
| `app/modules/shop_runner/.../auto_updater_v3/applier.py` | `apply_v3_actions` | PG `KeywordSetting` (`strategy_mode`, `hard_status`) | Yes |
| `app/modules/shop_runner/.../card_ab_hold/epoch_write.py` (+ pipelines, setup_apply, emergency) | multiple `update(AdvSetting)` | PG `AdvSetting` (AB hold fields) | Yes |
| `app/modules/shop_runner/.../auto_shelf_bid_control_repository.py` | create/update settings/state | PG shelf tables | Yes |
| `app/modules/adv_creator/backend/main_manager.py` | create/update complex adv | PG `AdvSetting` | Yes |
| `app/client_bot/.../connect_existing_advs.py` | link campaigns | PG `AdvSetting` | Yes |
| `app/modules/relevant_phrase_manager/relevant_phrase_manager.py` | phrase lists | PG `AdvSetting` | Yes |
| `app/modules/shop_runner/service_manager/old_modules/setting_auto_updater/*` | `update_adv_setting`, target place / white list | PG `AdvSetting` | Yes (legacy automation) |
| `app/modules/shop_runner/.../setting_auto_updater_v2/.../target_place_*_executor.py` | SQL `update(AdvSetting)` | PG | Yes |
| `app/modules/common_slaves/wildberries/wb_db_manager.py` | `update_advs_in_db` | PG `AdvSetting` (WB-sourced: `active_status`, `nmids`, `cpm`, `wb_*` meta, name) | Yes — **WB sync authority for WB-fact columns**, not user policy |
| `app/modules/wb_adv_updater/data_manager.py` | `update_advs_data_from_wb_to_pg` | PG via `ShopDataUpdater` + Redis bid cache | Yes (sync path) |
| `app/modules/common_slaves/wildberries/shops_data_updater.py` | `ShopDataUpdater.update_advs_data` | PG + Redis auto-rec bid cache | Yes |
| `app/core/mp/wb/api/managers/wb_promotion_manager/wb_promotion_manager.py` | `WBModifier` (`pause_*`, `start_*`, `update_auto_adv_cpm`, `set_cluster_bids`, minus phrases) | WB API | Yes — physical campaign |
| `app/modules/shop_runner/.../auto_adv_active_control_service.py` | orchestrates `WBModifier` start/pause | WB API | Yes |
| `app/modules/common_slaves/wildberries/wb_api.py` / `api/api.py` | legacy CPM/pause helpers | WB API | Yes |
| `app/client_bot/user_interface/handlers/set_common_bid_manual.py` | `redis_bid_value.set_bids` | Redis (+ WB via other paths) | Yes for bids display/control plane |
| `app/modules/campaign_settings_history/collector.py` | `collect_cabinet` → `history.insert_snapshots` | CH `default_db.campaign_settings_history` | No for *current* settings (append-only history) |
| `app/modules/campaign_settings_history/clickhouse_repository.py` | `insert_snapshots`, `latest_hashes` | CH | History only |
| `app/modules/wb_adv_updater/keyword_cache_updater/main.py` | `update_to_cache` | Redis keywords UI cache | No for settings SoT |

**Production write authority (inventory inference):**

- **Current settings values:** PostgreSQL ORM rows (`AdvSetting`, `KeywordSetting`, `AutoShelfBidControlSettings`, `AdvTimeSettings`, `AdvTimeWeekMask`).
- **Field semantics / allowed projections:** `app/modules/campaign_settings_contract/registry.py` (not a runtime writer).
- **WB physical state:** `WBModifier` / promotion API (bids, pause/start, phrases) — orthogonal to PG policy columns.
- **ClickHouse:** derived snapshots only (`campaign_settings_history`).

---

## SNAPSHOT READERS (current value / canonical snapshot)

| Path | Symbol | What it loads |
|------|--------|----------------|
| `app/modules/campaign_settings_history/pg_reader.py` | `PostgresCampaignSettingsReader.load_cabinet` | Full aggregate → `CampaignSettingsRecord` / `CampaignSettingsSources` (history collector) |
| `app/modules/campaign_settings_contract/canonical.py` | `build_canonical_settings_snapshot` | Normalized `CanonicalSettingsSnapshot` from `CampaignSettingsSources` |
| `app/modules/ai_package_v1/readers/pg_campaign_settings_reader.py` | `PgCampaignSettingsReader.load_adv_settings` | `AdvSetting` rows per `shop_id` |
| `app/modules/ai_package_v1/export/campaign_settings_assembler.py` | assembler functions | `CampaignSettingsSnapshotV1` (export/read model) |
| `app/snapshot_data_updater/providers/postgres_provider.py` | (provider) | Shop-runner snapshot DTOs incl. `bot_active`, legs |
| Ubiquitous UI/services | `session.get(AdvSetting, id)`, `select(AdvSetting)...` | Ad-hoc per-handler reads |
| CH (historical, not current) | `ClickHouseCampaignSettingsHistoryRepository.latest_hashes` | Last `state_hash` per campaign |

Docstring on `pg_reader.py`: *«current settings remain PG authority»*.

---

## IDEMPOTENCY

| Mechanism | Location | Scope |
|-----------|----------|-------|
| `card_ab_hold_wb_sync_idempotency_key` + `build_wb_sync_idempotency_key` | `AdvSetting` column; `epoch_write.py`, `epoch_lifecycle.py` | A/B Hold WB intent only |
| `state_hash` compare before CH insert | `collector.collect_cabinet` | History dedup, not mutation replay |
| `snapshot_id` UUID per insert | `collector.py` | CH row identity |
| `ControlOutcome.IDEMPOTENT_HIT` | `app/db/control_acquire.py` | Control-plane acquire, not settings |
| WB top-up `idempotency_key` | `wb_auto_budget_topup` model | Budget top-up ledger |

**For generic campaign-settings mutations (Excel, Telegram, V3 applier):** no shared operation-id / ChangeSet dedup primitive found.

---

## DTO / SCHEMA (settings-shaped, not ChangeSet)

| Artifact | Path | Key fields / dimensions |
|----------|------|-------------------------|
| `CampaignSettingsSources` | `canonical.py` | `adv_setting`, `keyword_settings`, `auto_shelf_settings`, `adv_time_settings`, `adv_time_week_masks` |
| Canonical history payload | `canonical.py` `_build_canonical_snapshot` | `schema_version`, `identity` (`adv_setting_id`, `adv_id`, `search_adv_id`, `nmids`, …), `campaign`, `keywords`, `auto_shelf_by_nmid`, `schedule` |
| `CanonicalSettingsSnapshot` | `canonical.py` | `schema_version`, `payload`, `payload_json`, `state_hash` |
| `FieldPolicy` | `registry.py` | `name`, `semantic_role`, `history`, `excel`, `normalization`, `exclusion_reason`, `excel_alias` |
| `CampaignSettingsSnapshotV1` | `ai_package_v1/domain/campaign_settings_snapshot_v1.py` | `inventory` (`adv_setting_id`, `shop_id`, `adv_id`, `search_adv_id`, `nmids`, …), `auto_leg`, `search_leg` (`wb_adv_id`, `leg_role`), `local_policy`, `completeness` |
| `V3Action` | `auto_updater_v3/dto.py` (used by `applier.py`) | Automation actions on `KeywordSetting`, not a general settings patch |
| Excel row | `schema.py` | Column headers tied to registry; `parse_edit_value(field, raw)` |

**No** `ChangeSet`, `ChangeSetV1`, or JSON Schema for settings *patch* found in repo at this SHA.

---

## Campaign / leg identity (writers & DTOs)

| Concept | Field names |
|---------|-------------|
| Internal campaign PK | `adv_setting_id` / `AdvSetting.id` / `adv_setting_original_id` in callbacks |
| Auto leg WB advert | `adv_id` on `AdvSetting` |
| Search / auction leg WB advert | `search_adv_id` (registry metadata `_search_adv_id`; Excel RO `search_adv_id`) |
| Product grain | `nmids` (Excel RO `nmid` = first nmid); shelf settings keyed by `nmid` |
| Shop scope | `wb_cabinet_id`, `shop_id` (`WBCabinet.shop_id`) |
| Leg role (export DTO) | `CampaignLegRole.AUTO` / `SEARCH`; `auto_leg.wb_adv_id` vs `search_leg.wb_adv_id` |
| Budget / activity UI | `AdvType.AUTO` / `AdvType.SEARCH` + `use_common_budget` (`campaign_activity.py`) |
| Target run flags (PG, sparse writers) | `auto_adv_target_status`, `auction_adv_target_status` |

---

## TEST FILES (ChangeSetV1 validation+diff relevance)

| File | Scenario cluster |
|------|------------------|
| `tests/unit/test_campaign_settings_contract_registry.py` | Registry structure, excel/history policies |
| `tests/unit/test_campaign_settings_contract_canonical.py` | `build_canonical_snapshot`, normalization, hash stability |
| `tests/unit/test_campaign_settings_canonical.py` | `build_canonical_settings_snapshot`, errors, schema_version |
| `tests/unit/test_campaign_settings_excel_registry_parity.py` | Excel columns ↔ registry parity |
| `tests/unit/test_campaign_settings_excel_characterization.py` | Excel v8 editable/RO membership |
| `tests/unit/client_bot/test_adv_excel_roundtrip.py` | Deviation math, header parsing, `parse_edit_value` |
| `tests/unit/client_bot/test_adv_excel_roundtrip_pg_seam_handoff.py` | Import PG seam / handoff |
| `tests/unit/client_bot/test_adv_excel_ui_parity.py` | UI/export parity |
| `tests/integration/test_adv_excel_roundtrip_integration.py` | End-to-end excel roundtrip |
| `tests/unit/test_campaign_settings_history_*.py` (7 files) | PG reader, collector, CH repo, coordinator, updater, migration 006 |
| `tests/unit/test_adv_setting_defaults_policy.py` | Default/mode field policies on `AdvSetting` |
| `tests/unit/test_default_settings.py` | Default settings application |
| `tests/unit/test_main_adv_manager_apply_defaults.py` | Main adv manager defaults |
| `tests/unit/test_auto_updater_v3_applier.py` | V3 keyword `strategy_mode` / `hard_status` writes |
| `tests/unit/test_keyword_strategy_mode.py` | Keyword strategy mode semantics |
| `tests/unit/test_v3_status_mode_sync.py` | `hard_status` ↔ `strategy_mode` invariant |
| `tests/unit/test_v3_status_mode_backfill.py` | Backfill repair |
| `tests/unit/ai_package_v1/test_campaign_settings_*.py` | Export snapshot contract |
| `tests/unit/test_auto_shelf_bid_control_repository_writes.py` | Shelf settings PG writes |
| `tests/unit/client_bot/handlers/test_adv_setting_write_path_hardening.py` | TG write path guards |
| `tests/client_bot/user_interface/handlers/test_cpm_target_place_workbook.py` | Target-place excel |
| `tests/client_bot/user_interface/handlers/test_keyword_target_place_guard.py` | Target place guards |

---

## REUSE vs CREATE (contract-only ChangeSetV1 — inventory inference)

**Likely REUSE:**

- `campaign_settings_contract.registry` — field names, normalization policy, excel allowlists, semantic roles.
- `normalize_value` / `_normalize_field` / `build_canonical_settings_snapshot` — validation + canonical equality semantics for diff baseline.
- `CampaignSettingsSources` projection pattern from `PostgresCampaignSettingsReader._history_input_row`.
- Excel `parse_edit_value` + registry `allowed_values` — per-field parse rules (today tied to Excel types).
- Existing unit tests above as golden vectors for normalization and identity.

**Likely CREATE (not present at SHA):**

- A transport DTO for *proposed* mutations (`ChangeSetV1`: op list, actor, correlation id).
- Diff engine: canonical snapshot before/after or field-level patch against registry.
- Validation-only apply path (no writer invocation) — imports currently go straight to ORM `setattr` + `commit`.
- Generic mutation idempotency key / dedup store for settings writes.
- JSON Schema file for ChangeSet (registry is Python dataclass, not JSON Schema).

---

## Moves / creates

- Created: `/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/internal/campaign-settings-mutation-inventory.md`
- Created directory: `internal/` under project store (first file in that folder).
