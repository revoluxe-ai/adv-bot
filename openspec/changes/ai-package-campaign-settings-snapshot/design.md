# Design — ai-package-campaign-settings-snapshot

## Architecture Decision References

| Decision | Role in this change |
|---|---|
| `openspec/decisions/shop-data-source-strategy/decision.md` (Accepted) | PG/CH accumulation read path; collection vs management; grain/Auto-Search; four completeness dimensions |
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` (Accepted) | Export lives in `app/modules/ai_package_v1/`; READ_ONLY_NO_MUTATION; forbidden WBShopDataManager/snapshot_updater scope |
| `openspec/decisions/mode-defaults-policy-ownership/decision.md` (Accepted) | Export MUST NOT assign mode defaults or bot transitions |
| Proposed: `decisions/ai-package-campaign-settings-snapshot-ownership/decision.md` | Seam: AI export snapshot vs A1 vs Redis DTO; allowed primitive reuse |

Canonical specs consumed (not modified in this planning hop):
`openspec/specs/data-source-selection`, `grain-preservation`, `coverage-provenance`,
`collection-modes`, `ai-package-v1-exporter`, `ai-package-v1-contract-tests`.

## Ownership & Placement

| Concern | Owner | Layer | Notes |
|---|---|---|---|
| AI Package detailed settings contract | This change (`ai-package-campaign-settings-snapshot` spec) | Domain under `app/modules/ai_package_v1/` | `CampaignSettingsSnapshotV1` DTO + assembler |
| Manifest card `campaign_settings_snapshot` | AI Package v1 exporter (modified requirement) | `ai_package_v1/export/` | Transport-agnostic payload reference in manifest |
| A1 authoritative WB snapshot | `wb_sky_control_plane` | Control plane read/apply | **Not** AI export contract |
| Redis shop-runner tick snapshot | `snapshot_data_updater` | Operational cache | **Not** AI export contract |
| WB promotion v2 raw read | Collectors / A1 `WbPromotionV2ReadPort` | Out of export path | Export reads **accumulated** PG sync columns only in slice 1 |
| PG scope query | `PgExportShopScopeReader` pattern | `ai_package_v1/scope/` | `only_bot_active=False`; no `WBShopDataManager` |

Checklist:

- [x] Context-first decision lookup performed (shop-data-source-strategy, ai-package-v1-exporter-ownership, mode-defaults).
- [x] Relevant decisions cited by path.
- [x] New decision proposed for snapshot ownership seam (registry gap).
- [x] Implementation layer matches decision (ai_package_v1 read assembler; no control-plane ownership).

## Seam resolution — three representations

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ AI Package export card: campaign_settings_snapshot                       │
│ Contract: CampaignSettingsSnapshotV1                                     │
│ Grain: shop_id + adv_setting_id (PG anchor) + explicit auto/search legs  │
│ Purpose: machine-readable settings for AI/analytics consumers            │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ MUST NOT alias
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌───────────────────────────┐               ┌───────────────────────────────┐
│ CampaignResourceSnapshotV1│               │ AdvSettingsSnapshotDTO        │
│ Owner: wb_sky_control_plane│               │ Owner: snapshot_data_updater  │
│ Key: cmp_* resource_id    │               │ Key: adv_id tick slice        │
│ Scope: ChangeSet apply    │               │ Scope: bot_active shop-runner │
│ WB live read on apply path│               │ Redis adv_snapshot:v1         │
└───────────────────────────┘               └───────────────────────────────┘
```

**Mapping metadata (optional, not primary grain):** export row MAY include
`a1_resource_id` when registry row exists, as cross-reference only. Export MUST NOT
require A1 registry completeness for shop-scoped snapshot.

## Dataset grain and identity

| Dimension | Value |
|---|---|
| Primary grain | `(shop_id, adv_setting_id)` — PostgreSQL `AdvSetting.id` |
| WB leg identity | Separate nested `auto_leg` / `search_leg` objects; each carries `wb_adv_id`, `leg_role` (`AUTO` \| `SEARCH`) |
| Pair link | Logical link via `AdvSetting.adv_id` (auto anchor) + `AdvSetting.search_adv_id`; stored **outside** stat rows per grain-preservation |
| Export row count | One record per in-scope `AdvSetting` inventory row (ComplexAdv anchor), not merged Auto+Search into one leg |
| Period | Point-in-time snapshot at export assembly; not daily time series (unlike `full_adv_wb_stat`) |
| Shop scope | `WBCabinet.shop_id == shop_id`; cross-shop rows forbidden |

**Forbidden identity shortcuts:**

- Using `cmp_*` as export primary key without `adv_setting_id` anchor.
- Collapsing Auto+Search into single `campaign_id` row.
- Treating Redis snapshot batch `collected_at` as AI Package manifest freshness for PG fields without explicit provenance.

## Field / source authority matrix

Authority classes (every exported field MUST declare `authority_class` in provenance):

| Class | Meaning | Conflict rule |
|---|---|---|
| `WB_AUTHORITATIVE` | Value reflects WB cabinet state | Wins over local projection for WB-owned semantics |
| `LOCAL_POLICY` | Bot/AdvSetting policy not written to WB on read path | Wins over inferred WB defaults; MUST NOT mask missing WB field |
| `INVENTORY_RELATION` | Identifiers and linkage only | Does not imply settings completeness |
| `UNSUPPORTED` | Known field slot; no safe reader in slice | Value MUST be absent; `reason_codes` include `UNSUPPORTED_FIELD` |
| `UNKNOWN` | Source read failed or semantics unresolved | Fail-closed; no fabricated default |

### Matrix — evidence from repository (planning)

| Field group | Representative fields | Primary source (export slice 1) | Reuse primitive | NOT contract |
|---|---|---|---|---|
| Inventory ids | `adv_setting_id`, `shop_id`, `adv_id`, `search_adv_id`, `name`, `active_status` | PG `AdvSetting` + `WBCabinet` join (`PgExportShopScopeReader` pattern) | Join/filter from v1 design | `AdvSettingsSnapshotDTO` |
| Product scope | `nmids`, main nmid | PG `AdvSetting.nmids` | — | A1 `product_nm_ids` merge |
| WB bid/placement sync | `wb_bid_type`, `wb_placement_search`, `wb_placement_recommendations` | PG columns (synced by shop cycle / `apply_wb_campaign_meta_from_legacy_adv_data`) | Column semantics from model comments | Generated `GetAdvertsAdvertsItem` defaults |
| WB leg status/placements (detailed) | status, payment_type, placements, nm_settings membership | **OPEN** — PG sync partial; live normalization in A1 `normalize_wb_campaign_leg` | MAY extract shared normalizer **after** A1 lands; slice 1 = PG columns + `UNKNOWN` | `CampaignResourceSnapshotV1` wholesale |
| Local management flags | `bot_active`, `bidder_active`, `parsing_active` | PG `AdvSetting` | — | Redis DTO defaults (`bot_active=True`) |
| Budget policy | `auto_budget_*`, `common_budget_*`, `use_common_budget` | PG `AdvSetting` | Field list from `project_local_policy_from_adv_setting` budget dict | Control-plane apply |
| Sales / plan policy | `plan_for_sales_for_day`, `target_price_for_order`, `max_price_for_order`, `strategy`, `orders_source_for_auto_mode` | PG `AdvSetting` | `project_local_policy_from_adv_setting` sales dict | — |
| Bid control policy | `auto_shelf_bid_control_*`, `bidder_for_auto`, `max_cpm`, `bidder_step` | PG `AdvSetting` | local_policy bid_control subset + additional PG columns | — |
| Keyword / phrase policy | `black_phrases`, `relevant_phrases`, `auto_update_minus_phrases`, `auto_update_white_list` | PG JSONB columns | — | Redis keywords section |
| Mode / updater legacy | `automatic_version`, `bidder_coroutine_type`, `type` | PG (export as INVENTORY or LOCAL with `UNSUPPORTED` semantics where legacy) | Mark `type` 8/9 as **not** leg definition | — |
| Pair topology classification | topology, payment_type aggregate | **OPEN** — A1 `classify_snapshot` not on export path slice 1 | Optional slice 2 after shared kernel extract | A1 classification as export requirement |

**Scope filter (export):** align with v1 inventory — `active_status != 'done'`,
`only_bot_active=False` (all shop inventory rows, not snapshot_updater
`bot_active.is_(True)` filter).

**Explicit non-reuse:**

- `AdvSettingsSnapshotDTO` — slim tick DTO; wrong scope filter; MUST NOT become
  export schema.
- `CampaignResourceSnapshotV1` — cmp-scoped apply snapshot; MUST NOT be serialized
  as AI Package payload.
- `AdvDataSnapshotDTO` — includes keywords/min_bids/plan_fact; different consumer;
  MAY share PG load list only.

## Timestamp, freshness, completeness, provenance

| Metadata | Semantics |
|---|---|
| `snapshot_assembled_at` | UTC timestamp when export assembler finished PG read for shop (manifest + payload) |
| `source_observed_at` | Per authority class: e.g. PG row `AdvSetting.last_update` for LOCAL_POLICY freshness signal |
| `freshness` | Independent dimension: stale PG sync vs assembly time; MUST NOT imply full WB cabinet coverage |
| `coverage` | Entity coverage = in-scope inventory rows exported vs shop scope query; NOT full WB universe |
| `collection_outcome` | Export read attempt result (PG session success/failure) |
| `reason_codes` | e.g. `NO_DATA`, `UNKNOWN`, `PARTIAL_PG_WB_SYNC`, `UNSUPPORTED_FIELD`, `A1_REGISTRY_GAP` (non-blocking) |
| `field_provenance[]` | `{ field_path, authority_class, source_ref, observed_at?, reason_codes? }` |

**Fail-closed:** If `authority_class=UNKNOWN` for a field required by consumer
mutation eligibility heuristics, consumer MUST treat mutation as disallowed (export
does not perform mutations).

**No fabricated defaults:** Nullable PG `None` exports as JSON `null` with
provenance; MUST NOT coerce to generated-client enum defaults or `bot_active=True`
(Redis DTO anti-pattern).

## Exposure as AI Package dataset (transport decoupling)

1. Domain payload: JSON document `CampaignSettingsSnapshotV1` with
   `schema_version`, `shop_id`, `records[]`, package-level completeness block.
2. Manifest card (existing id): `campaign_settings_snapshot` references payload
   file name + `sha256`; card metadata carries four dimensions per dataset.
3. ZIP is transport only; validator applies to domain JSON + manifest (per v1
   exporter spec).
4. Card MUST declare `detailed_settings_export: true` when this change applied;
   v1 minimal inventory used `detailed_settings_export: false`.

## Semantic Write Target (read-path MEANING_LOCK)

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
TARGET_ENTITY_OR_LEG: AI_PACKAGE_READ_EXPORT — campaign_settings_snapshot detailed payload
ALLOWED_ADAPTERS:
  - PG: get_async_session_maker(read_only=True) + AdvSetting/WBCabinet join (inventory scope)
  - PG: AdvSetting column projection into CampaignSettingsSnapshotV1 (LOCAL_POLICY, INVENTORY_RELATION, partial WB_AUTHORITATIVE)
  - Shared extract (optional slice 2): read-only normalizer functions copied/extracted to ai_package_v1/read/ with tests — not importing control-plane apply
FORBIDDEN_ADAPTERS:
  - WB HTTP on export path (CampaignsInfoV2Adapter, collectors)
  - WBShopDataManager, snapshot_data_updater Redis read as SoT for export contract
  - CampaignResourceSnapshotV1 serialize-through as AI payload
  - bot_active-only postgres_provider filter as export scope
  - Control-plane apply, registry writes, mode defaults transitions
EVIDENCE:
  - openspec/decisions/shop-data-source-strategy/decision.md
  - openspec/decisions/ai-package-v1-exporter-ownership/decision.md
  - app/modules/common_slaves/wildberries/models/models.py (AdvSetting)
  - app/modules/wb_sky_control_plane/read/local_policy.py
  - app/snapshot_data_updater/dto.py (anti-pattern reference)
  - app/modules/wb_sky_control_plane/models/snapshot.py (non-contract reference)
OWNER_DECISION_SOURCE: owner-contract.md (D-001..D-003)
PAIRED_TESTS: specs/ai-package-campaign-settings-snapshot/spec.md +
  delta ai-package-v1-contract-tests
```

## Derived Lifecycle (export read)

| Step | Action |
|---|---|
| L1 | Validate export inputs (`shop_id`, period bounds) — settings snapshot is point-in-time; period bounds gate shop scope only |
| L2 | Load inventory via read-only PG scope (all non-done adv rows for shop) |
| L3 | For each `AdvSetting`, project legs (auto anchor + optional search_adv_id) |
| L4 | Map PG columns to field groups with authority_class + provenance |
| L5 | Mark OPEN/unmapped WB fields UNKNOWN or UNSUPPORTED — no live WB fetch |
| L6 | Attach snapshot_assembled_at, four completeness dimensions per card |
| L7 | Emit domain JSON; manifest card references payload; no transport logic in domain model |

## Module layout (proposed — apply implements)

```
app/modules/ai_package_v1/
  domain/campaign_settings_snapshot_v1.py   # contract DTO + enums
  scope/pg_export_shop_scope_reader.py      # existing/planned — reuse
  readers/pg_campaign_settings_reader.py    # NEW — detailed projection
  export/campaign_settings_assembler.py     # NEW — builds payload + provenance
tests/unit/ai_package_v1/
  test_campaign_settings_snapshot_*.py
```

## A1 overlap and sequencing

| Slice | Dependency | Notes |
|---|---|---|
| Slice 1 (isolated) | ai-package-v1 exporter scaffold landed | PG-only projection; OPEN WB fields explicit |
| Slice 2 (optional) | A1 normalizer stable + shared extract ADR | Reuse `normalize_wb_campaign_leg` semantics without control-plane import on export default path |
| Slice 3 | Contract test expansion | Manifest + validator + golden fixtures |

Dirty A1 worktree MUST NOT block slice 1 if implementer avoids importing
`wb_sky_control_plane` apply/resolver modules.

## OPEN items (bounded follow-up in tasks)

| Id | Topic | Planning disposition |
|---|---|---|
| OPEN-01 | Full WB authoritative leg fields beyond PG sync columns | Slice 1: UNKNOWN/PARTIAL; accumulation or shared normalizer in slice 2 |
| OPEN-02 | Exact allowlist of LOCAL_POLICY fields for v1 detailed export | tasks §1.2 discovery gate before FULL local coverage claim |
| OPEN-03 | `a1_resource_id` cross-ref population | Optional metadata when registry row exists; never required for export success |
| OPEN-04 | Keyword-level settings in settings snapshot | Out of scope — belongs to keywords dataset / Redis snapshot, not this card |

## Non-goals

- Mutations, control-plane apply, campaign create/lifecycle, budget/bid writes.
- Live WB API on export path; collector triggers from ZIP build.
- Redis snapshot_data_updater changes; using Redis as settings SoT.
- Transport/API/MCP endpoints; Telegram/GUI.
- Canonical spec promotion; global decision/index edits; §0.3 openspec_guard debt.
- Promoting proposed ownership ADR to Accepted registry in this change.

## Product Acceptance (planning)

```text
PRODUCT_ACCEPTANCE_REQUIRED: true
PRODUCT_ACCEPTANCE_STATUS: BLOCKED (pre-apply)
NORMATIVE_MODALITY_PRESERVED: yes
DESIGN_STATUS: READY
TECHNICAL_DESIGN_UNRESOLVED: OPEN-01..OPEN-04 documented; slice 1 bounded
```
