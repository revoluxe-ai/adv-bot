---
cursor:
  subagentId: "bc-ab9bf4d3-e718-5cea-8964-6cc66bdca911"
---

# Hierarchical ad control — Slice A/B type archaeology

**Repo:** `/agent/repos/adv-bot`  
**Scope:** OpenSpec change `openspec/changes/hierarchical-ad-control-settings/` + related ADRs + `app/modules/ad_control_settings/` + `wb_sky_control_plane` ad-control ChangeSet/dry-run.  
**Authority note:** Slice A/B **code is on stage**; change-local ADRs under the change folder are **Proposed** (not in `openspec/decisions/`). Accepted ADRs that constrain the domain: `product-control-aggregate-ownership`, `product-pricing-and-cpo-ownership`, `drr-cpo-price-semantics`, `campaign-settings-changeset-ownership`, `campaign-settings-contract-ownership`, `changeset-apply-authority-ownership`.

---

## Layering: persistence vs domain vs control plane

| Layer | Path | Writes configured rows? |
|-------|------|-------------------------|
| Domain (pure) | `app/modules/ad_control_settings/domain/` | NO |
| Persistence | `app/modules/ad_control_settings/persistence/` (`AdControlSettingsRepository`) | YES (PG; future Apply Authority caller) |
| Dry-run / ChangeSet transport | `app/modules/wb_sky_control_plane/models/ad_control_changeset.py`, `kernel/ad_control_validate.py` | NO |
| Campaign settings ChangeSet (separate) | `wb_sky_control_plane` `ChangeSetV1` / `validate_changeset` | NO (AdvSetting fields; not ad-control registry) |

Product DRR tier: `app/modules/product_control/` owns semantics; ad control reads via `ProductDrrPolicyAdapter` only.

---

## Symbol map (requested concepts)

### SHOP settings type

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `ShopFeatureSlot` | dataclass | `domain/resolver_models.py:25` | `activation: ShopFeatureActivation`, `payload: ConfiguredFeaturePayload \| None` | YES | Domain configured slot input to resolver |
| `ConfiguredShopFeatureState` | dataclass | `domain/configured_state.py:27` | `feature_id`, `scope`, `activation`, `payload`, `schema_version` | YES | Diagnostics projection of configured shop policy |
| `AdControlShopFeatureRow` | SQLAlchemy ORM | `persistence/models.py:46` | `shop_id`, `feature_id`, `schema_version`, `activation`, `payload_json`, `revision`, `state_token`, `updated_at` | YES | Authoritative PG row; identity `(shop_id, feature_id)` |
| `ShopFeatureUpsert` | dataclass | `persistence/repository.py:68` | `shop_id`, `feature_id`, `schema_version`, `activation`, `payload` | YES | Repository write intent (Apply path) |
| `ShopAdControlFeaturePayloadV1` | pydantic | `wb_sky_control_plane/models/ad_control_changeset.py:87` | `feature_id`, `schema_version`, `activation`, `payload: dict \| None` | YES | ChangeSet op body (`shop.set_ad_control_feature`) |
| `AdControlShopFeatureSnapshotV1` | pydantic | `kernel/ad_control_validate.py:56` | `feature_id`, `schema_version`, `activation`, `payload_json`, `revision`, `state_token` | YES | Dry-run authoritative snapshot slice |
| `ShopFeatureActivation` | StrEnum | `domain/enums.py:35` | `ENABLED`, `DISABLED` | YES | Shop has no INHERIT; disabled = feature off at shop |

### CAMPAIGN settings type

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `CampaignFeatureSlot` | dataclass | `domain/resolver_models.py:33` | `mode: AdControlFeatureMode`, `payload: ConfiguredFeaturePayload \| None` | YES | Missing row ⇒ default INHERIT in resolver |
| `ConfiguredCampaignFeatureState` | dataclass | `domain/configured_state.py:38` | `feature_id`, `scope`, `mode`, `override_payload`, `schema_version` | YES | `override_payload` only when `mode == OVERRIDE` |
| `AdControlCampaignFeatureRow` | SQLAlchemy ORM | `persistence/models.py:76` | `shop_id`, `advert_id`, `feature_id`, `schema_version`, `mode`, `payload_json`, `revision`, `state_token`, `updated_at` | YES | OVERRIDE or DISABLED only; INHERIT = absent row |
| `CampaignOverrideUpsert` | dataclass | `persistence/repository.py:79` | `campaign`, `feature_id`, `schema_version`, `payload` | YES | Persists OVERRIDE |
| `CampaignDisableUpsert` | dataclass | `persistence/repository.py:89` | `campaign`, `feature_id`, `schema_version` | YES | Persists DISABLED |
| `CampaignClearUpsert` | dataclass | `persistence/repository.py:98` | `campaign`, `feature_id` | YES | Deletes row ⇒ INHERIT |
| `CampaignOverridePayloadV1` | pydantic | `ad_control_changeset.py:107` | `feature_id`, `schema_version`, `payload: dict` | YES | OVERRIDE ChangeSet body |
| `CampaignFeatureTargetV1` | pydantic | `ad_control_changeset.py:98` | `feature_id`, `schema_version` | YES | disable/clear targets |
| `AdvertCampaignRefV1` | pydantic | `ad_control_changeset.py:43` | `shop_id`, `advert_id` | YES | Campaign authority `(shop_id, advert_id)` |
| `CampaignRef` | dataclass | `domain/campaign_ref.py:9` | `shop_id`, `advert_id` | YES | Domain campaign identity |
| `AdControlCampaignFeatureSnapshotV1` | pydantic | `kernel/ad_control_validate.py:69` | `shop_id`, `advert_id`, `feature_id`, `schema_version`, `mode`, `payload_json`, `revision`, `state_token` | YES | Never INHERIT in snapshot |

### INHERIT / OVERRIDE / DISABLED

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `AdControlFeatureMode.INHERIT` | enum member | `domain/enums.py:30` | value `"INHERIT"` | YES | Campaign default; no PG row |
| `AdControlFeatureMode.OVERRIDE` | enum member | `domain/enums.py:31` | value `"OVERRIDE"` | YES | Campaign row with payload |
| `AdControlFeatureMode.DISABLED` | enum member | `domain/enums.py:32` | value `"DISABLED"` | YES | Explicit campaign off; beats shop |
| `PersistedInheritForbiddenError` | Exception | `persistence/cas.py:13` | — | YES | Fail closed if INHERIT stored on campaign row |

### Configured state

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `ResolverContext` | dataclass | `domain/resolver_models.py:41` | `enrollment`, `control_path`, `shop_id`, `shop_features`, `campaign`, `campaign_features`, `product_drr` | YES | Pure configured inputs (no I/O) |
| `ConfiguredFeaturePayload` | type alias | `domain/configured.py:67` | union of `*ParamsV1` dataclasses | YES | Typed owner payloads per feature |
| `project_configured_shop_features` | function | `domain/configured_state.py:58` | → `tuple[ConfiguredShopFeatureState, ...]` | YES | Full registry walk for diagnostics |
| `project_configured_campaign_features` | function | `domain/configured_state.py:80` | → `tuple[ConfiguredCampaignFeatureState, ...]` | YES | Default INHERIT per missing slot |

### Effective state

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `ResolvedFeaturePolicy` | dataclass | `domain/resolver_models.py:54` | `feature_id`, `active`, `payload`, `provenance`, `reason_codes` | YES | **Effective configured policy** per feature |
| `ConfiguredTargetDrr` | dataclass | `domain/drr_state.py:17` | `target_drr_percent`, `max_drr_percent`, `provenance` | YES | Resolved DRR policy slice |
| `ShopEffectiveControlDrr` | dataclass | `domain/drr_state.py:36` | `effective_control_drr_percent`, `derived_from_configured` | YES | **Derived** control state (not persisted) |
| `CampaignEffectiveControlDrr` | dataclass | `domain/drr_state.py:44` | `effective_control_drr_percent`, `inherits_shop_control`, `provenance` | YES | Derived campaign control DRR |
| `derive_shop_effective_control_drr` | function | `domain/headroom_eval.py:26` | → `ShopEffectiveControlDrr` | YES | Foundation placeholder dynamic path |
| `AdControlSettingsResolver.resolve_feature` | static method | `domain/resolver.py:56` | → `ResolvedFeaturePolicy \| ResolverBlocked` | YES | INHERIT live fall-through PRODUCT→SHOP |

### Provenance

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `ProvenanceEntry` | dataclass | `domain/provenance.py:15` | `feature_id`, `source_kind`, `source_scope`, `schema_version` | YES | One effective configured value source |
| `EffectiveSourceKind` | StrEnum | `domain/enums.py:70` | `CAMPAIGN_OVERRIDE`, `CAMPAIGN_DISABLED`, `PRODUCT_OVERRIDE`, `PRODUCT_DISABLED`, `SHOP_POLICY`, `SHOP_DISABLED`, `SYSTEM_LEGACY_DEFAULT`, `LEGACY_PASSTHROUGH`, `NOT_APPLICABLE` | YES | Diagnostics + resolver provenance |

### Revision

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `revision` (shop/campaign row) | ORM column | `persistence/models.py:59`, `:90` | `Mapped[int]` (BIGINT) | YES | CAS write authority |
| `AdControlSlotMutationLedger.last_mutation_revision` | ORM column | `persistence/models.py:26` | `Mapped[int]` | YES | Monotonic per logical slot; survives CLEAR |
| `SlotMutationKey` | dataclass | `persistence/revision_ledger.py:21` | `shop_id`, `scope`, `feature_id`, `advert_id` | YES | Ledger identity |
| `allocate_mutation_revision` | async function | `persistence/revision_ledger.py:52` | → `int` | YES | PG upsert increment |
| `AdControlRevisionPreconditionV1` | pydantic | `ad_control_changeset.py:67` | `expected_revision: int \| None` | YES | `None` ⇒ absent slot; `int` ⇒ must match |
| `RevisionConflictError` | Exception | `persistence/cas.py:9` | — | YES | Repository CAS fail closed |

### State token

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `state_token` (row) | ORM column | `persistence/models.py:60`, `:91` | `Mapped[str]` | YES | Content fingerprint on row |
| `compute_ad_control_state_token` | function | `persistence/state_token.py:10` | `parts: dict[str, Any]` → `str` (`acs_…`) | YES | **Not** CAS precondition; audit/diff only (per spec) |
| `AdControlShopFeatureSnapshotV1.state_token` | pydantic field | `kernel/ad_control_validate.py:66` | `str` | YES | Passed into dry-run snapshots |
| Campaign `ChangeSetV1` `st1` | function | `wb_sky_control_plane/kernel/state_token.py:83` | separate from ad-control | YES | **AdvSetting** campaign settings only; not used by `validate_ad_control_changeset` |

### Capabilities

| NAME | KIND | PATH | FIELDS | IMPLEMENTED | NOTES |
|------|------|------|--------|-------------|-------|
| *(ad control)* | — | — | — | **NO** | No `capabilities` symbol under `ad_control_settings/` |
| `CampaignCapabilitiesV1` | pydantic | `wb_sky_control_plane/models/capabilities.py:18` | `set_budget_policy`, `set_sales_policy`, `set_bid_control_policy` | YES | **Campaign settings ChangeSetV1 only**; unrelated to ad-control ops |
| `evaluate_capabilities` | function | `kernel/capabilities_eval.py:41` | snapshot → `CampaignCapabilitiesV1` | YES | Tri-state ELIGIBLE/INELIGIBLE/UNKNOWN for bounded campaign settings ops |

### Blockers / reasons

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `AdControlReasonCode` | StrEnum | `domain/reason_codes.py:8` | 18 codes incl. `NOT_ENROLLED_FAIL_CLOSED`, `ACTUAL_DRR_STALE`, `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`, … | YES | Deterministic diagnostics/eligibility |
| `ResolverBlocked` | dataclass | `domain/resolver_models.py:65` | `reason_codes`, `blockers: tuple[str, ...]` | YES | Hierarchical resolver fail-closed |
| `blockers` on diagnostics | field | `domain/diagnostics.py:52` | `tuple[str, ...]` | YES | Human/debug strings alongside reason codes |
| `CampaignHeadroomEligibility.blockers` | field | `domain/headroom.py:34` | `tuple[str, ...]` | YES | Headroom gate |
| `control_action_allowed` | function | `domain/headroom_eval.py:83` | → `(bool, AdControlReasonCode)` | YES | Stale/insufficient ⇒ no control action |

Dry-run **error codes** (`ControlPlaneError.code` in ad control validator): `REVISION_CONFLICT`, `DUPLICATE_OPERATION_ID`, `DUPLICATE_TARGET`, `UNSUPPORTED_OPERATION`, `UNKNOWN_FEATURE`, `INVALID_PAYLOAD`, `UNSUPPORTED_SCHEMA_VERSION`, `INVALID_CONFIGURATION`, `SCOPE_SHOP_MISMATCH`, plus scope reason enum **values** from `AdControlReasonCode` (e.g. `UNSUPPORTED_SCOPE_FOR_FEATURE`).

### Dry-run output

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `validate_ad_control_changeset` | function | `kernel/ad_control_validate.py:127` | snapshots in → `AdControlValidationResult` | YES | Any error ⇒ whole changeset REJECTED |
| `AdControlValidationResult` | pydantic | `kernel/ad_control_validate.py:97` | `status: DryRunStatus`, `changeset_id`, `semantic_digest`, `errors`, `diffs` | YES | Slice B dry-run contract |
| `AdControlSemanticDiffV1` | pydantic | `kernel/ad_control_validate.py:84` | `target_key`, `intent`, `field_path`, `current`, `desired`, `effective_source_after` | YES | Configured mutation diff entry |
| `DryRunStatus` | Enum | `models/enums.py:99` | `OK`, `REJECTED`, `NO_OP` | YES | Shared with campaign ChangeSet pipeline |
| `compute_ad_control_semantic_digest` | function | `kernel/ad_control_validate.py:119` | → `acs1_{sha256…}` | YES | Idempotency binding (Apply unwired) |
| `AdControlDiagnosticsReportV1.dry_run_diff_available` | field | `domain/diagnostics.py:53` | `bool` | YES | Flag for future UI; not populated from validator in domain alone |

`effective_source_after` dry-run strings: `CAMPAIGN_OVERRIDE`, `CAMPAIGN_DISABLED`, `SHOP_POLICY_OR_INHERIT` (see `ad_control_validate.py`).

### AdControlChangeSetV1

| NAME | KIND | PATH:LINE | FIELDS | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `AdControlChangeSetV1` | pydantic | `ad_control_changeset.py:167` | `contract_version`, `changeset_id`, `scope`, `operations`, `metadata` | YES | Transport-independent; dry-run only in Slice B |
| Ops | pydantic | `ad_control_changeset.py:133-155` | `shop.set_ad_control_feature`, `campaign.set_ad_control_override`, `campaign.disable_ad_control_feature`, `campaign.clear_ad_control_feature` | YES | Discriminated by `op` |
| `AdControlIdempotencyBinding` | dataclass | `ad_control/idempotency_contract.py:27` | `semantic_digest`, `fingerprint` | PARTIAL | Contract only; Apply not wired for ad control |

### Resolver / effective policy functions

| NAME | KIND | PATH | IMPLEMENTED | NOTES |
|------|------|------|-------------|-------|
| `AdControlSettingsResolver` | class | `domain/resolver.py:38` | YES | Pure effective **configured** policy |
| `assert_hierarchical_path` | static | `domain/resolver.py:42` | YES | NOT_ENROLLED / LEGACY fail closed |
| `resolve_configured_target_drr` | static | `domain/resolver.py:184` | YES | DRR convenience wrapper |
| `ProductDrrPolicyAdapter.from_effective_control` | static | `domain/product_adapter.py:47` | YES | PRODUCT tier for DRR_POLICY only |
| `load_resolver_shop_features` | async | `persistence/context_loader.py:18` | YES | PG → slots |
| `load_resolver_campaign_features` | async | `persistence/context_loader.py:26` | YES | PG → slots (omit ⇒ INHERIT) |
| `AdControlDiagnosticsBuilder` | class | `domain/diagnostics_builder.py:45` | YES | Resolver + headroom → report (no I/O) |
| `FEATURE_REGISTRY` / `validate_feature_payload` | dict / fn | `domain/registry.py:88`, `:147` | YES | Fail closed unknown feature/scope/schema |

### Mutation intent (persistence + dry-run diffs)

| NAME | KIND | PATH:LINE | VALUES | IMPLEMENTED | NOTES |
|------|------|-----------|--------|-------------|-------|
| `AdControlMutationKind` | StrEnum | `persistence/cas.py:21` | `CREATE`, `UPDATE`, `DISABLE`, `CLEAR_TO_INHERIT`, `NO_OP` | YES | Shared semantic intent for diffs + repository |

---

## Payload types (configured `*ParamsV1`)

All in `domain/configured.py` — `DrrPolicyParamsV1` (wraps `DrrProfile`), `DynamicDrrControlParamsV1`, `CpoIncreaseOnHeadroomParamsV1`, `CpoDecreaseOnOverspendParamsV1`, `CpoSafetyBoundsParamsV1`.

Registry: `AdControlFeatureId` + `FeatureDefinition` in `domain/registry.py`.

---

## SPEC_ONLY / not in code

| Concept | Where specified | Code |
|---------|-----------------|------|
| UI Advertising Control + Diagnostics | `owner-contract.md:57`, `tasks.md` 4.2 | **SPEC_ONLY** (no UI module wired) |
| Ad control Apply Authority durable apply | change persistence ADR §7 | **PARTIAL** (repository writes exist; no production Apply adapter) |
| `HeadroomAllocator` production ranking | `owner-contract.md`, `headroom.py` Protocol | **SPEC_ONLY** (protocol only) |
| Promoted main spec `openspec/specs/hierarchical-ad-control-settings/` | — | **SPEC_ONLY** (spec lives under active change only) |

---

## Architecture decisions constraining UI placement

| Path | Title | UI-relevant rule |
|------|-------|------------------|
| `openspec/changes/hierarchical-ad-control-settings/decisions/hierarchical-ad-control-settings-ownership/decision.md` | hierarchical-ad-control-settings-ownership (**Proposed**) | Registry/resolver in `ad_control_settings/`; product DRR via adapter; campaign id `(shop_id, advert_id)`; no global automation flag; no shop copy on campaign rows |
| `openspec/changes/hierarchical-ad-control-settings/owner-contract.md` | Owner contract | Future UI: **Advertising Control + Diagnostics/Test**, same resolver semantics, **no writes** in diagnostics |
| `openspec/changes/hierarchical-ad-control-settings/specs/.../spec.md` | foundation spec | Runtime shop-runner and **UI out of scope** for this change |
| `openspec/changes/hierarchical-ad-control-settings/proposal.md` | proposal | Explicit non-goals: UI / Excel / API / MCP transport |
| `openspec/decisions/product-control-aggregate-ownership/decision.md` | product-control-aggregate-ownership (**Accepted**) | UI/Excel/ChangeSet writers for **product** control are separate changes; WBCard not a settings bag; AdvSetting not canonical DRR owner post-migration |
| `openspec/decisions/campaign-settings-contract-ownership/decision.md` | campaign settings contract (**Accepted**) | Excel editable/read_only from **registry**; Excel not canonical; separate from ad-control per-function registry |
| `openspec/decisions/product-pricing-and-cpo-ownership/decision.md` | product-pricing-and-cpo-ownership (**Accepted**) | **No formula duplication** in Telegram, Excel, AI, MCP for price-based CPO path |
| `openspec/decisions/drr-cpo-price-semantics/decision.md` | drr-cpo-price-semantics (**Accepted**) | V1 hierarchical campaign `TARGET_CPO_RUB` from order value × DRR; catalog-price actuation blocked; aligns with `BoundedCpoProposal` / headroom types |
| `openspec/decisions/campaign-settings-changeset-ownership/decision.md` | campaign-settings-changeset-ownership (**Accepted**) | **Forbidden adapters** include Telegram UI apply for campaign ChangeSet; ad control uses parallel `AdControlChangeSetV1` in same package |

---

## Tests (evidence)

- `tests/unit/ad_control_settings/` — domain, persistence, resolver, diagnostics
- `tests/unit/wb_sky_control_plane/` — ad control dry-run (per design/tasks)
