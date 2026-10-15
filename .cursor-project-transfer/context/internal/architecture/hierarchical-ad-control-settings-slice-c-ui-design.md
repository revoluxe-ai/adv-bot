---
cursor:
  subagentId: "bc-1683885f-b8a1-59ed-ab57-13552c024279"
---

# hierarchical-ad-control-settings — Slice C (UI + diagnostics) design

**Status:** READ-ONLY design artifact (no code / no OpenSpec semantic edits).  
**Authority baseline:** Slice A on `origin/stage` (`065509c11`, PR #472).  
**Mutation contract:** Slice B PR #473 (`cursor/hierarchical-ad-control-settings-5b62`) — PG persistence + `AdControlChangeSetV1` dry-run.  
**Price boundary:** `PRICE_SEMANTICS_ACCEPTED = NO` (see `openspec/decisions/product-pricing-and-cpo-ownership/decision.md`).

---

## PAGE_STRUCTURE

Single owner-facing surface: **«Рекламный контроль»** (`Advertising Control`), one navigation entry per active `shop_id` (WB cabinet), not split across legacy `AdvSetting` screens.

| Zone | Purpose | Write policy |
|------|---------|--------------|
| **A. Shop policy** | All V1 features at SHOP scope; each feature independent (`ENABLED` / `DISABLED` + typed payload when enabled). | Configured mutations only via `AdControlChangeSetV1` → dry-run → (future) Apply. |
| **B. Campaign matrix** | Table keyed by `(shop_id, advert_id)`; per-feature mode `INHERIT` \| `OVERRIDE` \| `DISABLED`. | Per-row / per-cell actions only; no matrix-wide mutation shortcuts. |
| **C. Diagnostics** | Read-only inspector for shop and/or one campaign; same resolver semantics as runtime. | **No writes**; optional «dry-run diff» flag when a pending edit exists in zone A/B. |
| **D. Global banners** | Enrollment, control path, price semantics, stale measurement. | Informational. |

**Layout (implementation-neutral; Telegram accordion or web tabs):**

1. **Header:** `shop_id`, `HierarchicalEnrollment`, `ControlPathKind`, last refresh time.
2. **Zone A:** five feature cards (registry order from `FEATURE_REGISTRY`).
3. **Zone B:** filter bar + paginated summary table + row drill-down drawer.
4. **Zone C:** toggle «Режим диагностики» — when ON, edit controls in A/B are disabled; show `AdControlDiagnosticsReportV1` for selected scope (shop-only or shop+campaign).

**Default route:** Zone B list with shop policy collapsed link to Zone A. Campaign drill-down opens feature controls + inline diagnostics strip.

**Identity:** Campaign rows use **`advert_id`** as authority; display `main_nmid` / campaign title as **label only** (never as key).

---

## SHOP_SETTINGS_MODEL

**Domain source:** `ShopFeatureSlot` / `ConfiguredShopFeatureState`; persistence `AdControlShopFeatureRow` identity `(shop_id, feature_id, schema_version)`.

| UI field | Domain binding | Notes |
|----------|----------------|-------|
| Feature id | `AdControlFeatureId` | Fixed V1 set (5 features). |
| Activation | `ShopFeatureActivation` | `ENABLED` \| `DISABLED` only (no INHERIT at shop). |
| Payload | `ConfiguredFeaturePayload` via `payload_codec` | Shown/edited only when `ENABLED`. |
| Schema version | `FeatureDefinition.schema_version` | Read-only `1` in V1 UI. |
| Concurrency | `state_token` on row | From repository / snapshot; absent row → precondition token per Slice B dry-run (`acs_new` or equivalent absent-row convention). |

**Per-feature payload editors (bind to typed v1 structs, not free JSON):**

| Feature | Editor fields |
|---------|----------------|
| `DRR_POLICY` | `DrrProfile.target_drr_percent`, `max_drr_percent` (reuse product_control percent helpers). |
| `DYNAMIC_DRR_CONTROL` | `enabled`, `max_effective_delta_percent`. |
| `CPO_INCREASE_ON_HEADROOM` | `minimum_headroom_rub`, `maximum_increase_per_iteration_rub`, `cooldown_ticks`, `min_data_sufficiency`. |
| `CPO_DECREASE_ON_OVERSPEND` | `maximum_decrease_per_iteration_rub`, `cooldown_ticks`, `min_data_sufficiency`. |
| `CPO_SAFETY_BOUNDS` | Optional decimals: `absolute_min_cpo_rub`, `absolute_max_cpo_rub`, `max_step_up_rub`, `max_step_down_rub`. |

**Effective column (read-only):** For shop scope, effective === configured when enabled; when disabled, show inactive + `FEATURE_DISABLED_AT_SHOP`.

**Save:** One `shop.set_ad_control_feature` operation per feature save (or batch multiple features in one ChangeSet only when user explicitly saves a multi-feature shop form — still one shop, not bulk campaigns).

---

## CAMPAIGN_TABLE_MODEL

**Row key:** `(shop_id, advert_id)` — `CampaignRef`.

**Row source (read path):** Query campaigns for shop from existing PG campaign inventory (e.g. `AdvSetting` / cabinet linkage) **left join** `adcontrolcampaignfeaturerow` aggregates. Missing campaign rows imply default slots: all features `INHERIT`, no override payload.

**Columns (summary table):**

| Column | Content |
|--------|---------|
| `advert_id` | Primary key, sortable. |
| Display | Human name / SKU hint (non-authoritative). |
| `DRR_POLICY` mode chip | `INHERIT` \| `OVERRIDE` \| `DISABLED`. |
| Effective target DRR % | From `AdControlSettingsResolver.resolve_configured_target_drr` (or «—» if blocked). |
| Other features | Compact mode chips only (expand row for detail). |
| Control status | Aggregated: `OK` \| `BLOCKED` \| `NOT_ENROLLED` \| `LEGACY` from resolver + enrollment. |
| Diagnostics | Link/icon → Zone C prefilled for this campaign. |

**Filters:**

- Text: `advert_id` (exact/prefix).
- Per-feature mode multi-select (`INHERIT` / `OVERRIDE` / `DISABLED`).
- Status: blocked reason code bucket (enrollment, stale DRR, invalid config).
- Optional: «only overrides» / «only disabled at campaign».

**Pagination:** Server-side; default page size 25–50. Resolver runs per visible row (or batched service returning precomputed view models).

**Drill-down row panel:** `FEATURE_CONTROL_COMPONENT` for all five features; shows configured vs effective + provenance.

---

## FEATURE_CONTROL_COMPONENT

Reusable unit: **one `AdControlFeatureId` at one scope** (shop activation or campaign mode).

**States:**

1. **Shop:** toggle `ENABLED`/`DISABLED` + payload form when enabled.
2. **Campaign:** mode selector `INHERIT` \| `OVERRIDE` \| `DISABLED`.

**Read side (always visible):**

- `ResolvedFeaturePolicy`: `active`, payload summary, `provenance.source_kind`, `reason_codes`.
- For `DRR_POLICY`, highlight `ConfiguredTargetDrr` triple separation (configured target ≠ actual ≠ effective control DRR).

**Write side (campaign):**

| User action (RU) | Target mode | ChangeSet payload rule |
|------------------|-------------|-------------------------|
| **Переопределить** | `OVERRIDE` | `payload` = typed JSON from codec; **must not** include shop copy. |
| **Отключить** | `DISABLED` | `payload` omitted / `null`. |
| **Вернуть наследование** | `INHERIT` | `payload` omitted / `null` — **clear-to-inherit**; persistence rule: `non-OVERRIDE must not persist payload`. |

**Write side (shop):**

| Action | Activation | Payload |
|--------|------------|---------|
| Enable / edit | `ENABLED` | Required typed payload. |
| Disable | `DISABLED` | Must be null. |

**Validation:** Client-side mirrors `validate_shop_upsert` / `validate_campaign_upsert`; server truth = dry-run validator.

---

## INHERIT_OVERRIDE_DISABLED_UX

**INHERIT (campaign):**

- Show **effective** values from live resolver (shop + optional product tier for `DRR_POLICY`).
- Badge: «Наследует магазин» / «Наследует товар» (`SHOP_POLICY` vs product provenance).
- Do **not** display a persisted campaign payload editor; optional read-only «shop source» preview in collapsible section.
- Copy: changing shop policy affects this campaign immediately without campaign row update.

**OVERRIDE:**

- Full payload editor; effective === override values until mode changes.
- Switching shop policy does **not** change effective values.

**DISABLED:**

- Feature treated inactive at campaign; reason `FEATURE_DISABLED_AT_CAMPAIGN`.
- Effective payload hidden; CTA: «Вернуть наследование» or «Переопределить».

**Confirmations:**

- `OVERRIDE` → `INHERIT`: confirm «Значения магазина будут применяться автоматически; сохранённые переопределение будет удалено».
- `ENABLED` shop → `DISABLED`: warn campaigns in `INHERIT` lose effective feature.

**Anti-pattern (forbidden UX):** «Copy shop settings to campaign» button — violates live inheritance decision.

---

## DIAGNOSTICS_MODEL

**Contract:** `AdControlDiagnosticsReportV1` built by `AdControlDiagnosticsBuilder.build` with same `ResolverContext` as edit screens.

**Inputs (application layer must assemble):**

| Input | Source |
|-------|--------|
| `ResolverContext` | Repository loads + enrollment/path flags + optional `ProductDrrPolicyAdapter` for campaign `main_nmid`. |
| `actual_drr` | Port TBD (`ActualDrrObservation`); may be null → sufficiency `UNKNOWN`. |
| `current_max_cpo_rub` | Legacy/read port for display only. |
| `allowed_spend_rub`, `spend_rub` | Headroom ports TBD. |
| `dry_run_diff_available` | `true` when a validated pending ChangeSet exists for this scope. |

**UI sections mirroring report:**

1. Configured shop features (`configured_shop_features`).
2. Configured campaign overrides (`configured_campaign_overrides`) — payload only if `OVERRIDE`.
3. Effective features list + provenance index.
4. DRR triple: configured target, actual, shop/campaign effective control DRR.
5. Headroom block (`shop_headroom`, eligibility blockers).
6. CPO block: `current_max_cpo_rub`; **`proposed_cpo.proposed_max_cpo_rub` always withheld** under price semantics.
7. `decision`, `reason_codes`, `blockers`.

**Diagnostic mode:** Global toggle forces read-only; refreshes report on demand; no Apply.

**Shop-wide diagnostics:** `campaign=None` in builder if supported by application API; else iterate campaigns as read-only batch (see bulk rules).

---

## DRY_RUN_UX

**Pipeline (Slice B contract, no PG/WB writes in validator):**

1. User commits edit in Zone A or B → UI builds `AdControlChangeSetV1`:
   - `scope`: `AdControlLogicalScopeV1(shop_id=…)`.
   - `operations`: `shop.set_ad_control_feature` or `campaign.set_ad_control_feature` with `AdControlPreconditionV1(state_token)`.
2. Application loads snapshots:
   - `AdControlShopFeatureSnapshotV1` map keyed `(feature_id, schema_version)`.
   - `AdControlCampaignFeatureSnapshotV1` keyed `(shop_id, advert_id, feature_id, schema_version)`.
3. Call `validate_ad_control_changeset` → `AdControlValidationResult`.

**Result presentation:**

| `DryRunStatus` | UX |
|----------------|-----|
| `OK` | Green «Изменения готовы»; show `semantic_digest`; list `AdControlSemanticDiffV1` rows (`activation` / `mode` / `payload` previews). |
| `NO_OP` | Neutral «Без изменений»; disable Apply. |
| `REJECTED` | Red; list `ControlPlaneError` (`code`, `message`, `operation_index`). |

**Stale token:** `STATE_TOKEN_STALE` → prompt «Обновите страницу» and reload snapshots.

**Apply button:** **Hidden or disabled in Slice C** until Apply Authority wires ad-control writer (post–Slice B). Label when enabled: «Применить» with Owner GO / receipt flow (out of Slice C scope).

**Idempotency display:** Show `changeset_id` + `semantic_digest` (`acs1_…`) for support logs.

---

## BLOCKER_REASON_UX

Map `AdControlReasonCode` / `ControlPlaneError.code` to owner-facing RU strings + severity.

| Code / bucket | Severity | User message (distilled) | UI treatment |
|---------------|----------|---------------------------|--------------|
| `NOT_ENROLLED_FAIL_CLOSED` | Block | Иерархический контроль не подключён для магазина. | Zone A/B edits disabled; legacy CPO screens unchanged. |
| `LEGACY_PASSTHROUGH_ACTIVE` | Info | Кампания на legacy-пути; иерархия не применяется. | Show legacy badge; hierarchical controls hidden or read-only. |
| `FEATURE_DISABLED_AT_*` | Warn | Функция отключена на {уровне}. | Chip + tooltip. |
| `SHOP_ENABLED_MISSING_PAYLOAD` | Error | Магазин: включено без параметров. | Block save; link to shop card. |
| `INVALID_CONFIGURATION` | Error | Некорректная конфигурация. | Inline field errors. |
| `ACTUAL_DRR_STALE` / `INSUFFICIENT` / `UNSUPPORTED` | Warn | Фактический DRR недоступен / устарел. | Diagnostics banner; «без новых control action». |
| `NO_CONTROL_ACTION_STALE_OR_UNKNOWN` | Warn | Автоматические действия заблокированы (данные). | No actuation CTAs. |
| `HEADROOM_ALLOCATOR_NOT_ACCEPTED` | Info | Алгоритм распределения headroom не утверждён. | No allocation UI. |
| `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED` | Block | CPO из DRR недоступен (семантика цены не принята). | Show **NOT_AVAILABLE** / **BLOCKED**; never numeric recommendation. |
| `PRODUCT_DRR_ADAPTER_BLOCKED` | Warn | Товарный уровень DRR недоступен; используется магазин. | Tooltip on inherit chain. |
| `STATE_TOKEN_STALE` | Error | Данные изменились в другой сессии. | Refresh snapshots. |

**`blockers` tuple:** Show technical id in diagnostics «для поддержки» section only.

---

## BULK_OPERATIONS_ALLOWED

| Operation | Scope | Notes |
|-----------|-------|-------|
| Filter / search campaigns | Read | No mutation. |
| Export diagnostics summary (CSV/JSON) | Read | Resolver output only; no secrets. |
| Paginated «diagnostics scan» | Read | Batch **read** of `AdControlDiagnosticsReportV1` for visible page; rate-limited. |
| Multi-feature shop save | Write | Single ChangeSet, multiple `shop.set_*` ops, **one shop** — user-initiated explicit save. |
| Multi-feature single-campaign save | Write | Multiple `campaign.set_*` for **one** `advert_id` in one ChangeSet. |

---

## BULK_OPERATIONS_FORBIDDEN

| Operation | Rationale |
|-----------|-----------|
| Multi-campaign mode/payload apply (select all → inherit/override/disable). | Unsafe; violates per-campaign authority and concurrency. |
| «Copy shop to all campaigns». | Forbidden by architecture (copy-on-inherit). |
| Cross-shop ChangeSet. | `scope.shop_id` is singular. |
| Bulk clear inheritance across table. | Same as multi-campaign inherit. |
| Excel import of hierarchical modes. | Out of scope; separate change. |
| Any WB / `AdvSetting` CPO write from this UI. | Hierarchical configured plane only; legacy fields separate. |
| Showing computed `proposed_max_cpo_rub` as recommendation. | `PRICE_SEMANTICS_ACCEPTED = NO`. |

---

## CANONICAL_DOMAIN_BINDINGS

| UI concern | Canonical module / type |
|------------|-------------------------|
| Feature list & validation | `app/modules/ad_control_settings/domain/registry.py` — `FEATURE_REGISTRY`, `validate_feature_payload` |
| Effective policy | `AdControlSettingsResolver` |
| Configured projection | `project_configured_shop_features`, `project_configured_campaign_features` |
| Diagnostics | `AdControlDiagnosticsBuilder` → `AdControlDiagnosticsReportV1` |
| Reason codes | `AdControlReasonCode` |
| Campaign key | `CampaignRef(shop_id, advert_id)` |
| Modes / activation | `AdControlFeatureMode`, `ShopFeatureActivation`, `HierarchicalEnrollment`, `ControlPathKind` |
| DRR profile editing | `app/modules/product_control/domain` — `DrrProfile` / `drr_profile_from_percent` |
| Persistence read/write intents | `AdControlSettingsRepository`, `ShopFeatureUpsert`, `CampaignFeatureUpsert` |
| JSON boundary | `payload_codec.encode_payload_json` / `decode_payload_json` |
| Mutation transport | `wb_sky_control_plane.models.ad_control_changeset.AdControlChangeSetV1` |
| Dry-run | `wb_sky_control_plane.kernel.ad_control_validate.validate_ad_control_changeset` |

**Layering:** UI handlers (e.g. Telegram under `app/modules/ad_control_settings/telegram/` or cabinet module) → thin **application service** `AdControlSettingsUiService` (to be added in implementation) → domain + persistence + control plane validator. No resolver logic in handlers.

---

## SLICE_B_DEPENDENCIES

| Dependency | PR #473 deliverable | Slice C need |
|------------|---------------------|--------------|
| PG tables + Alembic | `adcontrolshopfeaturerow`, `adcontrolcampaignfeaturerow` | Load/save configured state |
| Repository | `load_shop_slots`, `load_campaign_slots`, `get_*_row`, `state_token` | Snapshots + edit forms |
| Payload codec | Round-trip typed payloads | Forms |
| ChangeSet model | `AdControlChangeSetV1`, ops `shop.set_ad_control_feature`, `campaign.set_ad_control_feature` | Mutation intent |
| Validator | `validate_ad_control_changeset`, snapshots, `DryRunStatus` | Dry-run UX |

**Not in Slice B (explicit gaps for implementation scheduling):**

- Apply Authority execution for ad-control ops (PG commit + receipt).
- HTTP/MCP/Telegram transport wiring.
- Campaign list query optimization at scale.

**Contract alignment:** Campaign `INHERIT` / `DISABLED` mutations must send `payload: null`; validator + `validate_campaign_upsert` enforce clear-to-inherit. **No contract conflict detected.**

---

## PRICE_SEMANTICS_DEPENDENCIES

- Global flag: `PRICE_SEMANTICS_ACCEPTED = NO` (`product-pricing-and-cpo-ownership` ADR).
- Diagnostics: `BoundedCpoProposal.proposed_max_cpo_rub` is `None`; `decision` includes `NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED`.
- UI must render CPO proposal area as **NOT_AVAILABLE** or **BLOCKED** with code `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`.
- Allowed: show `current_max_cpo_rub` if supplied from legacy read path (informational).
- Forbidden: DRR→CPO calculator, «recommended max CPO», headroom→CPO actuation preview with rub values.
- Future: when Owner sets `PRICE_SEMANTICS_ACCEPTED = YES`, UI unblocks proposal display in a **separate change** (not Slice C).

Evidence cross-ref: `/cursor/stores/self/internal/drr-cpo-price-semantics/evidence-report.md`.

---

## OWNER_DECISIONS_REQUIRED

| # | Decision | Blocks |
|---|----------|--------|
| O1 | **UI transport** for V1 (Telegram bot vs web admin vs both). | Handler placement only. |
| O2 | **Who may set `HierarchicalEnrollment.ENROLLED`** and `ControlPathKind.HIERARCHICAL` (ops flag / PG / env). | Edit gating in Zone A/B. |
| O3 | **Apply GO** for ad-control ChangeSet execution (Apply Authority slice). | Persist button. |
| O4 | **Campaign inventory query** (which campaigns appear in matrix; archived/excluded rules). | Table completeness. |
| O5 | **`ActualDrrObservation` port** for diagnostics (source, window, attribution basis). | Headroom / stale banners accuracy. |
| O6 | **Product tier** in UI for `DRR_POLICY` inherit chain (`ProductDrrPolicyAdapter` inputs). | Campaign inherit display when product override exists. |
| O7 | **Headroom allocator** acceptance (still protocol-only in domain). | Any «suggested allocation» UI. |

Design proceeds with placeholders for O1–O6; O3 required before production writes.

---

## IMPLEMENTATION_SLICES

| Slice | Deliverable | Depends on |
|-------|-------------|------------|
| **C1** | Application read service: load context, resolver view models, diagnostics builder wiring | Slice B merged |
| **C2** | Zone A shop UI + dry-run preview (no Apply) | C1 |
| **C3** | Zone B campaign table + filters + row drill-down | C1 |
| **C4** | Zone C diagnostic mode + reason/blocker UX | C1 |
| **C5** | Apply Authority hookup + «Применить» + receipt display | Owner O3 + apply slice |
| **C6** | Measurement ports for actual DRR / spend (diagnostics richness) | Owner O5 |

**Testing:** Unit tests on view-model mappers; integration tests with repository fakes + `validate_ad_control_changeset`; UI smoke manual per transport.

---

## FINAL_STATUS

**SLICE_C_DESIGN_READY**

Slice B contracts are sufficient to bind UI, dry-run, and clear-to-inherit mutations. Implementation of persist remains gated on Apply Authority (post–B). No OpenSpec semantic conflicts identified; report-only if B changes discriminator or payload rules before merge.
