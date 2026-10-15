---
cursor:
  subagentId: "bc-c1e53576-87ee-575a-be0d-a2eceeeec9b6"
---

# Wave 1C — UI diagnostics read model inventory (task 4.2)

Repo: `/agent/repos/adv-bot` · Change: `openspec/changes/hierarchical-ad-control-settings` · READ ONLY.

## Executive: canonical read aggregate today

UI-facing diagnostics **should** consume **`AdControlDiagnosticsReportV1`** built by **`AdControlDiagnosticsBuilder.build`** (pure, no I/O). Configured mutations dry-run uses **`validate_ad_control_changeset`** → **`AdControlValidationResult`** (separate from runtime diagnostics report).

**Not in tree:** shop-runner runtime wiring (task 4.1), UI/API transport, factual ports that populate `ActualDrrObservation` / spend inputs, campaign-table multi-row aggregate, campaign-scoped actual DRR / DIRECT GMV-orders / expected order value / observed CPO domain types wired into diagnostics.

---

## 1. SHOP panel field map

| UI field | Symbol | Path / accessor | Type | Kind | NOTES |
|----------|--------|-----------------|------|------|-------|
| configured target DRR | `ConfiguredTargetDrr` | `AdControlDiagnosticsReportV1.configured_target_drr.target_drr_percent` (+ `max_drr_percent`) | `Decimal` | **policy (resolved configured)** | Populated only when `DRR_POLICY` resolves active with `DrrPolicyParamsV1`. Shop **configured** slot also at `configured_shop_features[*]` where `feature_id==DRR_POLICY`. |
| effective target DRR | `ShopEffectiveControlDrr` | `…shop_effective_control_drr.effective_control_drr_percent` | `Decimal \| None` | **derived** | Requires `configured_target_drr` + `actual_drr`; gated by `DYNAMIC_DRR_CONTROL` + `DataSufficiency.SUFFICIENT`. Not a user setting. |
| actual DRR | `ActualDrrObservation` | `…actual_drr.actual_drr_percent` | `Decimal \| None` | **observed** | Caller-supplied fact port input to builder; **must not** be editable as policy. |
| headroom | `ShopHeadroomState` | `…shop_headroom.headroom_rub` (also `control_pressure`) | `Decimal \| None` | **derived** | `headroom_rub` needs `allowed_spend_rub` + `spend_rub` builder kwargs + sufficient actual DRR. ADR: `allowed − spend` in RUB. |
| measurement window | `ActualDrrObservation` | `…actual_drr.measurement_window_id` | `str` | **observed** | Opaque window id (tests use `"7d"`). No separate domain “window object”. |
| freshness | **MISSING_DOMAIN_SYMBOL** | closest: `ActualDrrObservation.attribution_lag_days` + `DataSufficiency` | `int \| None` + enum | **observed / derived gate** | No first-class `Freshness` type in `ad_control_settings`. Staleness flows through `data_sufficiency` → `control_action_allowed`. |
| sufficiency | `DataSufficiency` | `…actual_drr.data_sufficiency` | `DataSufficiency` | **observed** | `SUFFICIENT \| INSUFFICIENT \| STALE \| UNSUPPORTED \| UNKNOWN`. |
| status | (report field) | `…decision` | `str` | **derived** | `"DIAGNOSTIC_READ_ONLY"` or `"BLOCKED"` when blockers non-empty. Not an enum. |
| blockers | (report field) | `…blockers` | `tuple[str, …]` | **derived** | Freeform strings (e.g. `"not_enrolled"`, `"no_control_action"`). **Not** `AdControlReasonCode`. |
| reasons | `AdControlReasonCode` | `…reason_codes` | `tuple[AdControlReasonCode, …]` | **derived** | Machine codes from resolver/headroom gates. |
| provenance | `ProvenanceEntry` | `…provenance_index` (+ per-feature `effective_features[*].provenance`) | `tuple[ProvenanceEntry, …]` | **configured effective lineage** | `source_kind`, `source_scope`, `feature_id`, `schema_version`. |

---

## 2. CAMPAIGN table field map

Context: report is **single-campaign** (`campaign: CampaignRef | None`). No domain type for “shop-wide campaign table rows” yet.

| UI field | Symbol | Path / accessor | Type | Kind | NOTES |
|----------|--------|-----------------|------|------|-------|
| advert_id | `CampaignRef` | `…campaign.advert_id` | `int` | **identity** | Authority `(shop_id, advert_id)`. |
| campaign identity | `CampaignRef` | `…campaign` (`shop_id`, `advert_id`) | `CampaignRef` | **identity** | `main_nmid` explicitly not authority. |
| feature | `AdControlFeatureId` | `configured_campaign_overrides[*].feature_id` / `effective_features[*].feature_id` | enum | **policy key** | V1 registry: `DRR_POLICY`, `DYNAMIC_DRR_CONTROL`, CPO_* features. |
| mode | `AdControlFeatureMode` | `configured_campaign_overrides[*].mode` | enum | **policy (configured)** | `INHERIT \| OVERRIDE \| DISABLED`. Shop uses `ShopFeatureActivation` on `configured_shop_features`. |
| configured value | `ConfiguredCampaignFeatureState` | `override_payload` only when `mode==OVERRIDE`; else **no campaign configured value** for INHERIT | `ConfiguredFeaturePayload \| None` | **policy** | INHERIT must not fabricate shop copy (Owner tests A–C). |
| effective value | `ResolvedFeaturePolicy` | `effective_features[*].payload` + `active` | `ConfiguredFeaturePayload \| None` | **effective configured (resolved)** | Live inherit: effective shop/product payload without persisting on campaign row. |
| provenance | `ProvenanceEntry` | `effective_features[*].provenance` | `ProvenanceEntry` | **lineage** | e.g. `SHOP_POLICY`, `CAMPAIGN_OVERRIDE`, `PRODUCT_OVERRIDE`. |
| actual campaign DRR | **MISSING_DOMAIN_SYMBOL** | closest: `ActualDrrObservation` (shop-level on report only) | — | **observed** | ADR `campaign_actual_drr` defined in `openspec/decisions/drr-cpo-price-semantics/decision.md`; **no** `CampaignActualDrrObservation` or port in `app/modules/ad_control_settings`. |
| DIRECT attributed GMV | **MISSING_DOMAIN_SYMBOL** | closest: `AttributionMetrics.attributed_gmv_rub` | `Decimal \| None` | **observed** | `app/modules/attribution_facts/domain/models.py`; **not** on `AdControlDiagnosticsReportV1`. |
| DIRECT attributed orders | **MISSING_DOMAIN_SYMBOL** | closest: `AttributionMetrics.attributed_orders` | `int \| None` | **observed** | Same; DIRECT class via `AttributionCommerceFact.attribution_class`. |
| expected order value | **MISSING_DOMAIN_SYMBOL** | closest: ADR term `EXPECTED_ATTRIBUTED_ORDER_VALUE_RUB` / `expected_attributed_order_value_rub` | — | **observed (aggregated)** | Formula in ADR §1/§4; **no** Python symbol in diagnostics module. |
| target CPO proposal | `BoundedCpoProposal` | `…proposed_cpo` | `BoundedCpoProposal` | **derived proposal** | Foundation: `proposed_max_cpo_rub=None` + `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`. Not production actuation. |
| freshness | **MISSING_DOMAIN_SYMBOL** | closest: campaign would share shop `actual_drr` today | — | — | No campaign-specific freshness symbol. |
| sufficiency | `DataSufficiency` | via shared `actual_drr` on report | enum | **observed** | Campaign eligibility uses same observation in `campaign_headroom_eligibility`. |
| eligibility | `CampaignHeadroomEligibility` | **MISSING on report** — only via `campaign_headroom_eligibility(...)` | dataclass | **derived** | Builder merges into `reason_codes` / `blockers`; **not** exposed as field on `AdControlDiagnosticsReportV1`. |
| blockers | (report + eligibility) | `…blockers` | `tuple[str, …]` | **derived** | Campaign-specific blockers merged at report level. |
| reasons | `AdControlReasonCode` | `…reason_codes` | tuple enum | **derived** | Includes eligibility gates. |

---

## 3. Diagnostics / test mode concepts

| Concept | Symbol | Path | Type | Kind |
|---------|--------|------|------|------|
| configured policy | `ConfiguredShopFeatureState`, `ConfiguredCampaignFeatureState` | `…configured_shop_features`, `…configured_campaign_overrides` | tuples | **policy** |
| inherited/effective policy | `ResolvedFeaturePolicy` | `…effective_features` | tuple | **effective configured** |
| current CPO if available | (report kw input) | `…current_max_cpo_rub` | `Decimal \| None` | **external input / legacy hint** | Passed into builder; **not** ADR `OBSERVED_CPO_RUB`. |
| target CPO proposal | `BoundedCpoProposal` | `…proposed_cpo` | dataclass | **derived proposal** |
| dry-run diff | `AdControlSemanticDiffV1` | `AdControlValidationResult.diffs[*]` | Pydantic model | **configured mutation preview** |
| measurement window | `ActualDrrObservation.measurement_window_id` | `…actual_drr` | `str` | **observed** |
| dry-run available flag | (report) | `…dry_run_diff_available` | `bool` | **UI hint** | Builder param; does not run dry-run itself. |

---

## 4. Policy vs observed vs derived (critical)

| Category | Domain artifacts | UI rule |
|----------|------------------|---------|
| **Policy (editable via ChangeSet / PG)** | `ConfiguredShopFeatureState`, `ConfiguredCampaignFeatureState`, `ShopFeatureSlot`, `CampaignFeatureSlot`, `DrrPolicyParamsV1`, other `ConfiguredFeaturePayload` | Settings UI writes only through `AdControlChangeSetV1` + future Apply. |
| **Effective configured (read, recomputed)** | `ResolvedFeaturePolicy`, `ConfiguredTargetDrr`, `ProvenanceEntry` | Shows inherit/override outcome; not persisted on INHERIT campaign rows. |
| **Observed facts** | `ActualDrrObservation`, (future) attribution aggregates, shop spend/GMV ports | **Never** treat `actual_drr_percent` or attribution sums as editable settings. |
| **Derived / proposals** | `ShopEffectiveControlDrr`, `CampaignEffectiveControlDrr`, `ShopHeadroomState`, `BoundedCpoProposal`, `report.decision`, `reason_codes`, `blockers` | Recomputable; headroom/CPO proposal not user settings. |

`ProductCpoResolver` → `DerivedCpoRub` is **catalog-price derived** (`product_control`); ADR forbids substituting it for V1 campaign `TARGET_CPO_RUB` in hierarchical control.

---

## 5. Resolver / runtime entrypoints (diagnostics mode)

Production proposal path today is **pure domain** (no shop-runner service).

### `AdControlDiagnosticsBuilder`

```python
@staticmethod
def build(
    context: ResolverContext,
    actual_drr: ActualDrrObservation | None,
    *,
    current_max_cpo_rub: Decimal | None = None,
    allowed_spend_rub: Decimal | None = None,
    spend_rub: Decimal | None = None,
    dry_run_diff_available: bool = False,
) -> AdControlDiagnosticsReportV1
```

Path: `app/modules/ad_control_settings/domain/diagnostics_builder.py`

### `AdControlSettingsResolver`

```python
@staticmethod
def assert_hierarchical_path(context: ResolverContext) -> ResolverBlocked | None

@staticmethod
def resolve_feature(context: ResolverContext, feature_id: AdControlFeatureId) -> ResolvedFeaturePolicy | ResolverBlocked

@staticmethod
def resolve_configured_target_drr(context: ResolverContext) -> DrrPolicyParamsV1 | ResolverBlocked
```

Path: `app/modules/ad_control_settings/domain/resolver.py`

### Headroom / gates (same semantics as diagnostics builder)

```python
def derive_shop_effective_control_drr(configured_target_percent: Decimal, dynamic_enabled: bool, actual: ActualDrrObservation) -> ShopEffectiveControlDrr
def evaluate_shop_headroom_state(configured_target_percent: Decimal, actual: ActualDrrObservation, allowed_spend_rub: Decimal | None, spend_rub: Decimal | None) -> ShopHeadroomState
def control_action_allowed(actual: ActualDrrObservation) -> tuple[bool, AdControlReasonCode]
def campaign_headroom_eligibility(campaign: CampaignRef, actual: ActualDrrObservation, *, enrollment, control_path, hierarchical_resolver_available: bool) -> CampaignHeadroomEligibility
```

Path: `app/modules/ad_control_settings/domain/headroom_eval.py`

### Persistence → resolver context (async)

```python
async def load_resolver_shop_features(repository: AdControlSettingsRepository, shop_id: str) -> dict[AdControlFeatureId, ShopFeatureSlot]
async def load_resolver_campaign_features(repository: AdControlSettingsRepository, campaign: CampaignRef) -> dict[AdControlFeatureId, CampaignFeatureSlot]
```

Path: `app/modules/ad_control_settings/persistence/context_loader.py`

### Product tier (parallel resolver)

```python
EffectiveControlResolver.resolve(settings: EffectiveControlInput) -> EffectiveControlResult
ProductDrrPolicyAdapter.from_effective_control(effective: EffectiveControlResult) -> ProductDrrPolicyAdapterResult
```

Paths: `product_control/domain/effective_control_resolver.py`, `ad_control_settings/domain/product_adapter.py`

### ChangeSet dry-run (test mode writes preview)

```python
def validate_ad_control_changeset(
    changeset: AdControlChangeSetV1,
    *,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[tuple[str, int, AdControlFeatureId], AdControlCampaignFeatureSnapshotV1],
) -> AdControlValidationResult
```

Path: `app/modules/wb_sky_control_plane/kernel/ad_control_validate.py`

**No** `app/modules/shop_runner` references to `ad_control` / `AdControl` (grep empty).

---

## 6. Task 4.1 vs 4.2 (quoted from `tasks.md`)

```markdown
- [ ] 4.1 Runtime shop-runner integration
- [ ] 4.2 UI Advertising Control + Diagnostics
```

No further sub-bullets exist in-tree for 4.1 or 4.2.

### Already in tree (Slices A–B + tests)

- Domain: registry, resolver, DRR triple types, headroom, `AdControlDiagnosticsReportV1`, reason codes.
- Persistence: PG models, repository CAS, payload codec, context loader.
- Control plane: `AdControlChangeSetV1`, `validate_ad_control_changeset`, semantic diffs.
- Tests: `tests/unit/ad_control_settings/*`, `tests/unit/wb_sky_control_plane/test_ad_control_*`, integration PG persistence tests.

### NOT in tree (expected under 4.1 / 4.2 / ADR, not implemented)

- Shop-runner integration feeding `ResolverContext` + `ActualDrrObservation` + spend/GMV ports.
- Runtime factual adapters for campaign `campaign_actual_drr`, DIRECT aggregates, shop `whole_shop_order_gmv_rub`.
- UI/API/MCP/Excel transport for Advertising Control.
- `CampaignHeadroomEligibility` (and per-campaign economics) on diagnostics report.
- V1 order-value `TARGET_CPO_RUB` proposal math (only blocked placeholder `BoundedCpoProposal`).
- ADR §9 blocker tokens as Python enums (`DIRECT_ATTRIBUTION_MISSING`, etc.) — **documentation only** today.
- Apply Authority wiring for ad control mutations (explicitly out of Slice B).

Owner-contract diagnostics quote:

> Mandatory future UI: Advertising Control + Diagnostics/Test using same resolver; no writes.

---

## 7. Dry-run diff shape

**Not a dataclass** — Pydantic `BaseModel` `AdControlSemanticDiffV1`:

| Field | Type |
|-------|------|
| `target_key` | `str` |
| `intent` | `AdControlMutationKind` |
| `field_path` | `str` |
| `current` | `str \| None` |
| `desired` | `str \| None` |
| `effective_source_after` | `str \| None` |

Wrapped in `AdControlValidationResult`: `status: DryRunStatus`, `changeset_id: str`, `semantic_digest: str`, `errors: list[ControlPlaneError]`, `diffs: list[AdControlSemanticDiffV1]`.

`AdControlMutationKind` (`app/modules/ad_control_settings/persistence/cas.py`): `CREATE`, `UPDATE`, `DISABLE`, `CLEAR_TO_INHERIT`, `NO_OP`.

Dry-run errors use `ControlPlaneError.code: str` (e.g. `"REVISION_CONFLICT"`), not `AdControlReasonCode`.

---

## 8. Blocker / reason enums

### `AdControlReasonCode` (`ad_control_settings/domain/reason_codes.py`)

`OK`, `NOT_ENROLLED_FAIL_CLOSED`, `LEGACY_PASSTHROUGH_ACTIVE`, `FEATURE_DISABLED_AT_CAMPAIGN`, `FEATURE_DISABLED_AT_SHOP`, `FEATURE_DISABLED_AT_PRODUCT`, `UNSUPPORTED_SCOPE_FOR_FEATURE`, `UNKNOWN_FEATURE`, `INVALID_CONFIGURATION`, `SHOP_ENABLED_MISSING_PAYLOAD`, `ACTUAL_DRR_STALE`, `ACTUAL_DRR_INSUFFICIENT`, `ACTUAL_DRR_UNSUPPORTED`, `MEASUREMENT_UNKNOWN`, `NO_CONTROL_ACTION_STALE_OR_UNKNOWN`, `HEADROOM_ALLOCATOR_NOT_ACCEPTED`, `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`, `PRODUCT_DRR_ADAPTER_BLOCKED`.

### Report `blockers`

`tuple[str, ...]` — **no enum** (examples: `hierarchical_automation_not_enrolled`, `legacy_passthrough`, `no_control_action`, `hierarchical_resolver_blocked`, `drr_policy_inactive`, `campaign_override_missing_payload:…`).

### `DataSufficiency` / `MinObservedDataSufficiencyRequirement`

Observation gates for control action and CPO policy params.

### `AttributionReasonCode` (attribution_facts — for future campaign economics UI)

Separate from ad control; used in attribution domain/tests, not wired to diagnostics report.

### `ProductControlBlockerReason`

Product/CPO catalog path only (`product_control/domain/enums.py`).

### ADR §9 CPO blockers (`drr-cpo-price-semantics/decision.md`)

Documented string tokens only (`DIRECT_ATTRIBUTION_MISSING`, `ORDER_VALUE_UNAVAILABLE`, …) — **MISSING_DOMAIN_SYMBOL** as Python enum.

---

## 9. Test fixtures referencing these facts

| File | What it fixtures |
|------|------------------|
| `tests/unit/ad_control_settings/test_diagnostics_configured_state.py` | Configured vs effective, INHERIT no override payload, disabled campaign |
| `tests/unit/ad_control_settings/test_registry_and_headroom.py` | Stale DRR gate, CPO proposal blocked, headroom |
| `tests/unit/ad_control_settings/test_precedence_product_shop.py` | Product→shop fall-through, legacy passthrough eligibility |
| `tests/unit/ad_control_settings/test_resolver_drr_inheritance.py` | Live shop inherit |
| `tests/unit/wb_sky_control_plane/test_ad_control_changeset_validate.py` | Dry-run validation |
| `tests/unit/attribution_facts/*`, `tests/unit/ai_package_v1/analysis/test_attribution_economics_matrix.py` | `DRR_FACT_DIRECT`, attribution metrics (not ad_control diagnostics) |

---

## 10. Spec quotes (4.2-related wording in change spec — do not extend)

From `specs/hierarchical-ad-control-settings/spec.md`:

> When `actual_drr` data sufficiency is not `SUFFICIENT`, the controller MUST NOT emit new control actions from hierarchical evidence.

> Slice A catalog-price CPO diagnostics MUST remain fail-closed while `CATALOG_PRICE_SEMANTICS_ACCEPTED = NO`.

> `validate_ad_control_changeset` without PostgreSQL or WB writes.
