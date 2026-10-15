---
cursor:
  subagentId: "bc-46bc43af-e219-5941-9cf8-bd90beafb6f0"
---

# Wave 1B — Hierarchical contract inventory (task 4.2 UI Advertising Control)

Parent change: `openspec/changes/hierarchical-ad-control-settings/`.  
Code is source of truth; OpenSpec cited for slice boundaries only.

## 1. Concept → symbol map

| CONCEPT | SYMBOL | KIND | PATH | KEY FIELDS |
|--------|--------|------|------|------------|
| SHOP settings (configured slot) | `ShopFeatureSlot` | dataclass | `app/modules/ad_control_settings/domain/resolver_models.py` | `activation: ShopFeatureActivation`, `payload: ConfiguredFeaturePayload \| None` |
| SHOP settings (projection) | `ConfiguredShopFeatureState` | dataclass | `app/modules/ad_control_settings/domain/configured_state.py` | `feature_id`, `scope=SHOP`, `activation`, `payload`, `schema_version` |
| SHOP settings (PG authority) | `AdControlShopFeatureRow` | SQLAlchemy model | `app/modules/ad_control_settings/persistence/models.py` | `shop_id`, `feature_id`, `schema_version`, `activation`, `payload_json`, `revision`, `state_token` |
| CAMPAIGN settings (configured slot) | `CampaignFeatureSlot` | dataclass | `app/modules/ad_control_settings/domain/resolver_models.py` | `mode: AdControlFeatureMode`, `payload` (override only) |
| CAMPAIGN settings (projection) | `ConfiguredCampaignFeatureState` | dataclass | `app/modules/ad_control_settings/domain/configured_state.py` | `mode`, `override_payload` (only if `OVERRIDE`), `schema_version` |
| CAMPAIGN settings (PG authority) | `AdControlCampaignFeatureRow` | SQLAlchemy model | `app/modules/ad_control_settings/persistence/models.py` | `shop_id`, `advert_id`, `feature_id`, `mode` (OVERRIDE/DISABLED only), `payload_json`, `revision`, `state_token` |
| CAMPAIGN identity | `CampaignRef` / `AdvertCampaignRefV1` | dataclass / pydantic | `domain/campaign_ref.py`, `wb_sky_control_plane/models/ad_control_changeset.py` | `shop_id`, `advert_id` |
| INHERIT (campaign) | `AdControlFeatureMode.INHERIT` | enum member | `domain/enums.py` | Default when no campaign row; not persisted |
| OVERRIDE (campaign) | `AdControlFeatureMode.OVERRIDE` | enum member | `domain/enums.py` | Persisted authority row with payload |
| DISABLED (campaign) | `AdControlFeatureMode.DISABLED` | enum member | `domain/enums.py` | Persisted authority row, `payload_json=None` |
| DISABLED (shop) | `ShopFeatureActivation.DISABLED` | enum member | `domain/enums.py` | Shop has no INHERIT; disabled is explicit activation |
| ENABLED (shop) | `ShopFeatureActivation.ENABLED` | enum member | `domain/enums.py` | Requires payload when persisting |
| configured state (aggregate input) | `ResolverContext` | dataclass | `domain/resolver_models.py` | `enrollment`, `control_path`, `shop_features`, `campaign_features`, `product_drr` |
| configured state (project) | `project_configured_shop_features`, `project_configured_campaign_features` | functions | `domain/configured_state.py` | Full V1 registry sweep |
| effective state (per feature) | `ResolvedFeaturePolicy` | dataclass | `domain/resolver_models.py` | `active`, `payload`, `provenance`, `reason_codes` |
| effective DRR (derived) | `ShopEffectiveControlDrr`, `CampaignEffectiveControlDrr` | dataclass | `domain/drr_state.py` | Derived control DRR; not persisted as authority |
| provenance | `ProvenanceEntry` | dataclass | `domain/provenance.py` | `feature_id`, `source_kind: EffectiveSourceKind`, `source_scope`, `schema_version` |
| revision (row CAS) | `revision` on PG rows; `AdControlRevisionPreconditionV1.expected_revision` | field / pydantic | `persistence/models.py`, `ad_control_changeset.py` | `None` => absent slot; `int>=1` => must match row |
| revision (ledger) | `AdControlSlotMutationLedger.last_mutation_revision`, `allocate_mutation_revision` | ORM / function | `persistence/models.py`, `persistence/revision_ledger.py` | Survives campaign row delete (CLEAR) |
| state token (ad control content) | `compute_ad_control_state_token` | function | `persistence/state_token.py` | Prefix `acs_`; includes revision in hash parts |
| state token (on snapshots) | `state_token` field | pydantic/ORM | `kernel/ad_control_validate.py` snapshots, PG rows | Audit/diff; CAS binds to `revision` |
| state token (WB campaign A1) | `compute_state_token`, `STATE_TOKEN_VERSION=st1` | function | `wb_sky_control_plane/kernel/state_token.py` | **Separate** from ad-control settings (budget/sales/bid) |
| capabilities (ad control) | **ABSENT** dedicated type | — | Searched `ad_control_settings/**`, `kernel/ad_control_validate.py` | Use `reason_codes` + `blockers` + headroom eligibility |
| capabilities (WB A1 plane) | `CampaignCapabilitiesV1`, `evaluate_capabilities` | pydantic / function | `models/capabilities.py`, `kernel/capabilities_eval.py` | `set_budget_policy`, `set_sales_policy`, `set_bid_control_policy` — not ad-control V1 |
| blockers | `ResolverBlocked.blockers`, `CampaignHeadroomEligibility.blockers`, diagnostics `blockers` | `tuple[str, ...]` | `resolver_models.py`, `headroom.py`, `diagnostics.py` | Opaque string tokens e.g. `hierarchical_automation_not_enrolled` |
| reasons | `AdControlReasonCode` | enum | `domain/reason_codes.py` | Fail-closed eligibility/diagnostics |
| dry-run output | `AdControlValidationResult` | pydantic | `kernel/ad_control_validate.py` | `status: DryRunStatus`, `semantic_digest`, `errors`, `diffs: AdControlSemanticDiffV1[]` |
| dry-run diff row | `AdControlSemanticDiffV1` | pydantic | `kernel/ad_control_validate.py` | `intent: AdControlMutationKind`, `effective_source_after` |
| ChangeSet | `AdControlChangeSetV1` | pydantic | `wb_sky_control_plane/models/ad_control_changeset.py` | `contract_version=v1`, `scope`, `operations[]` |
| mutation intent | `AdControlMutationKind` | enum | `persistence/cas.py` | Includes `CLEAR_TO_INHERIT` |
| return to inherit (op) | `ClearCampaignAdControlFeatureOperation` | pydantic | `ad_control_changeset.py` | `op="campaign.clear_ad_control_feature"` |
| return to inherit (persist) | `AdControlSettingsRepository.clear_campaign_feature` | async method | `persistence/repository.py` | `CampaignClearUpsert` → DELETE row |
| feature IDs | `AdControlFeatureId` | enum | `domain/enums.py` | V1 registry keys |
| feature registry | `FEATURE_REGISTRY`, `FeatureDefinition` | dict / dataclass | `domain/registry.py` | `supported_scopes`, `schema_version`, `validate_payload` |
| payloads | `ConfiguredFeaturePayload` union + `*ParamsV1` | dataclass | `domain/configured.py` | Per-feature typed params |
| diagnostics read model | `AdControlDiagnosticsReportV1` | dataclass | `domain/diagnostics.py` | configured + effective + DRR triple + headroom |
| diagnostics builder | `AdControlDiagnosticsBuilder.build` | static method | `domain/diagnostics_builder.py` | Pure; `dry_run_diff_available` flag |
| product tier (parallel) | `ProductControlMode`, `ProductDrrPolicyAdapter` | enum / class | `product_control/domain/enums.py`, `ad_control_settings/domain/product_adapter.py` | Feeds `ResolverContext.product_drr` for DRR_POLICY inherit only |
| enrollment (hierarchical) | `HierarchicalEnrollment` | enum | `domain/enums.py` | `NOT_ENROLLED` fail-closed in resolver |
| control path | `ControlPathKind` | enum | `domain/enums.py` | `LEGACY_PASSTHROUGH` blocks hierarchical resolver |

## 2. Enum member lists (exact values)

### `AdControlFeatureId`
`DRR_POLICY`, `DYNAMIC_DRR_CONTROL`, `CPO_INCREASE_ON_HEADROOM`, `CPO_DECREASE_ON_OVERSPEND`, `CPO_SAFETY_BOUNDS`

### `AdControlFeatureMode` (campaign)
`INHERIT`, `OVERRIDE`, `DISABLED`

### `ShopFeatureActivation` (shop)
`ENABLED`, `DISABLED`

### `AdControlScope`
`SHOP`, `PRODUCT`, `CAMPAIGN`, `SYSTEM_LEGACY`

### `EffectiveSourceKind` (provenance)
`CAMPAIGN_OVERRIDE`, `CAMPAIGN_DISABLED`, `PRODUCT_OVERRIDE`, `PRODUCT_DISABLED`, `SHOP_POLICY`, `SHOP_DISABLED`, `SYSTEM_LEGACY_DEFAULT`, `LEGACY_PASSTHROUGH`, `NOT_APPLICABLE`  
**Used in resolver today:** `CAMPAIGN_*`, `SHOP_*`, `PRODUCT_OVERRIDE` (via adapter). Others are named only.

### `AdControlMutationKind`
`CREATE`, `UPDATE`, `DISABLE`, `CLEAR_TO_INHERIT`, `NO_OP`

### `AdControlReasonCode`
`OK`, `NOT_ENROLLED_FAIL_CLOSED`, `LEGACY_PASSTHROUGH_ACTIVE`, `FEATURE_DISABLED_AT_CAMPAIGN`, `FEATURE_DISABLED_AT_SHOP`, `FEATURE_DISABLED_AT_PRODUCT`, `UNSUPPORTED_SCOPE_FOR_FEATURE`, `UNKNOWN_FEATURE`, `INVALID_CONFIGURATION`, `SHOP_ENABLED_MISSING_PAYLOAD`, `ACTUAL_DRR_STALE`, `ACTUAL_DRR_INSUFFICIENT`, `ACTUAL_DRR_UNSUPPORTED`, `MEASUREMENT_UNKNOWN`, `NO_CONTROL_ACTION_STALE_OR_UNKNOWN`, `HEADROOM_ALLOCATOR_NOT_ACCEPTED`, `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`, `PRODUCT_DRR_ADAPTER_BLOCKED`

### `DataSufficiency`
`SUFFICIENT`, `INSUFFICIENT`, `STALE`, `UNSUPPORTED`, `UNKNOWN`

### `HierarchicalEnrollment`
`NOT_ENROLLED`, `ENROLLED`

### `ControlPathKind`
`HIERARCHICAL`, `LEGACY_PASSTHROUGH`

### `DryRunStatus` (dry-run)
`ok`, `rejected`, `no_op`

### `MinObservedDataSufficiencyRequirement`
`SUFFICIENT`

### ChangeSet `op` literals (`KNOWN_AD_CONTROL_OPS`)
`shop.set_ad_control_feature`, `campaign.set_ad_control_override`, `campaign.disable_ad_control_feature`, `campaign.clear_ad_control_feature`

### `ProductControlMode` (product_control; product tier for DRR adapter)
`INHERIT_SHOP`, `OVERRIDE_ENABLED`, `BLOCKED`

### `ProductControlBlockerReason`
`BLOCKED_BY_PRODUCT_PRICE_SOURCE`, `PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS`, `INVALID_CONFIGURATION`, `SHOP_CONTROL_BLOCKED`, `PRODUCT_CONTROL_BLOCKED`

## 3. Configured vs effective

| Layer | Representation | Primary fields |
|-------|----------------|----------------|
| Configured shop | `ShopFeatureSlot` / `ConfiguredShopFeatureState` | `activation`, `payload` |
| Configured campaign | `CampaignFeatureSlot` / `ConfiguredCampaignFeatureState` | `mode`, `override_payload` (only OVERRIDE) |
| Effective per feature | `ResolvedFeaturePolicy` | `active`, `payload`, `provenance`, `reason_codes` |
| Effective DRR target | `ConfiguredTargetDrr` | `target_drr_percent`, `max_drr_percent`, `provenance` |
| Observed fact | `ActualDrrObservation` | `actual_drr_percent`, `data_sufficiency` |
| Derived control | `ShopEffectiveControlDrr`, `CampaignEffectiveControlDrr` | Not user settings; recomputable |

Resolver entry: `AdControlSettingsResolver.resolve_feature(context, feature_id)`.

Campaign INHERIT = missing PG row → default `CampaignFeatureSlot(INHERIT, None)` at load; resolver live-reads shop/product without copying shop into campaign storage (`configured_state.py` docstring; `persistence/models.py` campaign row docstring).

## 4. CLEAR_TO_INHERIT / return to inherit

**Dry-run:** `_validate_campaign_clear` in `kernel/ad_control_validate.py`  
- Absent snapshot + valid revision preconditions → `NO_OP`, `effective_source_after="SHOP_POLICY_OR_INHERIT"`.  
- Present snapshot → `CLEAR_TO_INHERIT`, `current=prior_mode`, `desired="absent"`, same `effective_source_after`.

**Persistence:** `clear_campaign_feature` deletes `AdControlCampaignFeatureRow`, bumps `AdControlSlotMutationLedger`, returns `AdControlMutationResult(kind=CLEAR_TO_INHERIT, revision=None, state_token=None)`. INHERIT is never stored (`PersistedInheritForbiddenError`).

**ChangeSet op:** `ClearCampaignAdControlFeatureOperation` with `CampaignFeatureTargetV1`.

## 5. Persistence vs read-model only

| Persisted (PG) | Read-model / pure |
|----------------|-------------------|
| `AdControlShopFeatureRow` | `ShopFeatureSlot`, `ConfiguredShopFeatureState` |
| `AdControlCampaignFeatureRow` (OVERRIDE/DISABLED only) | `CampaignFeatureSlot`, `ConfiguredCampaignFeatureState` |
| `AdControlSlotMutationLedger` | — |
| — | `ResolverContext`, `ResolvedFeaturePolicy`, `AdControlDiagnosticsReportV1` |
| — | `AdControlShopFeatureSnapshotV1`, `AdControlCampaignFeatureSnapshotV1` (dry-run inputs; built from rows in tests via helpers; `row_to_shop_snapshot` / `row_to_campaign_snapshot` partial helpers on repository module) |
| — | DRR derived types, headroom state, `BoundedCpoProposal` |
| Product control rows | **Out of scope** for `ad_control_settings` persistence; via `ProductDrrPolicyAdapter` only |

Apply Authority wiring for ad-control mutations: **not implemented** (Slice B dry-run only per `design.md`).

## 6. Public read-only / validate APIs (no writes)

| Function | Args | Returns | Path |
|----------|------|---------|------|
| `AdControlSettingsResolver.assert_hierarchical_path` | `context: ResolverContext` | `ResolverBlocked \| None` | `domain/resolver.py` |
| `AdControlSettingsResolver.resolve_feature` | `context`, `feature_id` | `ResolvedFeaturePolicy \| ResolverBlocked` | `domain/resolver.py` |
| `AdControlSettingsResolver.resolve_configured_target_drr` | `context` | `DrrPolicyParamsV1 \| ResolverBlocked` | `domain/resolver.py` |
| `project_configured_shop_features` | `context` | `tuple[ConfiguredShopFeatureState, ...]` | `domain/configured_state.py` |
| `project_configured_campaign_features` | `context` | `tuple[ConfiguredCampaignFeatureState, ...]` | `domain/configured_state.py` |
| `AdControlDiagnosticsBuilder.build` | `context`, `actual_drr`, optional economics kwargs, `dry_run_diff_available` | `AdControlDiagnosticsReportV1` | `domain/diagnostics_builder.py` |
| `ProductDrrPolicyAdapter.from_effective_control` | `EffectiveControlResult` | `ProductDrrPolicyAdapterResult` | `domain/product_adapter.py` |
| `validate_ad_control_changeset` | `changeset`, `shop_snapshots`, `campaign_snapshots` | `AdControlValidationResult` | `kernel/ad_control_validate.py` |
| `compute_ad_control_semantic_digest` | `changeset` | `str` (`acs1_…`) | `kernel/ad_control_validate.py` |
| `validate_shop_upsert` | `ShopFeatureUpsert` | `None` (raises) | `persistence/repository.py` |
| `validate_campaign_override_upsert` | `CampaignOverrideUpsert` | `None` (raises) | `persistence/repository.py` |
| `load_resolver_shop_features` | `repository`, `shop_id` | `dict[AdControlFeatureId, ShopFeatureSlot]` | `persistence/context_loader.py` |
| `load_resolver_campaign_features` | `repository`, `campaign` | `dict[AdControlFeatureId, CampaignFeatureSlot]` | `persistence/context_loader.py` |
| `AdControlSettingsRepository.load_shop_slots` / `load_campaign_slots` | async read | slot dicts | `persistence/repository.py` |
| `bind_ad_control_idempotency` / `evaluate_ad_control_idempotency_replay` | changeset + binding metadata | pure idempotency decision | `ad_control/idempotency_contract.py` |
| `control_action_allowed` | `ActualDrrObservation` | `tuple[bool, AdControlReasonCode]` | `domain/headroom_eval.py` |
| `campaign_headroom_eligibility` | campaign, actual, enrollment, control_path, … | `CampaignHeadroomEligibility` | `domain/headroom_eval.py` |

**Note:** No production helper maps PG rows → `AdControl*SnapshotV1` except test helpers (`test_ad_control_dry_run_repository_parity.py`) and manual field copy pattern.

## 7. Slice A vs B vs 4.2

From `openspec/changes/hierarchical-ad-control-settings/tasks.md`:

- **Slice A (done):** registry, resolver, product adapter, DRR triple, headroom eligibility, diagnostics contract, unit tests.
- **Slice B (done):** PG models, repository, payload codec, `AdControlChangeSetV1`, `validate_ad_control_changeset` (dry-run only; Apply unwired).
- **4.1 (open):** Runtime shop-runner integration.
- **4.2 (open):** UI Advertising Control + Diagnostics.

`design.md`: Apply Authority unwired; `HeadroomAllocator` protocol without production algorithm; no runtime CPO actuation in Slice B.

## 8. Fail-closed errors

### Domain resolver
- Returns `ResolverBlocked` with `reason_codes` + `blockers` (not exceptions) for enrollment, legacy path, scope, invalid config.
- `get_feature_definition` → `FeatureValidationError` (unknown feature string).

### Dry-run `ControlPlaneError.code` (representative)
`DUPLICATE_OPERATION_ID`, `DUPLICATE_TARGET`, `UNSUPPORTED_OPERATION`, `SCOPE_SHOP_MISMATCH`, `REVISION_CONFLICT`, `UNKNOWN_FEATURE`, `INVALID_PAYLOAD`, `INVALID_CONFIGURATION`, `UNSUPPORTED_SCHEMA_VERSION`, plus scope reason values e.g. `UNSUPPORTED_SCOPE_FOR_FEATURE`.

### Persistence (writes — not for UI read path but parity with validate)
`RevisionConflictError`, `PersistedInheritForbiddenError`, `UnsupportedSchemaVersionError`, `AdControlPersistenceError`, `PayloadCodecError`, `FeatureValidationError`.

### Pydantic ChangeSet parse
Invalid `AdControlFeatureId` / empty ops fail at model validation before `validate_ad_control_changeset`.
