---
cursor:
  subagentId: "bc-ab5b6195-2881-5695-99a9-8bdd25249475"
---

# Slice A/B domain archaeology (ad_control_settings + attribution_facts)

Read-only inventory at `/agent/repos/adv-bot` for Task 4.1 runtime port+provider wiring.

## Naming note

**`ShopEconomicControlState` does not exist** in the repo. Closest types:

| User name (concept) | Actual type | Module |
|---------------------|-------------|--------|
| Shop economic / control DRR (derived) | `ShopEffectiveControlDrr` | `drr_state.py` |
| Shop headroom (derived) | `ShopHeadroomState` | `headroom.py` |
| Campaign effective control DRR | `CampaignEffectiveControlDrr` | `drr_state.py` |

---

## 1. Types to MUST reuse (no parallel DTOs)

### `app/modules/ad_control_settings/domain/`

#### `enums.py` — all `StrEnum`

- `AdControlScope`: `SHOP`, `PRODUCT`, `CAMPAIGN`, `SYSTEM_LEGACY`
- `AdControlFeatureId`: `DRR_POLICY`, `DYNAMIC_DRR_CONTROL`, `CPO_INCREASE_ON_HEADROOM`, `CPO_DECREASE_ON_OVERSPEND`, `CPO_SAFETY_BOUNDS`
- `AdControlFeatureMode`: `INHERIT`, `OVERRIDE`, `DISABLED`
- `ShopFeatureActivation`: `ENABLED`, `DISABLED`
- `ControlPathKind`: `HIERARCHICAL`, `LEGACY_PASSTHROUGH`
- `HierarchicalEnrollment`: `NOT_ENROLLED`, `ENROLLED`
- `DataSufficiency`: `SUFFICIENT`, `INSUFFICIENT`, `STALE`, `UNSUPPORTED`, `UNKNOWN`
- `EffectiveSourceKind`: `CAMPAIGN_OVERRIDE`, `CAMPAIGN_DISABLED`, `PRODUCT_OVERRIDE`, `PRODUCT_DISABLED`, `SHOP_POLICY`, `SHOP_DISABLED`, `SYSTEM_LEGACY_DEFAULT`, `LEGACY_PASSTHROUGH`, `NOT_APPLICABLE`

#### `reason_codes.py` — `AdControlReasonCode(StrEnum)`

Members (add new codes here; see § AdControlReasonCode pattern):

`OK`, `NOT_ENROLLED_FAIL_CLOSED`, `LEGACY_PASSTHROUGH_ACTIVE`, `FEATURE_DISABLED_AT_CAMPAIGN`, `FEATURE_DISABLED_AT_SHOP`, `FEATURE_DISABLED_AT_PRODUCT`, `UNSUPPORTED_SCOPE_FOR_FEATURE`, `UNKNOWN_FEATURE`, `INVALID_CONFIGURATION`, `SHOP_ENABLED_MISSING_PAYLOAD`, `ACTUAL_DRR_STALE`, `ACTUAL_DRR_INSUFFICIENT`, `ACTUAL_DRR_UNSUPPORTED`, `MEASUREMENT_UNKNOWN`, `NO_CONTROL_ACTION_STALE_OR_UNKNOWN`, `HEADROOM_ALLOCATOR_NOT_ACCEPTED`, `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`, `PRODUCT_DRR_ADAPTER_BLOCKED`

(`HEADROOM_ALLOCATOR_NOT_ACCEPTED` is defined but **unused** in production code paths today.)

#### `campaign_ref.py`

```python
@dataclass(frozen=True, slots=True)
class CampaignRef:
    shop_id: str
    advert_id: int
```

#### `provenance.py`

```python
@dataclass(frozen=True, slots=True)
class ProvenanceEntry:
    feature_id: AdControlFeatureId
    source_kind: EffectiveSourceKind
    source_scope: AdControlScope
    schema_version: int
```

#### `configured.py` — configured payloads (union `ConfiguredFeaturePayload`)

- `DrrPolicyParamsV1`: `profile: DrrProfile`, `schema_version: int = 1` (reuses `app.modules.product_control.domain.models.DrrProfile`)
- `DynamicDrrControlParamsV1`: `enabled: bool`, `max_effective_delta_percent: Decimal`, `schema_version: int = 1`
- `CpoIncreaseOnHeadroomParamsV1`: `minimum_headroom_rub`, `maximum_increase_per_iteration_rub`, `cooldown_ticks`, `min_data_sufficiency: MinObservedDataSufficiencyRequirement`, `schema_version: int = 1`
- `CpoDecreaseOnOverspendParamsV1`: `maximum_decrease_per_iteration_rub`, `cooldown_ticks`, `min_data_sufficiency`, `schema_version: int = 1`
- `CpoSafetyBoundsParamsV1`: `absolute_min_cpo_rub`, `absolute_max_cpo_rub`, `max_step_up_rub`, `max_step_down_rub` (all `Decimal | None`), `schema_version: int = 1`

#### `min_data_sufficiency.py`

- `MinObservedDataSufficiencyRequirement(StrEnum)`: only `SUFFICIENT` in V1
- `validate_min_observed_requirement(value) -> None`

#### `drr_state.py`

```python
@dataclass(frozen=True, slots=True)
class ConfiguredTargetDrr:
    target_drr_percent: Decimal
    max_drr_percent: Decimal
    provenance: ProvenanceEntry

@dataclass(frozen=True, slots=True)
class ActualDrrObservation:
    actual_drr_percent: Decimal | None
    measurement_window_id: str
    data_sufficiency: DataSufficiency
    attribution_lag_days: int | None

@dataclass(frozen=True, slots=True)
class ShopEffectiveControlDrr:
    effective_control_drr_percent: Decimal | None
    derived_from_configured: bool

@dataclass(frozen=True, slots=True)
class CampaignEffectiveControlDrr:
    effective_control_drr_percent: Decimal | None
    inherits_shop_control: bool
    provenance: ProvenanceEntry
```

#### `headroom.py`

```python
@dataclass(frozen=True, slots=True)
class ShopHeadroomState:
    configured_target_drr_percent: Decimal
    actual_drr_percent: Decimal | None
    headroom_rub: Decimal | None
    control_pressure: Decimal | None

@dataclass(frozen=True, slots=True)
class CampaignHeadroomEligibility:
    campaign: CampaignRef
    eligible: bool
    reason_codes: tuple[AdControlReasonCode, ...]
    blockers: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class BoundedCpoProposal:
    campaign: CampaignRef
    current_max_cpo_rub: Decimal | None
    proposed_max_cpo_rub: Decimal | None
    decision: str
    reason_codes: tuple[AdControlReasonCode, ...]

class HeadroomAllocator(Protocol):
    def propose_bounded_adjustments(
        self,
        shop_headroom: ShopHeadroomState,
        eligible_campaigns: tuple[CampaignHeadroomEligibility, ...],
    ) -> tuple[BoundedCpoProposal, ...]: ...
```

#### `resolver_models.py`

```python
@dataclass(frozen=True, slots=True)
class ShopFeatureSlot:
    activation: ShopFeatureActivation
    payload: ConfiguredFeaturePayload | None

@dataclass(frozen=True, slots=True)
class CampaignFeatureSlot:
    mode: AdControlFeatureMode
    payload: ConfiguredFeaturePayload | None

@dataclass(frozen=True, slots=True)
class ResolverContext:
    enrollment: HierarchicalEnrollment
    control_path: ControlPathKind
    shop_id: str
    shop_features: Mapping[AdControlFeatureId, ShopFeatureSlot]
    campaign: CampaignRef
    campaign_features: Mapping[AdControlFeatureId, CampaignFeatureSlot]
    product_drr: ProductDrrPolicyAdapterResult | None = None

@dataclass(frozen=True, slots=True)
class ResolvedFeaturePolicy:
    feature_id: AdControlFeatureId
    active: bool
    payload: ConfiguredFeaturePayload | None
    provenance: ProvenanceEntry
    reason_codes: tuple[AdControlReasonCode, ...]

@dataclass(frozen=True, slots=True)
class ResolverBlocked:
    reason_codes: tuple[AdControlReasonCode, ...]
    blockers: tuple[str, ...]
```

#### `configured_state.py`

```python
@dataclass(frozen=True, slots=True)
class ConfiguredShopFeatureState:
    feature_id: AdControlFeatureId
    scope: AdControlScope
    activation: ShopFeatureActivation
    payload: ConfiguredFeaturePayload | None
    schema_version: int | None

@dataclass(frozen=True, slots=True)
class ConfiguredCampaignFeatureState:
    feature_id: AdControlFeatureId
    scope: AdControlScope
    mode: AdControlFeatureMode
    override_payload: ConfiguredFeaturePayload | None
    schema_version: int | None
```

Projectors: `project_configured_shop_features(context)`, `project_configured_campaign_features(context)`.

#### `diagnostics.py`

```python
@dataclass(frozen=True, slots=True)
class AdControlDiagnosticsReportV1:
    shop_id: str
    campaign: CampaignRef | None
    configured_shop_features: tuple[ConfiguredShopFeatureState, ...]
    configured_campaign_overrides: tuple[ConfiguredCampaignFeatureState, ...]
    effective_features: tuple[ResolvedFeaturePolicy, ...]
    configured_target_drr: ConfiguredTargetDrr | None
    actual_drr: ActualDrrObservation | None
    shop_effective_control_drr: ShopEffectiveControlDrr | None
    campaign_effective_control_drr: CampaignEffectiveControlDrr | None
    shop_headroom: ShopHeadroomState | None
    current_max_cpo_rub: Decimal | None
    proposed_cpo: BoundedCpoProposal | None
    decision: str
    reason_codes: tuple[AdControlReasonCode, ...]
    blockers: tuple[str, ...]
    dry_run_diff_available: bool
    provenance_index: tuple[ProvenanceEntry, ...]
```

#### `product_adapter.py`

- `ProductDrrPolicyAdapterSuccess`: `params: DrrPolicyParamsV1`, `provenance: ProvenanceEntry`
- `ProductDrrPolicyAdapterBlocked`: `reason: AdControlReasonCode`
- `ProductDrrPolicyAdapter.from_effective_control(effective: EffectiveControlResult) -> ProductDrrPolicyAdapterResult`

#### `registry.py`

- `FeatureDefinition`, `FEATURE_REGISTRY`, `get_feature_definition`, `assert_scope_supported`, `validate_feature_payload`, `configuration_identity`
- `FeatureValidationError(ValueError)`

#### Pure APIs

| Class / module | Public callables |
|----------------|------------------|
| `AdControlSettingsResolver` (`resolver.py`) | `assert_hierarchical_path(context) -> ResolverBlocked \| None`, `resolve_feature(context, feature_id) -> ResolvedFeaturePolicy \| ResolverBlocked`, `resolve_configured_target_drr(context) -> DrrPolicyParamsV1 \| ResolverBlocked`, `_resolve_product_tier` (private) |
| `headroom_eval.py` | `derive_shop_effective_control_drr`, `evaluate_shop_headroom_state`, `control_action_allowed`, `campaign_headroom_eligibility` |
| `AdControlDiagnosticsBuilder` (`diagnostics_builder.py`) | `build(context, actual_drr, *, current_max_cpo_rub, allowed_spend_rub, spend_rub, dry_run_diff_available) -> AdControlDiagnosticsReportV1` |

### `app/modules/attribution_facts/` (reuse for facts, not re-wrap)

#### `domain/enums.py`

- `AttributionClass`: `DIRECT`, `LINKED`, `UNKNOWN`, `UNATTRIBUTED`, `UNSUPPORTED`
- `AttributionCoverageStatus`: `COMPLETE`, `PARTIAL`, `NO_DATA`, `UNSUPPORTED`, `UNKNOWN`
- `AttributionReasonCode`: (10 members — source partial/missing, relation unknown, reconciliation, denominator zero, blocked, etc.)
- `SourceFamily`: `WB_PROMOTION_FULLSTATS_NM_DAY`

#### `domain/models.py` (key types)

- `AttributionFactKey`: `shop_id`, `physical_adv_id`, `event_date`, `app_type`, `ordered_nm_id`, `source_family`
- `AttributionMetrics`: `attributed_orders`, `attributed_gmv_rub`, `attributed_atc`, `attributed_units_shks` (all optional)
- `AttributionCommerceFact`: `key`, `metrics`, `attribution_class`, `provenance`, `reconciliation_pass`
- `DateWindow`: `start: date`, `end: date` (inclusive)
- `AttributionScope`: `shop_id`, `physical_adv_ids: frozenset[int]`, `allow_pair_aggregate: Literal[False]`
- `AttributionQueryResult`: `facts`, `coverage`, `reconciliations`
- `AttributionCoverage`: `status`, `reason_codes`, `source_complete_through`, `effective_covered_range_start/end`, `package_cutoff_date`
- `CampaignDaySpendReference`: `physical_adv_id`, `event_date`, `spend_rub`
- `DerivedFactEconomics`: `metric_name`, `value: Decimal | None`, `reason_codes`

#### `ports/reader.py`

```python
class AttributionFactsReader(Protocol):
    async def query(
        self,
        scope: AttributionScope,
        window: DateWindow,
    ) -> AttributionQueryResult: ...
```

#### `testing/in_memory_reader.py`

`InMemoryAttributionFactsReader` — same `async def query(scope, window) -> AttributionQueryResult`.

#### `domain/derived_metrics.py`

- `compute_cpo_fact(metric_name, facts, spend_refs, attr_class, coverage) -> DerivedFactEconomics`
- `compute_drr_fact(metric_name, facts, spend_refs, attr_class, coverage) -> DerivedFactEconomics`

#### `domain/coverage.py`

- `evaluate_window_coverage(...) -> AttributionCoverage`
- `can_emit_direct_linked_economics(coverage) -> bool` (only `COMPLETE`)
- `package_cutoff_does_not_imply_complete(...)`, `all_reconciliations_passed(...)`

#### `domain/classification.py`

- `classify_ordered_nm(ordered_nm_id, snapshot) -> AttributionClass`
- `classify_fact_row(ordered_nm_id, snapshot, *, unsupported_metric=False) -> AttributionClass`

### Persistence (slot shapes already aligned with resolver)

Reuse `ShopFeatureSlot`, `CampaignFeatureSlot` from `resolver_models` — loaded via repository, not redefined.

---

## 2. Gaps (must add for Task 4.1 — not in codebase yet)

| Gap | Evidence |
|-----|----------|
| **Runtime port** bridging attribution + supplier orders → `ActualDrrObservation` | No module under `ad_control_settings` reads `AttributionFactsReader` or maps `AttributionCoverage` → `DataSufficiency` |
| **Shop GMV aggregate** (`whole_shop_order_gmv_rub`) | Decision `drr-cpo-price-semantics` §3 requires `ORDERS_OR_SALES_REPORTS_READ`; no domain type or reader port in repo for shop-order GMV window aggregate |
| **Shop spend window** (total shop ad spend for same window) | `evaluate_shop_headroom_state` accepts `spend_rub` / `allowed_spend_rub` as caller-supplied scalars; no typed “shop spend window” fact DTO |
| **`allowed_spend_rub` derivation** | Headroom rub = `allowed_spend_rub - spend_rub` but nothing computes allowed spend from target DRR × shop GMV |
| **Campaign order-value / expected attributed order value** | Decision: `EXPECTED_ATTRIBUTED_ORDER_VALUE_RUB = DIRECT GMV / DIRECT orders`; `compute_cpo_fact` gives spend/orders CPO, not a dedicated “order value” type; no `ExpectedAttributedOrderValueRub` in ad_control_settings |
| **Campaign actual DRR from facts** | Use `compute_drr_fact(..., AttributionClass.DIRECT, ...)` + map to `ActualDrrObservation` at campaign scope — mapper absent |
| **Measurement window identity** | `ActualDrrObservation.measurement_window_id: str` is opaque; no shared `DateWindow` ↔ id codec in ad_control_settings |
| **Price semantics accepted path** | ADR accepts V1 order-value semantics; `diagnostics_builder` still always emits blocked CPO (foundation placeholder) |

Do **not** invent parallel types for anything in §1; add only ports/adapters/mappers and any **new** fact aggregates explicitly required by ADR (shop GMV window, optional thin wrappers if needed).

---

## 3. Exact function signatures (headroom + diagnostics)

### Headroom / gates (`headroom_eval.py`)

```python
def derive_shop_effective_control_drr(
    configured_target_percent: Decimal,
    dynamic_enabled: bool,
    actual: ActualDrrObservation,
) -> ShopEffectiveControlDrr: ...

def evaluate_shop_headroom_state(
    configured_target_percent: Decimal,
    actual: ActualDrrObservation,
    allowed_spend_rub: Decimal | None,
    spend_rub: Decimal | None,
) -> ShopHeadroomState: ...

def control_action_allowed(
    actual: ActualDrrObservation,
) -> tuple[bool, AdControlReasonCode]: ...

def campaign_headroom_eligibility(
    campaign: CampaignRef,
    actual: ActualDrrObservation,
    *,
    enrollment: HierarchicalEnrollment,
    control_path: ControlPathKind,
    hierarchical_resolver_available: bool,
) -> CampaignHeadroomEligibility: ...
```

### Diagnostics (`diagnostics_builder.py`)

```python
class AdControlDiagnosticsBuilder:
    @staticmethod
    def build(
        context: ResolverContext,
        actual_drr: ActualDrrObservation | None,
        *,
        current_max_cpo_rub: Decimal | None = None,
        allowed_spend_rub: Decimal | None = None,
        spend_rub: Decimal | None = None,
        dry_run_diff_available: bool = False,
    ) -> AdControlDiagnosticsReportV1: ...
```

Internal call chain when `configured_target` and `actual_drr` both set:

1. `derive_shop_effective_control_drr(...)`
2. `evaluate_shop_headroom_state(...)`
3. `control_action_allowed(actual_drr)`
4. `AdControlSettingsResolver.assert_hierarchical_path(context)`
5. `campaign_headroom_eligibility(...)`
6. Builds `BoundedCpoProposal` (see §4)

### Attribution derived metrics (for provider implementation)

```python
def compute_drr_fact(
    metric_name: str,
    facts: tuple[AttributionCommerceFact, ...],
    spend_refs: tuple[CampaignDaySpendReference, ...],
    attr_class: AttributionClass,
    coverage: AttributionCoverage,
) -> DerivedFactEconomics: ...

def compute_cpo_fact(
    metric_name: str,
    facts: tuple[AttributionCommerceFact, ...],
    spend_refs: tuple[CampaignDaySpendReference, ...],
    attr_class: AttributionClass,
    coverage: AttributionCoverage,
) -> DerivedFactEconomics: ...
```

### Resolver (configured only)

```python
AdControlSettingsResolver.resolve_feature(context, feature_id)
AdControlSettingsResolver.resolve_configured_target_drr(context)
AdControlSettingsResolver.assert_hierarchical_path(context)
```

### Persistence load (async)

```python
async def load_resolver_shop_features(repository, shop_id) -> dict[AdControlFeatureId, ShopFeatureSlot]
async def load_resolver_campaign_features(repository, campaign) -> dict[AdControlFeatureId, CampaignFeatureSlot]

class AdControlSettingsRepository:
    async def load_shop_slots(shop_id) -> dict[AdControlFeatureId, ShopFeatureSlot]
    async def load_campaign_slots(campaign) -> dict[AdControlFeatureId, CampaignFeatureSlot]
    # ... mutations: apply_shop_mutation, apply_campaign_override, apply_campaign_disable, clear_campaign_feature
```

---

## 4. PRICE_SEMANTICS enforcement in `diagnostics_builder`

There is **no** runtime check of Owner ADR flags. When both `configured_target` and `actual_drr` are present, the builder **always** constructs:

- `BoundedCpoProposal` with `proposed_max_cpo_rub=None`
- `decision="NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED"`
- `reason_codes=(PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED,)`

This runs **unconditionally** after headroom/eligibility (not gated on price adapter or order-value computation). `BoundedCpoProposal` docstring in `headroom.py` states `proposed_max_cpo_rub` is allowed only when price semantics accepted — implementation is fail-closed stub until Task 4.1+ wires accepted semantics.

Related: `test_diagnostics_no_cpo_proposal_without_price_semantics` in `test_registry_and_headroom.py` asserts this behavior even when `data_sufficiency=SUFFICIENT`.

---

## 5. `AdControlReasonCode` — enum and extension pattern

- **Yes**: `class AdControlReasonCode(StrEnum)` in `reason_codes.py`.
- **Add a member**: new string token on the class (Pascal-case value matching name is the convention).
- **Use**: diagnostics `reason_codes`, `ResolverBlocked`, `ResolvedFeaturePolicy.reason_codes`, eligibility/proposals.
- **Registry**: CPO features do not auto-register reason codes; only `FEATURE_REGISTRY` validates payloads.
- **Tests**: extend assertions in existing ad_control_settings unit tests when adding codes.

Separate enum: `AttributionReasonCode` in attribution_facts (do not merge with ad control).

---

## 6. `openspec/decisions/orders-or-sales-reports-read-identity` — completeness rules (summary)

**Identity**

- Family `ORDERS_OR_SALES_REPORTS_READ` = **only** statistics-api `GET /api/v1/supplier/orders` and/or `GET /api/v1/supplier/sales` on `statistics-api.wildberries.ru` (swagger `12-reports`), via `app/core/mp/wb/api`.

**Period honesty**

- Period = `dateFrom` + cursor `lastChangeDate`; **must not** claim classic exact `start+end` if API has no end param.
- Stage A preflight: one first-page GET with `dateFrom` at window start; `next_page_followed=NO`.
- Attestation model `DATE_FROM` / cursor; `REFUSED` / `REQUIRED_PERIOD_UNSUPPORTED` when COL-R03 asks for impossible period.

**Forbidden as substitute**

- Sales funnel, search-report product orders, promotion fullstats `orders`, FBS assembly orders, finance sales-reports, invented URLs, silent yesterday→today period, pagination in Stage A disguised as single page.

**Allowed**

- Narrow generated client surface (orders/sales only), unit tests with mocks.

For shop DRR denominator (ADR §3), this family is the **required** source of `whole_shop_order_gmv_rub` — not yet modeled in Python domain types.

---

## 7. Test files to extend (not fork)

### `tests/unit/ad_control_settings/`

| File | Focus |
|------|--------|
| `test_registry_and_headroom.py` | Registry, `control_action_allowed`, headroom gates, **diagnostics CPO blocked** |
| `test_diagnostics_configured_state.py` | `AdControlDiagnosticsBuilder`, configured projection, blocked paths |
| `test_resolver_drr_inheritance.py` | Resolver inheritance, reason codes |
| `test_precedence_product_shop.py` | Product vs shop precedence + headroom eligibility |
| `test_product_adapter.py` | Product DRR adapter |
| `test_payload_codec.py` | Persistence codec |
| `test_persistence_validation.py` | Repository validation |

### `tests/integration/ad_control_settings/`

- `test_persistence_live_pg.py`, `conftest.py`

### `tests/unit/attribution_facts/` (for provider mapping tests)

| File | Focus |
|------|--------|
| `test_reconciliation_and_coverage.py` | `compute_drr_fact`, coverage gates |
| `test_slice_a_scenario_evidence.py` | End-to-end slice A scenarios |
| `test_in_memory_reader.py` | `InMemoryAttributionFactsReader` |
| `test_classification.py` | DIRECT vs LINKED |
| Others | ingest, membership, reconciliation grid |

**Suggested extension points for Task 4.1**

- New tests colocated: `tests/unit/ad_control_settings/test_economic_facts_port.py` (or similar) **or** extend `test_diagnostics_configured_state.py` / `test_registry_and_headroom.py` once provider feeds real `ActualDrrObservation` and optionally unblocks CPO proposal path.

---

## 8. Slice A/B boundary (implementation hint)

- **Slice A (domain)**: everything under `ad_control_settings/domain/` + `attribution_facts/domain|ports|testing` — pure, no I/O.
- **Slice B (persistence)**: `ad_control_settings/persistence/` — PG slots only; **no** economic facts.
- **Task 4.1 port+provider**: likely `ad_control_settings/application/` or `ports/` (not present yet) implementing read adapters that **produce** `ActualDrrObservation`, `CampaignDaySpendReference` tuples, and shop-level scalars for `AdControlDiagnosticsBuilder.build(...)`.

---

## 9. `DataSufficiency` vs attribution coverage (mapper gap)

`ActualDrrObservation.data_sufficiency` uses ad-control enum. Attribution uses `AttributionCoverageStatus`. **No canonical mapper** exists today. Provider must define deterministic mapping (e.g. `COMPLETE` + gates → `SUFFICIENT`; `PARTIAL`/`NO_DATA` → `INSUFFICIENT` or `STALE`; fail-closed on `UNKNOWN`) consistent with `drr-cpo-price-semantics` §9 and `control_action_allowed`.
