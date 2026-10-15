---
cursor:
  subagentId: "bc-ee799658-6b27-517d-9811-d5d14e734675"
---

# Runtime economic facts — archaeology (Diagnostics contract prep)

Repo: `/agent/repos/adv-bot`. READ ONLY survey for hierarchical ad control UI diagnostics.

## Task 4.1 / 4.2 (openspec)

From `openspec/changes/hierarchical-ad-control-settings/tasks.md`:

| Task | Status in tasks.md | Stated scope |
|------|-------------------|--------------|
| **4.1** | Unchecked | Runtime shop-runner integration |
| **4.2** | Unchecked | UI Advertising Control + Diagnostics |

No further 4.1/4.2 breakdown in `tasks.md`. **EXPECTED_4_1** (inferred from change artifacts + ADR, not a separate task spec):

- Wire shop-runner (or adjacent runtime read path) to load configured slots (`context_loader` + `AdControlSettingsRepository`).
- Populate `ResolverContext` (`HierarchicalEnrollment`, `ControlPathKind`, shop/campaign slots, optional `ProductDrrPolicyAdapter`).
- Build factual inputs: `ActualDrrObservation` (shop and per-campaign), `allowed_spend_rub` / `spend_rub` per `drr-cpo-price-semantics` §5.
- Map attribution / order-ledger coverage → `DataSufficiency` (fail-closed).
- Call `AdControlDiagnosticsBuilder.build` (or successor) per shop/campaign; **no production CPO actuation** until bounded proposal path accepts order-value semantics in code.
- Expose runtime read API for UI (4.2) projecting domain results only.

**EXPECTED_4.2**: Owner-contract — Advertising Control + Diagnostics/Test, same resolver semantics, no writes.

**PRESENT today:** Slice A+B domain + persistence + `validate_ad_control_changeset` dry-run. **No** shop-runner / UI integration. **No** runtime port that materializes `ActualDrrObservation` from CH/WB.

---

## 1) Existing domain symbols (UI read-model feedstock)

### Hierarchical ad control (`app/modules/ad_control_settings/`)

| NAME | PATH | FIELDS (summary) | WHAT_IT_MEANS | GAPS for UI |
|------|------|------------------|---------------|-------------|
| `AdControlDiagnosticsReportV1` | `domain/diagnostics.py` | shop_id, campaign, configured_shop/campaign tuples, effective_features, configured_target_drr, actual_drr, shop/campaign effective DRR, shop_headroom, current_max_cpo_rub, proposed_cpo, decision, reason_codes, blockers, dry_run_diff_available, provenance_index | Canonical **read-only diagnostic snapshot** (one campaign per report) | No multi-campaign table; no shop-only aggregate without campaign; `CampaignHeadroomEligibility` not on report; no per-campaign `actual_drr` field |
| `AdControlDiagnosticsBuilder` | `domain/diagnostics_builder.py` | `build(context, actual_drr, allowed_spend_rub, spend_rub, current_max_cpo_rub, dry_run_diff_available)` | Pure assembly: resolver + headroom + eligibility gates | No I/O; caller must supply facts; `proposed_cpo` always blocked with `PRICE_SEMANTICS_NOT_ACCEPTED_*` in current code (ADR/order-value gap) |
| `ResolverContext` | `domain/resolver_models.py` | enrollment, control_path, shop_id, shop_features, campaign, campaign_features, product_drr | Configured **inputs** to resolver (no runtime economics) | Enrollment/path not populated from shop-runner yet |
| `ResolvedFeaturePolicy` | `domain/resolver_models.py` | feature_id, active, payload, provenance, reason_codes | **Effective configured** policy per feature | Not runtime DRR/CPO |
| `ConfiguredShopFeatureState` / `ConfiguredCampaignFeatureState` | `domain/configured_state.py` | feature_id, scope, activation/mode, payload/override_payload, schema_version | **Configured** slots (INHERIT does not copy shop payload to campaign row) | No economic facts |
| `ConfiguredTargetDrr` | `domain/drr_state.py` | target_drr_percent, max_drr_percent, provenance | Resolved **configured** DRR target (policy) | Shop vs campaign scope collapsed into one resolved target for context |
| `ActualDrrObservation` | `domain/drr_state.py` | actual_drr_percent, measurement_window_id, data_sufficiency, attribution_lag_days | **Observed** DRR fact port (read-only) | No provenance of spend/GMV sources; single blob for shop+campaign context in builder (no separate campaign actual type) |
| `ShopEffectiveControlDrr` | `domain/drr_state.py` | effective_control_drr_percent, derived_from_configured | **Derived** shop control DRR | Placeholder when `DYNAMIC_DRR_CONTROL` enabled; no production dynamic formula |
| `CampaignEffectiveControlDrr` | `domain/drr_state.py` | effective_control_drr_percent, inherits_shop_control, provenance | **Derived** campaign control DRR | Currently mirrors shop effective when dynamic enabled; not campaign-specific actual |
| `ShopHeadroomState` | `domain/headroom.py` | configured_target_drr_percent, actual_drr_percent, headroom_rub, control_pressure | Derived headroom / pressure | `headroom_rub` only if caller passes allowed_spend + spend; ADR formula not encapsulated in domain type |
| `CampaignHeadroomEligibility` | `domain/headroom.py` | campaign, eligible, reason_codes, blockers | Campaign eligibility for bounded CPO | **Not** exported on `AdControlDiagnosticsReportV1` (only folded into report reason_codes/blockers) |
| `BoundedCpoProposal` | `domain/headroom.py` | campaign, current_max_cpo_rub, proposed_max_cpo_rub, decision, reason_codes | Bounded CPO proposal contract | Implementation blocks proposals; no TARGET_CPO_RUB field (ADR §4) |
| `HeadroomAllocator` | `domain/headroom.py` | Protocol `propose_bounded_adjustments` | Future ranking | **EXPECTED_4.3** / not implemented |
| `derive_shop_effective_control_drr` | `domain/headroom_eval.py` | fn | Derived effective DRR | UI must not compute |
| `evaluate_shop_headroom_state` | `domain/headroom_eval.py` | fn | Headroom + pressure | UI must not compute DRR/headroom |
| `control_action_allowed` | `domain/headroom_eval.py` | fn | Sufficiency gate | UI must not re-derive |
| `campaign_headroom_eligibility` | `domain/headroom_eval.py` | fn | Eligibility | UI must not re-derive |
| `AdControlSettingsResolver` | `domain/resolver.py` | resolve_feature, assert_hierarchical_path | Effective **configured** policy | Explicitly **without** derived DRR/headroom |
| `ProvenanceEntry` | `domain/provenance.py` | feature_id, source_kind, source_scope, schema_version | Where effective config came from | No factual-source provenance for GMV/spend |
| `AdControlReasonCode` | `domain/reason_codes.py` | enum | Deterministic diagnostics/eligibility codes | ADR §9 blockers (e.g. `DIRECT_ATTRIBUTION_MISSING`) not all mirrored here |
| `DataSufficiency` | `domain/enums.py` | SUFFICIENT, INSUFFICIENT, STALE, UNSUPPORTED, UNKNOWN | Observation quality for control | Mapping from attribution coverage **MISSING** (EXPECTED_4_1) |
| `CampaignRef` | `domain/campaign_ref.py` | shop_id, advert_id | Campaign identity | No display name / WB metadata |
| `ProductDrrPolicyAdapter` | `domain/product_adapter.py` | maps `EffectiveControlResult` → DrrPolicyParamsV1 | PRODUCT tier for inherit | Requires product_control outcome from outside |
| Payload types | `domain/configured.py` | DrrPolicyParamsV1, DynamicDrrControlParamsV1, Cpo*ParamsV1 | Owner **configured** parameters | CPO features are policy knobs, not runtime facts |
| `load_resolver_*` | `persistence/context_loader.py` | async loaders | PG → resolver slots | No economic facts |

### Persistence / dry-run (configured, not runtime economics)

| NAME | PATH | FIELDS | MEANING | GAPS |
|------|------|--------|---------|------|
| `AdControlShopFeatureRow` / `AdControlCampaignFeatureRow` | `persistence/models.py` | shop_id, feature_id, advert_id, payload_json, revision, state_token, … | Configured authority rows | Not a UI read model |
| `AdControlShopFeatureSnapshotV1` / `AdControlCampaignFeatureSnapshotV1` | `wb_sky_control_plane/kernel/ad_control_validate.py` | snapshots for dry-run | ChangeSet validation inputs | Not runtime diagnostics |
| `validate_ad_control_changeset` → `AdControlValidationResult` | same | status, diffs, errors | **Dry-run** only | `dry_run_diff_available` flag on diagnostics report; no embedded diff |
| `AdControlChangeSetV1` | `wb_sky_control_plane/models/ad_control_changeset.py` | ops, scope, preconditions | Intent to mutate config | Not economic state |

### Attribution / campaign economics (adjacent, not wired to ad_control)

| NAME | PATH | FIELDS | MEANING | GAPS |
|------|------|--------|---------|------|
| `AttributionFactsReader` | `attribution_facts/ports/reader.py` | `query(scope, window)` → `AttributionQueryResult` | DIRECT/LINKED facts + coverage | Not called from ad_control; EXPECTED_4_1 adapter |
| `AttributionCommerceFact` / `AttributionMetrics` | `attribution_facts/domain/models.py` | attributed_orders, attributed_gmv_rub, … | Grain facts | Need aggregation + window for UI fields |
| `AttributionCoverage` | same | status, reason_codes, date ranges | Window completeness | Must map to `DataSufficiency` in 4.1 |
| `DerivedFactEconomics` | same | metric_name, value, reason_codes | CPO/DRR derivations | |
| `compute_drr_fact` / `compute_cpo_fact` | `attribution_facts/domain/derived_metrics.py` | fns | spend/GMV or spend/orders | Campaign scope; fail-closed on coverage |
| AI analysis wrappers | `ai_package_v1/analysis/attribution_evidence.py` | `DRR_FACT_DIRECT`, `ATTRIBUTION_DIRECT_*`, `assess_campaign_spend_for_economics` | Analysis-layer naming + spend window checks | **Non-authoritative** for hierarchical control per ADR; duplicate logic risk if UI uses directly without 4.1 facade |

### Product control (catalog CPO path — not V1 campaign headroom authority)

| NAME | PATH | MEANING | GAPS |
|------|------|---------|------|
| `DrrProfile` | `product_control/domain/models.py` | target/max % | Shared with DRR_POLICY payload | |
| `ProductCpoResolver` | `product_control/domain/product_cpo_resolver.py` | price × DRR% → CPO | **Path A** catalog | **Forbidden** as V1 `TARGET_CPO_RUB` substitute per ADR §8 |
| `EffectiveControlResolver` | `product_control/domain/effective_control_resolver.py` | Product enrollment → profile | PRODUCT tier only | Separate from `HierarchicalEnrollment` |

### Shop-runner legacy runtime (parallel path)

| NAME | PATH | MEANING | GAPS |
|------|------|---------|------|
| `ComplexAdv.fact_pay_for_order` / `resolve_cpo` | `shop_runner/.../complex_adv.py` | Legacy plan-fact CPO | Not hierarchical `TARGET_CPO_RUB` |
| `StatsFreshnessState` | `shop_runner/.../stats_freshness_guard.py` | CH stats age | Campaign automation guard; not `DataSufficiency` |
| V3 PFO “headroom” | `auto_updater_v3/campaign_pfo_gates.py` | Ratio vs max CPO | **Different semantics** from shop DRR headroom |

### OpenSpec / ADR (normative, not code symbols)

| NAME | PATH | MEANING |
|------|------|---------|
| `drr-cpo-price-semantics` | `openspec/decisions/drr-cpo-price-semantics/decision.md` | Shop/campaign DRR formulas, order-value TARGET_CPO, headroom rub, fail-closed blockers §9 |
| Change spec | `openspec/changes/hierarchical-ad-control-settings/specs/.../spec.md` | Stale actual DRR blocks control; dry-run revision rules |

---

## 2) Proposed UI-facing read model (projections only)

**Rule:** UI MUST NOT compute `actual_drr`, `headroom_rub`, `TARGET_CPO_RUB`, or DRR%. All numeric economics from domain builder/resolver or **MISSING_DOMAIN_SYMBOL** until 4.1.

### SHOP panel

| UI field | SOURCE_SYMBOL | SOURCE_PATH | TYPE | DERIVED_BY | FAIL_CLOSED if missing |
|----------|---------------|-------------|------|------------|------------------------|
| configured target DRR | `ConfiguredTargetDrr` / `DrrPolicyParamsV1.profile` | `drr_state.py` / `configured.py` via `report.configured_target_drr` or shop row in `configured_shop_features` | `Decimal` % | `AdControlSettingsResolver` + `AdControlDiagnosticsBuilder` | Hide numeric target; show `ResolverBlocked` / `FEATURE_DISABLED_*` reasons |
| effective target DRR | `ShopEffectiveControlDrr` | `report.shop_effective_control_drr.effective_control_drr_percent` | `Decimal \| None` | `derive_shop_effective_control_drr` | `null` + reason if dynamic off or sufficiency not SUFFICIENT |
| actual DRR | `ActualDrrObservation` | `report.actual_drr.actual_drr_percent` | `Decimal \| None` | **EXPECTED_4_1** factual port → observation | `null`; sufficiency ≠ SUFFICIENT → no control semantics |
| headroom | `ShopHeadroomState` | `report.shop_headroom.headroom_rub` (+ optional `control_pressure`) | `Decimal \| None` | `evaluate_shop_headroom_state` (needs allowed/spend inputs) | `null` if inputs absent or sufficiency gate; **UI_MUST_NOT_COMPUTE** headroom from GMV |
| measurement window | `ActualDrrObservation` | `measurement_window_id` | `str` | **EXPECTED_4_1** port labels window | Show id + blocker if empty |
| freshness | **MISSING_DOMAIN_SYMBOL** | — | — | **EXPECTED_4_1** (map observation age / attribution lag policy) | `attribution_lag_days` on observation is partial only |
| sufficiency | `DataSufficiency` | `actual_drr.data_sufficiency` | enum | **EXPECTED_4_1** mapper from coverage/freshness | UNKNOWN → fail-closed display |
| status | `AdControlDiagnosticsReportV1` | `decision` (`DIAGNOSTIC_READ_ONLY` / `BLOCKED`) | `str` | `AdControlDiagnosticsBuilder` | `BLOCKED` if any blockers |
| blockers | report | `blockers` | `tuple[str, ...]` | builder + eligibility | list as-is |
| reasons | report | `reason_codes` | `tuple[AdControlReasonCode, ...]` | resolver/headroom gates | include `ACTUAL_DRR_STALE`, `NOT_ENROLLED_*`, etc. |
| provenance | `ProvenanceEntry` | `provenance_index`, `configured_target_drr.provenance` | tuple / struct | resolver | empty if resolve blocked |

### CAMPAIGN table (per row)

| UI field | SOURCE_SYMBOL | SOURCE_PATH | TYPE | DERIVED_BY | FAIL_CLOSED |
|----------|---------------|-------------|------|------------|-------------|
| advert_id | `CampaignRef` | `campaign.advert_id` | `int` | identity | — |
| campaign identity | `CampaignRef` | shop_id + advert_id | — | — | display name **MISSING_DOMAIN_SYMBOL** (AdvSetting not in report) |
| feature | `AdControlFeatureId` | per-row from `effective_features` / configured tuples | enum | registry | — |
| mode | `ConfiguredCampaignFeatureState` | `mode` / shop `activation` | enum | configured projection | — |
| configured value | `ConfiguredCampaignFeatureState` / shop payload | override_payload or shop payload | typed payload | projection | null for INHERIT at campaign |
| effective value | `ResolvedFeaturePolicy` | `effective_features[].payload` | payload | `AdControlSettingsResolver` | blocked → reasons only |
| provenance | `ProvenanceEntry` | `effective_features[].provenance` | struct | resolver | — |
| actual campaign DRR | **MISSING_DOMAIN_SYMBOL** (use `ActualDrrObservation` per campaign) | Today only shop-level observation in builder | `Decimal \| None` | **EXPECTED_4_1** `compute_drr_fact` / port | **UI_MUST_NOT_COMPUTE** spend/GMV ratio |
| DIRECT attributed GMV | `AttributionMetrics` / analysis constants | **EXPECTED_4_1** aggregate from `AttributionFactsReader` | `Decimal` | domain aggregate (not AI package in prod UI) | null + `BLOCKED_BY_ATTRIBUTION_FACTS` |
| DIRECT attributed orders | same | same | `int` | domain aggregate | null if incomplete |
| expected order value | **MISSING_DOMAIN_SYMBOL** (ADR name) | ADR §3–§4 formula | `Decimal` | **EXPECTED_4_1** domain fn on DIRECT sums | `ORDER_VALUE_UNAVAILABLE` |
| target CPO proposal | `BoundedCpoProposal` | `report.proposed_cpo` (today blocked) | `Decimal \| None` | **EXPECTED_4_1** order-value proposal builder | `proposed_max_cpo_rub` null + reason codes; **UI_MUST_NOT_COMPUTE** price×DRR |
| freshness | **MISSING_DOMAIN_SYMBOL** | — | — | **EXPECTED_4_1** | — |
| sufficiency | `DataSufficiency` | campaign-scoped observation (missing) | enum | **EXPECTED_4_1** | same as shop gate |
| eligibility | `CampaignHeadroomEligibility` | **not on report** — use builder output or extend report | `eligible: bool` | `campaign_headroom_eligibility` | false + reasons |
| blockers | eligibility + report | `blockers` / eligibility.blockers | strings | domain | — |
| reasons | eligibility + report | `reason_codes` | enums | domain | — |

### Fields that would force forbidden UI math (flagged)

- **actual DRR** (shop or campaign): ratio spend/GMV — only via `ActualDrrObservation` / `compute_drr_fact` (**EXPECTED_4_1**).
- **headroom_rub**: only via `evaluate_shop_headroom_state` with port-supplied allowed/spend.
- **expected order value**: GMV/orders aggregate — ADR §3; no UI division.
- **target CPO proposal**: ADR §4 `TARGET_CPO_RUB`; not `ProductCpoResolver` for V1 campaign control.
- **control_pressure**: configured − actual % — already in `ShopHeadroomState`; UI displays only.

### Dry-run (diagnostics adjunct)

| UI need | SOURCE | Notes |
|---------|--------|-------|
| dry-run available | `AdControlDiagnosticsReportV1.dry_run_diff_available` | bool; diffs from `AdControlValidationResult` when 4.2 wires ChangeSet preview |

---

## Implementation notes for coordinator

1. **Single-campaign report** today — 4.2 likely needs a list DTO or repeated `AdControlDiagnosticsReportV1`.
2. **`CampaignHeadroomEligibility`** should be first-class on runtime read model for table `eligibility` column.
3. **Code vs ADR:** `diagnostics_builder` still emits `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED` for all proposals; ADR §10 says order-value path should supersede in implementation (4.1).
4. **No `grep` hits** for `ad_control` under `app/modules/shop_runner` — confirms 4.1 absent.
