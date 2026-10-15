---
cursor:
  subagentId: "bc-8ea5e1aa-0ab9-5eb0-8de8-c1e1ae65e1e5"
---

# Telegram UI — Slice A/B read-only symbol map (no economics)

**Repo:** `/agent/repos/adv-bot` @ `stage` (read-only survey).  
**Scope:** configured/effective ad-control state + `validate_ad_control_changeset` dry-run only.  
**Related:** [hierarchical-ad-control-slice-ab-type-map](../architecture/hierarchical-ad-control-slice-ab-type-map-bc-ab9bf4d3.md).

---

## 1. Feature registry

| Symbol | Path |
|--------|------|
| `FEATURE_REGISTRY` | `app/modules/ad_control_settings/domain/registry.py` |
| `FeatureDefinition` | same |
| `AdControlFeatureId` | `app/modules/ad_control_settings/domain/enums.py` |
| `AdControlScope` | same |
| Payload types | `app/modules/ad_control_settings/domain/configured.py` |
| `get_feature_definition`, `validate_feature_payload`, `assert_scope_supported` | `registry.py` |

```python
class AdControlFeatureId(StrEnum):
    DRR_POLICY = "DRR_POLICY"
    DYNAMIC_DRR_CONTROL = "DYNAMIC_DRR_CONTROL"
    CPO_INCREASE_ON_HEADROOM = "CPO_INCREASE_ON_HEADROOM"
    CPO_DECREASE_ON_OVERSPEND = "CPO_DECREASE_ON_OVERSPEND"
    CPO_SAFETY_BOUNDS = "CPO_SAFETY_BOUNDS"
```

```python
@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    feature_id: AdControlFeatureId
    schema_version: int
    supported_scopes: frozenset[AdControlScope]
    validate_payload: Callable[[ConfiguredFeaturePayload], None]
```

**Registry rows (all `schema_version=1` today):**

| `AdControlFeatureId` | Payload type | `supported_scopes` |
|----------------------|--------------|----------------------|
| `DRR_POLICY` | `DrrPolicyParamsV1` | SHOP, CAMPAIGN, PRODUCT |
| `DYNAMIC_DRR_CONTROL` | `DynamicDrrControlParamsV1` | SHOP, CAMPAIGN |
| `CPO_INCREASE_ON_HEADROOM` | `CpoIncreaseOnHeadroomParamsV1` | SHOP, CAMPAIGN |
| `CPO_DECREASE_ON_OVERSPEND` | `CpoDecreaseOnOverspendParamsV1` | SHOP, CAMPAIGN |
| `CPO_SAFETY_BOUNDS` | `CpoSafetyBoundsParamsV1` | SHOP, CAMPAIGN |

**Payload field shapes (UI forms / codec):**

- `DrrPolicyParamsV1`: `profile: DrrProfile` (`target_drr_percent`, `max_drr_percent` as `Decimal`), `schema_version: int = 1`
- `DynamicDrrControlParamsV1`: `enabled: bool`, `max_effective_delta_percent: Decimal`, `schema_version: int = 1`
- `CpoIncreaseOnHeadroomParamsV1`: `minimum_headroom_rub`, `maximum_increase_per_iteration_rub`, `cooldown_ticks`, `min_data_sufficiency: MinObservedDataSufficiencyRequirement` (V1: `SUFFICIENT` only), `schema_version: int = 1`
- `CpoDecreaseOnOverspendParamsV1`: `maximum_decrease_per_iteration_rub`, `cooldown_ticks`, `min_data_sufficiency`, `schema_version: int = 1`
- `CpoSafetyBoundsParamsV1`: optional `absolute_min_cpo_rub`, `absolute_max_cpo_rub`, `max_step_up_rub`, `max_step_down_rub` (`Decimal | None`), `schema_version: int = 1`

**Human label:** no `display_name` / i18n in `FeatureDefinition`. UI should render `feature_id.value` (e.g. `DRR_POLICY`) or maintain its own map.

**UI must pass `schema_version`** matching `FeatureDefinition.schema_version` (always `1` for all V1 features) on ChangeSet bodies and upsert-shaped validation.

---

## 2. Shop configured

| Symbol | Path |
|--------|------|
| `ShopFeatureSlot` | `domain/resolver_models.py` |
| `ConfiguredShopFeatureState` | `domain/configured_state.py` |
| `project_configured_shop_features` | `domain/configured_state.py` |
| `ShopFeatureActivation` | `domain/enums.py` |

```python
@dataclass(frozen=True, slots=True)
class ShopFeatureSlot:
    activation: ShopFeatureActivation
    payload: ConfiguredFeaturePayload | None
```

```python
class ShopFeatureActivation(StrEnum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
```

```python
@dataclass(frozen=True, slots=True)
class ConfiguredShopFeatureState:
    feature_id: AdControlFeatureId
    scope: AdControlScope  # always SHOP in projection
    activation: ShopFeatureActivation
    payload: ConfiguredFeaturePayload | None
    schema_version: int | None  # from payload when present
```

```python
def project_configured_shop_features(
    context: ResolverContext,
) -> tuple[ConfiguredShopFeatureState, ...]:
```

**UI read:** build `ResolverContext.shop_features` (from PG via `load_shop_slots` or defaults), then call `project_configured_shop_features` for a full registry walk. Missing feature in map ⇒ projected as `DISABLED`, `payload=None`.

**UI write (ChangeSet only):** `ShopAdControlFeaturePayloadV1` — `feature_id`, `schema_version`, `activation`, `payload: dict | None` (`ENABLED` requires payload; `DISABLED` must have `payload=None` per `validate_shop_upsert`).

---

## 3. Campaign configured

| Symbol | Path |
|--------|------|
| `CampaignFeatureSlot` | `domain/resolver_models.py` |
| `ConfiguredCampaignFeatureState` | `domain/configured_state.py` |
| `project_configured_campaign_features` | `domain/configured_state.py` |
| `AdControlFeatureMode` | `domain/enums.py` |

```python
@dataclass(frozen=True, slots=True)
class CampaignFeatureSlot:
    mode: AdControlFeatureMode
    payload: ConfiguredFeaturePayload | None
```

```python
class AdControlFeatureMode(StrEnum):
    INHERIT = "INHERIT"
    OVERRIDE = "OVERRIDE"
    DISABLED = "DISABLED"
```

```python
@dataclass(frozen=True, slots=True)
class ConfiguredCampaignFeatureState:
    feature_id: AdControlFeatureId
    scope: AdControlScope  # CAMPAIGN
    mode: AdControlFeatureMode
    override_payload: ConfiguredFeaturePayload | None  # only if mode == OVERRIDE
    schema_version: int | None
```

**Missing PG row ⇒ INHERIT, payload None:** enforced in resolver (`CampaignFeatureSlot(mode=INHERIT, payload=None)` default) and in `project_configured_campaign_features` (same default). `load_campaign_slots` omits absent features; it never returns INHERIT rows (`PersistedInheritForbiddenError` if INHERIT stored).

---

## 4. Resolver

| Symbol | Path |
|--------|------|
| `AdControlSettingsResolver` | `domain/resolver.py` |
| `ResolverContext` | `domain/resolver_models.py` |
| `ResolvedFeaturePolicy` | `domain/resolver_models.py` |
| `ResolverBlocked` | `domain/resolver_models.py` |
| `ProvenanceEntry` | `domain/provenance.py` |
| `EffectiveSourceKind` | `domain/enums.py` |

```python
@dataclass(frozen=True, slots=True)
class ResolverContext:
    enrollment: HierarchicalEnrollment
    control_path: ControlPathKind
    shop_id: str
    shop_features: Mapping[AdControlFeatureId, ShopFeatureSlot]
    campaign: CampaignRef
    campaign_features: Mapping[AdControlFeatureId, CampaignFeatureSlot]
    product_drr: ProductDrrPolicyAdapterResult | None = None
```

```python
def resolve_feature(
    context: ResolverContext,
    feature_id: AdControlFeatureId,
) -> ResolvedFeaturePolicy | ResolverBlocked:
```

```python
@dataclass(frozen=True, slots=True)
class ResolvedFeaturePolicy:
    feature_id: AdControlFeatureId
    active: bool
    payload: ConfiguredFeaturePayload | None
    provenance: ProvenanceEntry
    reason_codes: tuple[AdControlReasonCode, ...]
```

```python
@dataclass(frozen=True, slots=True)
class ResolverBlocked:
    reason_codes: tuple[AdControlReasonCode, ...]
    blockers: tuple[str, ...]
```

```python
@dataclass(frozen=True, slots=True)
class ProvenanceEntry:
    feature_id: AdControlFeatureId
    source_kind: EffectiveSourceKind
    source_scope: AdControlScope
    schema_version: int
```

**`EffectiveSourceKind` (provenance):** `CAMPAIGN_OVERRIDE`, `CAMPAIGN_DISABLED`, `PRODUCT_OVERRIDE`, `PRODUCT_DISABLED`, `SHOP_POLICY`, `SHOP_DISABLED`, `SYSTEM_LEGACY_DEFAULT`, `LEGACY_PASSTHROUGH`, `NOT_APPLICABLE`.

**UI must supply for effective view:** `enrollment`, `control_path`, `shop_id`, shop + campaign slot maps, `CampaignRef`, optional `product_drr` (product tier only affects `DRR_POLICY` today). Fail-closed if `NOT_ENROLLED` or `LEGACY_PASSTHROUGH`.

---

## 5. Load slots from PG

| Symbol | Path |
|--------|------|
| `AdControlSettingsRepository` | `persistence/repository.py` |
| `load_resolver_shop_features` | `persistence/context_loader.py` |
| `load_resolver_campaign_features` | same |

```python
async def load_shop_slots(self, shop_id: str) -> dict[AdControlFeatureId, ShopFeatureSlot]:
```

```python
async def load_campaign_slots(
    self, campaign: CampaignRef,
) -> dict[AdControlFeatureId, CampaignFeatureSlot]:
```

**Returns:** domain slots only — **no `revision` / `state_token`** on these methods.

**CAS metadata for dry-run:** use row getters or ORM:

```python
async def get_shop_row(self, shop_id: str, feature_id: AdControlFeatureId) -> AdControlShopFeatureRow | None
async def get_campaign_row(self, campaign: CampaignRef, feature_id: AdControlFeatureId) -> AdControlCampaignFeatureRow | None
```

Helpers:

```python
def row_to_shop_snapshot(row: AdControlShopFeatureRow) -> tuple[
    ShopFeatureActivation, ConfiguredFeaturePayload | None, int, str,
]:  # activation, payload, revision, state_token

def row_to_campaign_snapshot(row: AdControlCampaignFeatureRow) -> tuple[
    AdControlFeatureMode, ConfiguredFeaturePayload | None, int, str, int,
]:  # mode, payload, revision, state_token, schema_version
```

**Dry-run snapshots** (`AdControlShopFeatureSnapshotV1` / `AdControlCampaignFeatureSnapshotV1` in `kernel/ad_control_validate.py`) are built from row fields in tests (`tests/unit/wb_sky_control_plane/test_ad_control_dry_run_repository_parity.py`); no shared app helper yet.

`context_loader` functions are thin wrappers over `load_*_slots`.

---

## 6. List campaigns (read-only, no writes)

**Ad-control authority key:** `(shop_id, advert_id)` — not `main_nmid` (`domain/campaign_ref.py`, `AdvertCampaignRefV1`).

| Function | Path | Returns `main_nmid`? |
|----------|------|----------------------|
| `get_active_adv_ids_for_shop(shop_id: str) -> Sequence[int]` | `app/modules/wb_adv_updater/data_manager.py:868` | **No** — ints only (`adv_id` + optional `search_adv_id` per complex) |
| `PgAdvSettingInventoryReader.load_inventory(shop_id) -> list[AdvSetting]` | `app/modules/ai_package_v1/scope/pg_adv_setting_inventory_reader.py:45` | **No** — ORM has `adv_id`, `name`, `nmids` (JSONB list); no `main_nmid` column |
| `select_shop_inventory_advs(shop_id) -> Select[tuple[AdvSetting]]` | `app/modules/ai_package_v1/scope/queries.py:10` | Query only; same AdvSetting shape |
| `WBShopDataManager.__get_advs(session, shop_id, only_bot_active) -> list[AdvSetting]` | `app/modules/shop_runner/.../wb_shop_data_manager.py:118` | Same; raises `NotFoundActiveAdvCompany` if empty |

**UI labels:** use `AdvSetting.name` and/or `adv_id`. `main_nmid` exists on `ComplexAdv` (shop-runner), not on raw inventory listing functions above.

---

## 7. Payload codec

**Path:** `app/modules/ad_control_settings/persistence/payload_codec.py`

```python
def encode_payload_json(
    feature_id: AdControlFeatureId,
    payload: ConfiguredFeaturePayload,
) -> dict[str, object]:

def decode_payload_json(
    feature_id: AdControlFeatureId,
    data: dict[str, object] | None,
) -> ConfiguredFeaturePayload | None:
```

**ChangeSet `payload` dict shape:** same as `encode_payload_json` output — top-level `kind` (e.g. `"DrrPolicyParamsV1"`), `schema_version` (int), plus type-specific fields. Decimals serialized as strings in JSON. DRR profile nested: `profile.target_drr_percent`, `profile.max_drr_percent` strings.

`ShopAdControlFeaturePayloadV1.payload` / `CampaignOverridePayloadV1.payload` are **untyped dicts** that must decode via `decode_payload_json(feature_id, body.payload)`.

---

## 8. ChangeSet types (Slice B transport)

**Path:** `app/modules/wb_sky_control_plane/models/ad_control_changeset.py`

```python
class AdControlChangeSetV1(BaseModel):
    contract_version: Literal["v1"] = "v1"
    changeset_id: str
    scope: AdControlLogicalScopeV1
    operations: list[AdControlOperationV1]
    metadata: AdControlChangeSetMetadataV1 = Field(default_factory=...)
```

```python
class AdControlLogicalScopeV1(BaseModel):
    provider: Literal["wildberries"] = "wildberries"
    shop_id: str
```

```python
class AdControlChangeSetMetadataV1(BaseModel):
    origin: str | None = None
    reason: str | None = None
```

**Four operation classes (discriminator `op`):**

| Class | `op` | Extra fields |
|-------|------|----------------|
| `SetShopAdControlFeatureOperation` | `shop.set_ad_control_feature` | `payload: ShopAdControlFeaturePayloadV1` |
| `SetCampaignAdControlOverrideOperation` | `campaign.set_ad_control_override` | `resource: AdvertCampaignRefV1`, `payload: CampaignOverridePayloadV1` |
| `DisableCampaignAdControlFeatureOperation` | `campaign.disable_ad_control_feature` | `resource`, `payload: CampaignFeatureTargetV1` |
| `ClearCampaignAdControlFeatureOperation` | `campaign.clear_ad_control_feature` | `resource`, `payload: CampaignFeatureTargetV1` |

**Shared operation base:** `operation_id: str`, `reason: str | None`, `preconditions: AdControlRevisionPreconditionV1`.

```python
class AdControlRevisionPreconditionV1(BaseModel):
    expected_revision: int | None = None  # None => row must be absent; int >= 1 => must match
```

```python
class AdvertCampaignRefV1(BaseModel):
    shop_id: str
    advert_id: int  # positive int
```

---

## 9. Dry-run validation

**Path:** `app/modules/wb_sky_control_plane/kernel/ad_control_validate.py`

```python
def validate_ad_control_changeset(
    changeset: AdControlChangeSetV1,
    *,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> AdControlValidationResult:
```

**Snapshot types:**

```python
class AdControlShopFeatureSnapshotV1(BaseModel):
    feature_id: AdControlFeatureId
    schema_version: int
    activation: ShopFeatureActivation
    payload_json: dict[str, object] | None
    revision: int
    state_token: str

class AdControlCampaignFeatureSnapshotV1(BaseModel):
    shop_id: str
    advert_id: int
    feature_id: AdControlFeatureId
    schema_version: int
    mode: AdControlFeatureMode  # never INHERIT
    payload_json: dict[str, object] | None
    revision: int
    state_token: str
```

```python
class AdControlValidationResult(BaseModel):
    status: DryRunStatus
    changeset_id: str
    semantic_digest: str
    errors: list[ControlPlaneError] = []
    diffs: list[AdControlSemanticDiffV1] = []
```

```python
class AdControlSemanticDiffV1(BaseModel):
    target_key: str
    intent: AdControlMutationKind
    field_path: str
    current: str | None
    desired: str | None
    effective_source_after: str | None = None
```

**`DryRunStatus`:** `app/modules/wb_sky_control_plane/models/enums.py` — `OK`, `REJECTED`, `NO_OP`.

**`REVISION_CONFLICT`:** `ControlPlaneError.code == "REVISION_CONFLICT"` from `_check_revision_precondition` (absent vs present row mismatch or stale revision).

**`CLEAR_TO_INHERIT`:** `AdControlMutationKind.CLEAR_TO_INHERIT` (`persistence/cas.py`); clear op diff uses `effective_source_after="SHOP_POLICY_OR_INHERIT"`. Override create uses `"CAMPAIGN_OVERRIDE"`; disable uses `"CAMPAIGN_DISABLED"`.

**Digest:** `compute_ad_control_semantic_digest(changeset) -> str` (prefix `acs1_`).

---

## 10. Repository methods UI MUST NOT call

**Path:** `persistence/repository.py` — write/CAS surface:

- `apply_shop_mutation`
- `apply_campaign_override`
- `apply_campaign_disable`
- `clear_campaign_feature`

Telegram UI (Slice A read + Slice B dry-run) should use read methods + `validate_ad_control_changeset`; production writes belong to Apply Authority / WB Sky, not the bot UI.

---

## 11. `app/modules/ad_control_settings/runtime/`

**Does not exist** on `stage` (only `domain/` + `persistence/` under `ad_control_settings/`). Nothing to list; no generated runtime to avoid editing.

---

## 12. Existing UI adapter?

**None** for hierarchical ad control in `app/client_bot/` (no `ad_control` / `AdControl` references).

**Read adapters that exist today:**

| Adapter | Role |
|---------|------|
| `persistence/context_loader.py` | PG slots → resolver maps |
| `domain/configured_state.py` | `project_configured_*` for configured projection |
| `domain/diagnostics_builder.py` | `AdControlDiagnosticsBuilder.build` → `AdControlDiagnosticsReportV1` (includes headroom/economics — **omit for no-economics Telegram UI**) |
| `domain/product_adapter.py` | Product DRR tier → `ProductDrrPolicyAdapterResult` for `ResolverContext.product_drr` |

Slice B: `validate_ad_control_changeset` only (no Telegram wrapper).

---

## Suggested UI data flow (read + dry-run)

1. `shop_id` from cabinet context.
2. `load_resolver_shop_features` / `load_resolver_campaign_features` + row getters for revisions.
3. Build `ResolverContext` (enrollment/path from shop policy source of truth elsewhere).
4. `project_configured_*` + `AdControlSettingsResolver.resolve_feature` per feature.
5. User edits → assemble `AdControlChangeSetV1` with codec-shaped dict payloads + `expected_revision` from snapshots.
6. `validate_ad_control_changeset` → show `diffs` / `errors`; do not call `apply_*`.
