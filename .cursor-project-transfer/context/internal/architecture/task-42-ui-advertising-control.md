---
cursor:
  subagentId: "bc-67d4fbe8-cec9-58ce-8d2e-648423dff71f"
---

# Task 4.2 — UI Advertising Control + Diagnostics (architecture packet)

READ-ONLY. No code, no OpenSpec, no PR.
Baseline: `a2e8453e773411eab989b08fa1358f2195c2dee4` (`stage` = `origin/stage`, merge PR #473).
Parent change: `openspec/changes/hierarchical-ad-control-settings`.
Tasks: `tasks.md` 4.1 and 4.2 are unchecked one-liners. 4.1 is an independent stream and is not in this tree (`app/modules/shop_runner` has no `ad_control` wiring).

Supersedes the stale Slice C note `internal/architecture/hierarchical-ad-control-settings-slice-c-ui-design.md` on price semantics (`PRICE_SEMANTICS_ACCEPTED = NO` there). Accepted ADR `openspec/decisions/drr-cpo-price-semantics/decision.md` is `PRICE_SEMANTICS_ACCEPTED = YES` with `PRICE_SEMANTICS_QUALIFIER = V1_ORDER_VALUE_BASIS`. The domain builder has not caught up (see BLOCKERS).

Archaeology (Composer 2.5, read-only):

- `internal/wb-sky-task-4-2-ui-archaeology-a.md`
- `internal/architecture/hierarchical-ad-control-slice-ab-type-map-bc-ab9bf4d3.md`
- `internal/hierarchical-ad-control/runtime-economic-facts-archaeology-c.md`
- `internal/hierarchical-ad-control/campaign-list-scale-ux-archaeology-d.md`

## START_STAGE

`a2e8453e773411eab989b08fa1358f2195c2dee4`

## EXISTING_UI_STACK

Product control surface is **Telegram (aiogram 3)**, not a web admin.

| Surface | Path | Role |
|---|---|---|
| Bot routers / FSM | `app/client_bot/` | Settings, campaign lists, V3 menus |
| Webhook only | `client_bot_run.py` FastAPI `/health` `/ready` | Not a settings UI |
| V3 campaign menu | `app/client_bot/user_interface/views/messages/main_adv_setting_menu/` (`AdvSettingMenu`) | Plan/fact, activity, last V3 action |
| Campaign list | `ChoiceAdvPaginator` → `AdvCompanyChoicing` → `get_advs_keyboard_with_paginator` | Page size 20, in-memory offset after full PG load |
| Shop menu | `app/modules/shop_menu/message.py` (`ShopMenu`) | Cabinet settings, not ad-control |
| Domain diagnostics | `AdControlDiagnosticsBuilder` → `AdControlDiagnosticsReportV1` | **No UI handler.** Tests only |
| Ad-control Apply | none | `validate_ad_control_changeset` is dry-run only |

Zero Jinja/Vue/HTML product templates. Do not invent an HTTP settings app in 4.2.

## REUSABLE_UI_PATTERNS

| Pattern | Reuse | Do not reuse |
|---|---|---|
| Shop entry | `ShopMenu` navigation + cabinet ownership `load_wb_user_cabinet_for_adv_in_session` / `load_adv_for_owner_cabinet_in_session` | Writing `WBCabinet` / `WBUserCabinet` as ad-control persistence |
| List chrome | Telegram page size **20**, `advert_id` as row key | Full-cabinet `AdvSetting` load + per-row Redis `check_last_24_hours` |
| Submenu forms | V3 calibration / sales-plan telegram handlers (one feature, typed fields, FSM) | Excel roundtrip `apply_adv_excel_rows` |
| Status text | `format_v3_tick_report_text`, keyword V3 diagnostic blocks (read-only text) | Treating V3 tick text as hierarchical DRR |
| Auth | Cabinet ownership; `is_bot_admin` / `IsBotAdminFilter` for admin-only traces; `UiAccessResolver`; read-only WB token gate; `is_ab_hold_structural_freeze`; middleware `gate.py`, `phone_required.py`, `channel_subscription.py` | `CampaignCapabilitiesV1` — that is AdvSetting ChangeSet, not ad control |
| Validation errors | Control-plane `ControlPlaneError.code` (`REVISION_CONFLICT`, …) rendered as text | Client-only validation as source of truth |

**REUSABILITY of Advertising Control itself: LOW.** Backend domain is ready for configured policy; UI module does not exist (`app/client_bot` has no `ad_control` usage).

## Canonical UX

Section name: **Advertising Control** (RU: «Рекламный контроль»), one entry per `shop_id` (WB cabinet).

Zones:

1. **Shop panel** — five features from `FEATURE_REGISTRY` (`AdControlFeatureId`): `DRR_POLICY`, `DYNAMIC_DRR_CONTROL`, `CPO_INCREASE_ON_HEADROOM`, `CPO_DECREASE_ON_OVERSPEND`, `CPO_SAFETY_BOUNDS`. Shop activation is `ShopFeatureActivation` `ENABLED` | `DISABLED` only. No shop INHERIT.
2. **Campaign table** — row identity `(shop_id, advert_id)` = `CampaignRef`. Per feature: `AdControlFeatureMode` `INHERIT` | `OVERRIDE` | `DISABLED`.
3. **Diagnostics / Test** — read-only. Same `AdControlSettingsResolver` + `AdControlDiagnosticsBuilder` + `headroom_eval` as production. Edit controls disabled while diagnostics mode is on.

Visible separation (never collapse these columns):

| Kind | Symbol | Editable |
|---|---|---|
| Configured | `ConfiguredShopFeatureState` / `ConfiguredCampaignFeatureState` | Future intent only |
| Effective configured policy | `ResolvedFeaturePolicy` | No |
| Provenance | `ProvenanceEntry.source_kind` (`EffectiveSourceKind`) | No |
| Observed | `ActualDrrObservation` | **Never** |
| Derived | `ShopEffectiveControlDrr`, `CampaignEffectiveControlDrr`, `ShopHeadroomState`, `BoundedCpoProposal` | **Never** |
| Blocked | `ResolverBlocked` or report `decision == "BLOCKED"` | No |

`main_nmid` / campaign title are labels only. Authority is `advert_id`.

## SHOP_UI_READ_MODEL

UI binds fields. It does not compute them.

| UI field | Source | Path | Fail-closed |
|---|---|---|---|
| configured target DRR | `ConfiguredTargetDrr.target_drr_percent` (+ `max_drr_percent`) | `AdControlDiagnosticsReportV1.configured_target_drr` | `None` + `ResolverBlocked` reasons; do not show a number |
| effective target DRR | `ShopEffectiveControlDrr.effective_control_drr_percent` | `report.shop_effective_control_drr` | `None` when dynamic off or observation not sufficient (`derived_from_configured`) |
| actual DRR | `ActualDrrObservation.actual_drr_percent` | `report.actual_drr` | `None`; label **observed**, not a setting |
| headroom | `ShopHeadroomState.headroom_rub` | `report.shop_headroom` | `None` unless 4.1 passed `allowed_spend_rub` and `spend_rub` into the builder. UI must not subtract |
| measurement window | `ActualDrrObservation.measurement_window_id` | `report.actual_drr` | empty → show `MEASUREMENT_UNKNOWN` if present in reasons |
| freshness | **no dedicated field** | closest: `data_sufficiency` + `attribution_lag_days` | render sufficiency; if no observation, show missing fact, not a computed age |
| sufficiency | `DataSufficiency` | `actual_drr.data_sufficiency` | `STALE` / `INSUFFICIENT` / `UNKNOWN` / `UNSUPPORTED` → no control action (`NO_CONTROL_ACTION_STALE_OR_UNKNOWN`) |
| status | `report.decision` | `"DIAGNOSTIC_READ_ONLY"` or `"BLOCKED"` | blockers non-empty ⇒ `BLOCKED` |
| blockers | `report.blockers` | `tuple[str, ...]` | display as-is |
| reasons | `report.reason_codes` | `AdControlReasonCode` | display as-is |
| provenance | `ConfiguredTargetDrr.provenance` and `provenance_index` | `ProvenanceEntry` | empty when DRR resolve blocked |

Shop feature cards (configured, separate from the DRR triple):

- activation: `ConfiguredShopFeatureState.activation`
- payload: `ConfiguredShopFeatureState.payload` only when `ENABLED` (`DrrPolicyParamsV1`, `DynamicDrrControlParamsV1`, CPO param structs in `domain/configured.py`)
- schema_version: read-only from payload / `FeatureDefinition`
- concurrency shown to the user: persistence `revision` (`AdControlShopFeatureRow`), not `state_token` and not campaign `st1`

Header (from `ResolverContext`, not invented): `shop_id`, `HierarchicalEnrollment`, `ControlPathKind`.

## CAMPAIGN_UI_READ_MODEL

One row per `CampaignRef`. Feature cells repeat for all five `AdControlFeatureId`.

| UI field | Source | Fail-closed |
|---|---|---|
| advert_id | `CampaignRef.advert_id` | required |
| campaign identity | `(shop_id, advert_id)` | display name from `AdvSetting` is label only; missing label does not drop the row |
| feature | `AdControlFeatureId` | unknown id → `UNKNOWN_FEATURE`, no editor |
| mode | `ConfiguredCampaignFeatureState.mode` | missing persistence row ⇒ `INHERIT`, `override_payload is None` (`project_configured_campaign_features`) |
| configured value | `override_payload` iff `mode == OVERRIDE`; else null | INHERIT must not show a copied shop payload as “configured” |
| effective value | `ResolvedFeaturePolicy.payload` + `active` | `ResolverBlocked` → reasons, no synthetic payload |
| provenance | `ResolvedFeaturePolicy.provenance` (`EffectiveSourceKind`) | show source kind + scope |
| actual campaign DRR | **MISSING on report** | do **not** reuse shop `actual_drr` as the campaign actual |
| DIRECT attributed GMV | **MISSING** (facts exist only as `AttributionMetrics.attributed_gmv_rub`) | null + attribution blocker from 4.1; UI does not query facts itself |
| DIRECT attributed orders | **MISSING** (`AttributionMetrics.attributed_orders`) | same |
| expected order value | **MISSING** (ADR name `EXPECTED_ATTRIBUTED_ORDER_VALUE_RUB`, no dataclass field) | null; do not use `ProductCpoResolver` or catalog price |
| target CPO proposal | `BoundedCpoProposal.proposed_max_cpo_rub` | today builder sets `None` + `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`. Display that. Do not compute `order_value × DRR` |
| current CPO | `BoundedCpoProposal.current_max_cpo_rub` / `report.current_max_cpo_rub` | `None` if 4.1 did not inject it |
| freshness / sufficiency | per-campaign observation **MISSING** | same gates as shop once 4.1 supplies a campaign `ActualDrrObservation` |
| eligibility | `CampaignHeadroomEligibility.eligible` | computed inside builder but **not stored on the report**. 4.2 read facade must surface it from the same `campaign_headroom_eligibility` call the builder already makes, not a second formula |
| blockers / reasons | eligibility + report | display domain strings/enums |

`CampaignEffectiveControlDrr` is derived control DRR (`inherits_shop_control`), not the configured effective payload. Show it in the derived column only.

## DIAGNOSTICS_READ_MODEL

Mode: **Diagnostics / Test**. No writes. No second engine.

Call chain (only):

1. Load configured slots: `AdControlSettingsRepository.load_shop_slots` / `load_campaign_slots` (or `persistence/context_loader.py`) → `ResolverContext`.
2. Runtime facts (4.1): `ActualDrrObservation`, `allowed_spend_rub`, `spend_rub`, `current_max_cpo_rub`. If absent, pass `actual_drr=None`. Builder then leaves effective/headroom/proposal empty. That is the missing-fact UX.
3. `AdControlDiagnosticsBuilder.build(...)` → `AdControlDiagnosticsReportV1`.
4. Optional dry-run: build `AdControlChangeSetV1` from **unsaved intent** and call `validate_ad_control_changeset` → `AdControlValidationResult` (`DryRunStatus`, `diffs: AdControlSemanticDiffV1`, `errors`). Report flag `dry_run_diff_available` is only a bool; the diff itself is the validation result. Diagnostics of saved policy does not require a ChangeSet.

Show, bound to those objects only:

- configured policy (`configured_shop_features`, `configured_campaign_overrides`)
- inherited/effective policy (`effective_features`)
- provenance (`provenance_index`, per-feature `ProvenanceEntry`)
- actual DRR (`actual_drr`) — observed
- measurement window (`measurement_window_id`)
- freshness — only fields that exist (`data_sufficiency`, `attribution_lag_days`)
- sufficiency (`DataSufficiency`)
- shop headroom (`shop_headroom`)
- campaign eligibility (`CampaignHeadroomEligibility` — must be returned beside the report; builder currently discards the object after merging reasons)
- current CPO (`current_max_cpo_rub`)
- target CPO proposal (`proposed_cpo`)
- blockers, reason codes
- dry-run diff (`AdControlValidationResult.diffs`) when the user has a pending intent

Enrollment / path banners: `NOT_ENROLLED_FAIL_CLOSED`, `LEGACY_PASSTHROUGH_ACTIVE`. Do not present legacy passthrough as inherit.

## WRITE_FLOW

Future production flow (not implemented in this packet):

`UI intent → AdControlChangeSetV1 → validate_ad_control_changeset → dry-run diff → future Apply Authority → AdControlSettingsRepository.apply_*`

**Allowed in the 4.2 implementation phase (when it starts):**

- Read configured state and render it.
- Assemble `AdControlChangeSetV1` in memory.
- Dry-run via `validate_ad_control_changeset` (read-only; no PG write).
- Show `REVISION_CONFLICT` and other `ControlPlaneError` codes.

**Not allowed in 4.2 until a separate Apply slice exists:**

- `repository.apply_shop_mutation`
- `repository.apply_campaign_override`
- `repository.apply_campaign_disable`
- `repository.clear_campaign_feature`
- Any insert/update/delete of `AdControlShopFeatureRow` / `AdControlCampaignFeatureRow` from handlers
- WB API mutations
- Bulk ops

There is no ad-control Apply module under `wb_sky_control_plane`. Channel labels `UI` / `MCP` / `API` are not a write path.

Ops (exact):

| User intent | `op` | Body |
|---|---|---|
| Shop enable/edit/disable | `shop.set_ad_control_feature` | `ShopAdControlFeaturePayloadV1` (`activation`, typed `payload` or null if DISABLED) |
| Campaign override | `campaign.set_ad_control_override` | `CampaignOverridePayloadV1.payload` = typed override only |
| Campaign disable | `campaign.disable_ad_control_feature` | `CampaignFeatureTargetV1` (no payload) |
| Return to inherit | `campaign.clear_ad_control_feature` | `CampaignFeatureTargetV1` (no payload) |

Preconditions: `AdControlRevisionPreconditionV1.expected_revision`. `None` means the authoritative row must be absent. An int means the row’s `revision` must match (`ad_control_validate.py` `_check_revision_precondition`). `state_token` (`acs_*`) is stored, not a CAS key. Do not send campaign `st1`.

One operation = one shop feature or one `(shop_id, advert_id, feature_id)`. No shop-wide campaign fan-out in one op. V1 has **no unsafe bulk-write control**.

## RETURN_TO_INHERIT_FLOW

User action «Вернуть наследование» means **clear the campaign authority row**, not copy the shop value.

1. UI reads current campaign slot. If no row, mode is already `INHERIT`. Dry-run must not invent a payload. Absent row + `expected_revision=None` is the absent-slot precondition (no-op clear only if validator accepts it; do not write a row).
2. If a row exists (`OVERRIDE` or `DISABLED`), intent is `ClearCampaignAdControlFeatureOperation` with `expected_revision=<row.revision>` and `CampaignFeatureTargetV1` (`feature_id`, `schema_version` only).
3. Dry-run semantic: `AdControlMutationKind.CLEAR_TO_INHERIT`, `effective_source_after="SHOP_POLICY_OR_INHERIT"` (`ad_control_validate.py`).
4. After a future Apply, `clear_campaign_feature` deletes the row. Next read uses `CampaignFeatureSlot(mode=INHERIT, payload=None)`.
5. Forbidden: `set_ad_control_override` whose payload equals the current shop payload. That is a fake inherit and violates owner-contract “Campaign INHERIT = no campaign row”.

UX copy: effective values shown while INHERIT come from the resolver (`SHOP_POLICY`, `PRODUCT_OVERRIDE`, `SHOP_DISABLED`, …). Changing the shop changes this campaign without a campaign write. OVERRIDE does not follow later shop edits.

## PAGINATION_MODEL

Current catalog (`ChoiceAdvPaginator`) loads **all** `AdvSetting` rows for the cabinet, slices 20 in memory, and hits Redis per row. Do not copy that for this screen.

4.2 list:

- Server-side keyset on `(shop_id, advert_id)` plus the active sort rank.
- Page size **20** (Telegram keyboard limit already used).
- Inventory source: existing PG campaign list left-joined to `AdControlCampaignFeatureRow`. Missing feature rows render `INHERIT`.
- Resolver + diagnostics run for the **current page** (and for blocked-first ranking, a batch eligibility projection — see performance). Not one WB call per row.
- Display label (`main_nmid`, title) joined in the same page query. Non-authoritative.

## FILTER_MODEL

Predicates are domain modes or diagnostics outputs. «actionable» is **not** a domain enum (`EVIDENCE_GAP` if product later wants a stored status). Presentation mapping only:

| Filter | Predicate | Owner |
|---|---|---|
| overridden | `ConfiguredCampaignFeatureState.mode == OVERRIDE` for the selected feature (or any feature if the chip is “any”) | configured projection |
| disabled | `mode == DISABLED` | configured projection. Do not conflate with shop `FEATURE_DISABLED_AT_SHOP` while campaign mode is INHERIT; that is effective-inactive, show via provenance `SHOP_DISABLED` |
| inherited | `mode == INHERIT` (no authority row) | configured projection |
| blocked | report `decision == "BLOCKED"` or `blockers` non-empty or `ResolverBlocked` | diagnostics. Missing runtime facts ⇒ treat as blocked/unknown, not as healthy |
| actionable | presentation: `CampaignHeadroomEligibility.eligible is True` and not blocked | not a new status code |

Sort (server-side, stable):

1. Blocked first (blocked rank, then `advert_id`).
2. Where the page is diagnostic and values exist: headroom / `proposed_max_cpo_rub` as **display sort only** on domain numbers. If proposal is `None`, those rows sort after numeric proposals, by `advert_id`. UI does not invent a rank score (`HEADROOM_ALLOCATOR_NOT_ACCEPTED` — no production ranking formula).
3. Default non-diagnostic sort: `advert_id` ascending.

Text filter: exact `advert_id` (positive int). Prefix search is optional presentation, not identity.

## RUNTIME_4_1_DEPENDENCIES

4.2 diagnostics columns stay fail-closed until 4.1 supplies these **into** `AdControlDiagnosticsBuilder` (or a thin runtime facade that only calls it):

- Shop `ActualDrrObservation` (percent, `measurement_window_id`, `DataSufficiency`, `attribution_lag_days`) from the attribution/spend port — not from AI `store_drr` families (ADR: non-authoritative).
- Shop `allowed_spend_rub` + `spend_rub` for `headroom_rub`.
- **Separate** per-campaign observation for actual campaign DRR, sufficiency, freshness. Shop observation must not be copied down.
- DIRECT campaign aggregates: orders + GMV for the same window (from attribution facts, assembled in 4.1).
- `EXPECTED_ATTRIBUTED_ORDER_VALUE_RUB` as a domain output.
- `current_max_cpo_rub` when the runtime knows it.
- Order-value `BoundedCpoProposal.proposed_max_cpo_rub` **produced by domain**. Builder today hardcodes `decision="NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED"`. That is a 4.1/domain gap relative to `drr-cpo-price-semantics`. UI displays the code; UI does not “fix” it.
- Enrollment + `ControlPathKind` on `ResolverContext`.
- `CampaignHeadroomEligibility` exposed on the read model (builder already calls `campaign_headroom_eligibility` and drops the struct).

4.2 must not import `attribution_facts` readers or `compute_drr_fact` from Telegram handlers.

## SLICE_B_DEPENDENCIES

Present on this stage and required by the UI:

- Persistence models and repository **reads**: `load_shop_slots`, `load_campaign_slots`; rows carry `revision`.
- `AdControlChangeSetV1` and four ops in `wb_sky_control_plane/models/ad_control_changeset.py`.
- `validate_ad_control_changeset` → `AdControlValidationResult` (`OK` | `REJECTED` | `NO_OP`), `REVISION_CONFLICT`.
- INHERIT never persisted (`PersistedInheritForbiddenError` in `persistence/cas.py`).
- Clear diff `CLEAR_TO_INHERIT`.
- Writes (`apply_*`, `clear_campaign_feature`) exist but are **out of bounds** for the UI layer and for 4.2 until Apply authority is an explicit later slice.

No ad-control `capabilities` type. Do not reuse `CampaignCapabilitiesV1`.

## NEW_UI_SERVICE_REQUIRED

**YES.** `app/modules/ad_control_settings/` needs a read facade (name during implementation, e.g. a `ui_read` or `read_model` module in that package — not a new economics engine):

- Batch page of campaign identities + configured slots.
- Build `ResolverContext` per visible campaign (product DRR only via `ProductDrrPolicyAdapter`).
- Call `AdControlSettingsResolver` + `AdControlDiagnosticsBuilder`.
- Return a frozen view DTO that is a **projection** of those results (shop panel + page rows + optional dry-run errors). No formulas.

Telegram handlers stay thin: auth, FSM, render, intent → ChangeSet → dry-run.

Ownership: `openspec/changes/hierarchical-ad-control-settings/decisions/hierarchical-ad-control-settings-ownership/decision.md` (Proposed) places resolver and future UI under `app/modules/ad_control_settings/`. Product DRR persistence stays in `product_control`. AdvSetting field policy stays in campaign-settings registry — this screen does not edit `AdvSetting` DRR columns.

## NEW_API/ROUTE_REQUIRED

**YES, Telegram only.** New handlers + FSM states under `app/client_bot/` (shop entry → Advertising Control). No new FastAPI settings routes. Webhook app is health-only.

Callback data must carry `shop_id`, `advert_id`, `feature_id`, and a mode/intent discriminator. Page cursor `(shop_id, advert_id, sort)` belongs in FSM, not in a full in-memory campaign dump.

## WHY

The domain report is one optional `CampaignRef` and has no list, no per-campaign economics, and no handler. The existing campaign keyboard cannot host five-feature mode chips plus diagnostics without a batch read model. Dry-run validation already exists; Apply does not. A new read service + Telegram route is the smallest 4.2 surface that does not write rows and does not reimplement headroom.

## DIRECT_DB_WRITE_ALLOWED

**NO**

## SECOND_CALCULATION_ENGINE_ALLOWED

**NO**

## TEST_PLAN

Unit tests (mocks only) beside existing `tests` for `ad_control_settings` and a new client_bot view-model test module. No PG in unit tests. Integration of repository reads stays in existing persistence tests; UI tests assert the facade calls resolver/builder/validator and never `apply_*`.

| Case | Assert |
|---|---|
| Inherit display | No campaign row → mode `INHERIT`, `override_payload is None`, effective payload from shop/product provenance `SHOP_POLICY` or `PRODUCT_*` |
| Override display | Mode `OVERRIDE`, configured payload is the override, effective payload equals it, provenance `CAMPAIGN_OVERRIDE` |
| Disabled display | Mode `DISABLED`, payload null, reason `FEATURE_DISABLED_AT_CAMPAIGN`, effective inactive |
| Return-to-inherit | Intent op is `campaign.clear_ad_control_feature` with no payload; dry-run intent `CLEAR_TO_INHERIT`; resulting projection has no campaign payload. Reject a test that sets override payload equal to shop values |
| Configured vs effective | Shop DISABLED + campaign INHERIT shows configured shop activation DISABLED and effective inactive (`SHOP_DISABLED`), not a campaign DISABLED row |
| Provenance | Each feature cell shows `EffectiveSourceKind` + `source_scope` from `ResolvedFeaturePolicy` |
| Unsupported feature | `UNKNOWN_FEATURE` / `UNSUPPORTED_SCOPE_FOR_FEATURE` → no editor, fail closed |
| Unknown state | Unknown enrollment/path/sufficiency → `ResolverBlocked` or `UNKNOWN` sufficiency, decision `BLOCKED`, no numeric fallback |
| Revision conflict UX | Validator `REVISION_CONFLICT` (stale int, or `None` while row exists, or int while row absent) → UI message + reload revision; no apply call |
| Blocked diagnostics | `blockers` non-empty → `decision == BLOCKED`; CPO proposal not shown as a number |
| Fresh runtime facts | `DataSufficiency.SUFFICIENT` + non-null observation → observed DRR and headroom **as returned** |
| Stale runtime facts | `STALE` → `ACTUAL_DRR_STALE` and `NO_CONTROL_ACTION_STALE_OR_UNKNOWN`; observed value may display with stale badge; not editable |
| Missing runtime facts | `actual_drr is None` → effective control, headroom, proposal are `None`; status not “healthy” |
| Large campaign table | Facade requests one page (20) by keyset; builder not invoked for off-page ids; test double proves call count |
| No direct DB writes | Handler/facade test: repository apply/clear methods not called; only `load_*` and `validate_ad_control_changeset` |

Also: diagnostics mode disables intent submission; actual DRR widget has no input control; five features are independent (override one does not copy others).

## CRITICAL

- UI writes persistence rows or calls `apply_*` / `clear_campaign_feature`.
- Return-to-inherit copies shop payload into a campaign override.
- UI computes DRR, headroom ₽, expected order value, or `TARGET_CPO_RUB` (including via `ProductCpoResolver`).
- Shop `actual_drr` displayed as per-campaign actual DRR.
- Observed actual DRR rendered as an editable setting.
- Diagnostics path uses a different formula than `AdControlDiagnosticsBuilder` / `headroom_eval`.
- Unknown or missing facts shown as zero or as a green OK.

## HIGH

- Blocked-first sort that loads every campaign’s diagnostics with WB/CH fan-out.
- Bulk disable/override (do not port `off_all`, `ApplyDefaultsForShop`, keyword mass reset, Excel import loops).
- Using `state_token` or AdvSetting `st1` as the ad-control CAS key.
- Treating `PRICE_SEMANTICS_NOT_ACCEPTED_*` as a UI bug to patch locally while the builder still emits it. Display it. Domain/4.1 owns the order-value proposal.
- Editing `AdvSetting` or product-control tables from this screen.
- Conflating campaign `DISABLED` with inherited `SHOP_DISABLED`.

## MEDIUM

- Full-cabinet load copied from `ChoiceAdvPaginator` (works for small shops, breaks large ones, N+1 Redis).
- Telegram message size if five features are fully expanded on every row. Summary chips + drill-down.
- `CampaignHeadroomEligibility` dropped by the builder, so the table cannot show eligibility without a facade change.
- Human campaign label missing (`CampaignRef` has no title).
- Filter «actionable» without a domain code — keep it a presentation alias and test the mapping.

## LOW

- RU/EN copy, chip colors.
- Page size 20 vs 25 (stick to 20 for Telegram).
- Schema version badge (`1` in V1), read-only.
- Collapsed shop panel vs campaign-first default. Either is fine if both zones exist.

## FILES_LIKELY_TO_CHANGE_IN_4_2

Implementation phase only (this chat changes none of these):

- New read facade under `app/modules/ad_control_settings/` (projection only).
- New Telegram package: handlers, FSM, keyboards, message formatters under `app/client_bot/` and/or `app/modules/.../telegram/`.
- Shop menu entry (`app/modules/shop_menu/`) — one callback to the new section.
- Unit tests for projection, inherit/override/disabled, dry-run clear, revision conflict, missing/stale facts, page bounding, no `apply_*`.
- Possible small domain addition **only if** 4.1/owner agrees: put `CampaignHeadroomEligibility` on the diagnostics result so UI does not re-call eligibility. That is a domain field exposure, not a new formula. If 4.1 owns the report shape, 4.2 waits.

Not in 4.2: `persistence/repository.py` apply methods, shop-runner actuation, OpenSpec archive, Apply authority.

## IMPLEMENTATION_READY

**PARTIAL.**

Ready now: configured shop panel, campaign mode table, provenance of **configured** policy, inherit/override/disabled rendering, clear-to-inherit **dry-run** (no apply), revision-conflict UX, fail-closed unknown feature.

Not ready: economic diagnostics columns (actual DRR, headroom, DIRECT GMV/orders, expected order value, target CPO, per-campaign freshness/sufficiency/eligibility on a list DTO). Those wait on 4.1 runtime ports and on the builder stopping the hardcoded order-value block — UI must not fill the gap.

## BLOCKERS

1. Task 4.1 runtime shop-runner integration is absent on `a2e8453e`. No factual port feeds `AdControlDiagnosticsBuilder`.
2. `AdControlDiagnosticsReportV1` is single-campaign and has no per-campaign `ActualDrrObservation`, no DIRECT GMV/orders, no `EXPECTED_ATTRIBUTED_ORDER_VALUE_RUB`.
3. `AdControlDiagnosticsBuilder.build` sets `proposed_max_cpo_rub=None` and `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED` even though accepted ADR enables V1 order-value proposals. UI must not compensate.
4. `CampaignHeadroomEligibility` is not a report field.
5. No list/keyset read API; existing UI loads all campaigns.
6. No ad-control Apply authority. Dry-run is the end of the write path for 4.2.
7. Freshness has no timestamp field distinct from `DataSufficiency` / `attribution_lag_days`.
8. «actionable» has no domain symbol.

## UX risks (scale)

- Telegram payload limits if diagnostics text is inlined for 20 campaigns × 5 features. Use chips + one-campaign diagnostics drill-down.
- Blocked-first sort across the whole shop needs a batch snapshot. Do it in the read facade from already-loaded facts, never per-row WB.
- Legacy `bot_active` / AdvSetting activity is a different switch from `AdControlFeatureMode.DISABLED`. Label them differently.
- FSM page filters that keep full id lists will OOM/timeout on large cabinets. Cursor only.
- Dry-run of a stale screen: always reload `revision` before showing a confirm. Conflict reloads the row; it does not retry the write.

## Performance requirements

- No WB API on list or diagnostics read.
- No CH/PG N+1 per keyboard row. One page query + one slot load for those ids.
- Diagnostics builder only for the open page (or one selected campaign in diagnostics drill-down).
- Filter/sort/slice on the server before render.
- One ChangeSet operation per feature cell. No multi-campaign apply.
- Redis `check_last_24_hours` from the legacy list is out of this screen.
