---
cursor:
  subagentId: "bc-1e7e744b-70b5-51c7-b099-e3332ddead67"
---

# hierarchical-ad-control-settings — architecture planning

## CHANGE

`hierarchical-ad-control-settings` — canonical hierarchical settings/control model for WB Sky automatic advertising: per-function policies at SHOP and CAMPAIGN/ADV scopes, live inheritance (INHERIT | OVERRIDE | DISABLED), DRR/CPO headroom controller semantics, shared resolver for production and diagnostics. **Isolated** from `wb-sky-mcp-read-interface`, `decision-experiment-memory`, `campaign-settings-history`, `shop-wide campaign collection`.

## ARCHITECTURE_STATUS

Planning complete for owner review. **No implementation code.** OpenSpec scaffold: `openspec/changes/hierarchical-ad-control-settings/`.

## CURRENT_STATE

### FACT — Product control foundation (delivered, no PG persistence)

| Area | Location | State |
|------|----------|--------|
| Identity | `ProductRef(shop_id, nmid)` | **FACT** |
| Shop gate | `ShopControlEnrollment` NOT_ENROLLED \| ENROLLED \| BLOCKED | **FACT** |
| Product mode (whole-profile) | `ProductControlMode` INHERIT_SHOP \| OVERRIDE_ENABLED \| BLOCKED | **FACT** |
| DRR profile | `DrrProfile(target_drr_percent, max_drr_percent)` atomic | **FACT** |
| Effective DRR profile resolver | `EffectiveControlResolver` — product tier only today | **FACT** |
| DRR→static CPO | `ProductCpoResolver` pure math | **FACT** |
| Campaign binding | read-only projector, multi-nm fail-closed | **FACT** |
| Persistence | `ShopControlSettings` / `ProductControlSettings` | **NOT IMPLEMENTED** (`product-control-settings-persistence` concept) |

Precedence today (product foundation only): **PRODUCT override profile → SHOP profile → LEGACY_TIER** when shop ENROLLED; shop NOT_ENROLLED → LEGACY_NOT_ENROLLED; whole-profile inheritance only (**no per-function modes**).

### FACT — Campaign execution settings (legacy authority)

- `AdvSetting.target_price_for_order`, `max_price_for_order` (and related plan fields) are **current PG authority** for campaign CPO/plan execution (**FACT**).
- `campaign_settings_contract` registry classifies AdvSetting fields for history/Excel (**ACCEPTED_EXISTING_DECISION**).
- V3 auto_updater uses **campaign-local** `plan`/`fact`/`resolve` and env-driven PFO headroom ratios (`campaign_pfo_gates.py`) — **not** shop configured DRR hierarchy (**FACT**).
- Store-level DRR/headroom appears in **scripts** (`a1_whole_store_daily_drr_collect.py`, economics collectors) and AI package gaps (`store_drr` family) — **not** wired as canonical control loop (**FACT**).

### FACT — Control plane / writes

- `ChangeSetV1` + dry-run: `wb_sky_control_plane` (**ACCEPTED_EXISTING_DECISION**).
- Apply Authority V1: three `campaign.set_*_policy` PG ops only (**FACT**); legacy Telegram/Excel/shop-runner bypass remain (**FACT**).
- No `SET_SHOP_DRR_PROFILE` / automation registry ops in production yet (**FACT**; named in `product-control-surfaces` concept).

### FACT — DRR vocabulary split (partial)

- `configured` via `DrrProfile.target_drr_percent` / `max_drr_percent` at product foundation (**FACT** for static profile only).
- `actual_drr`: `compute_drr_fact` in `attribution_facts` / AI export (**FACT**); not unified with control resolver.
- `effective_control_drr`: **no canonical domain type** in repo (**EVIDENCE_GAP** for dynamic control-pressure path).

### ACCEPTED_EXISTING_DECISION — must not contradict

- `product-control-aggregate-ownership`: catalog vs control; future shop/product settings tables; AdvSetting not canonical DRR owner post-migration.
- `product-pricing-and-cpo-ownership`: `PRICE_SEMANTICS_ACCEPTED = NO` (**EVIDENCE_GAP** blocks runtime DRR→CPO adapter).
- `campaign-settings-contract-ownership`, `campaign-settings-changeset-ownership`, `changeset-apply-authority-ownership`.
- `mode-defaults-policy-ownership`: mode defaults in policy overlays — **not** a substitute for per-function automation registry.

### Explicit non-merge boundaries (Owner)

- **campaign-settings-history**: CH snapshots of **registered campaign settings fields** — consumer of registry; not owner of automation function registry.
- **shop-runner shop-wide collection**: data ingestion grain — feeds `actual_drr` inputs, not settings authority.
- **decision-experiment-memory** / **wb-sky-mcp-read-interface**: separate transports; must call same resolver/contracts when added.

## PROPOSED_MODEL

### Layering (NEW_PROPOSAL)

```text
app/modules/ad_control_settings/          # NEW package (name TBD — avoid collision with campaign_settings_contract)
  domain/
    feature_registry.py                   # AdControlFeatureId, schema, validation
    scope_mode.py                         # INHERIT | OVERRIDE | DISABLED per feature
    configured/                           # persisted intent (shop + campaign rows)
    resolved/                             # ResolvedAdControlSettings + ProvenanceEntry
    drr_semantics.py                      # configured_target / actual / effective_control DRR types
    headroom_policy.py                    # parameter model + pure evaluation (no I/O)
  application/
    AdControlSettingsResolver             # orchestrates loaders + pure steps
    diagnostics_service.py                # same resolver, read-only + proposed CPO trace
  ports/                                  # loaders for shop/campaign configured, metrics, CPO state
```

**Relationship to `product_control`:** extend, do not fork. Product scope remains `(shop_id, nmid)` with existing `EffectiveControlResolver` for **configured_target_drr profile** at PRODUCT tier. New registry **wraps** product + shop + campaign scopes for **all control functions**, mapping product-tier DRR profile into `configured_target_drr` feature params.

### Core types (NEW_PROPOSAL — names aligned to repo patterns)

| Concept | Proposed name | Notes |
|---------|---------------|--------|
| Feature id | `AdControlFeatureId` (StrEnum) | Versioned string ids; registry is SoT |
| Per-scope mode | `AdControlFeatureMode` | INHERIT \| OVERRIDE \| DISABLED |
| Configured bag | `ScopedAdControlConfiguration` | shop row + campaign row fragments keyed by feature |
| Resolved bag | `ResolvedAdControlState` | effective values + `ProvenanceV1` per field |
| Resolver | `AdControlSettingsResolver` | pure core + injected ports |

**Persist configured ≠ resolved:** campaign rows store only OVERRIDE payloads + mode flags; effective values computed on read/tick/diagnostic.

### DRR semantic triple (NEW_PROPOSAL — mandatory separation)

| Field | Meaning | Source |
|-------|---------|--------|
| `configured_target_drr` | Owner/business target % | Resolved from shop/product/campaign **configured_target_drr** feature |
| `actual_drr` | Observed % for measurement window | Metrics port (shop/campaign attribution); read-only |
| `effective_control_drr` | Runtime control setpoint / pressure input | Pure function of configured, actual, **dynamic_drr** feature params, headroom policy, data sufficiency |

Static `ProductCpoResolver` maps **configured** profile → baseline target/max CPO at product price. **Headroom controller** adjusts **effective** campaign CPO proposals relative to baseline — does not rewrite configured targets.

### Control function registry (NEW_PROPOSAL)

Each `AdControlFeatureId` entry defines:

- `supported_scopes: set[SHOP | PRODUCT | CAMPAIGN]` (PRODUCT optional per feature)
- `parameter_schema` (typed dataclass / pydantic internal — not transport)
- `validate_config(mode, payload) -> ValidationResult` (fail-closed)
- `resolve_inheritance(chain, modes) -> ConfiguredSlice | DISABLED`
- `capability_rules(snapshot) -> TriState` (reuse wb_sky pattern where write-related)

**V1 minimum features (Owner list):**

| FeatureId | Scope default | Role |
|-----------|---------------|------|
| `configured_target_drr` | SHOP + PRODUCT + CAMPAIGN | Business DRR target (may reuse `DrrProfile` shape) |
| `dynamic_drr_control` | SHOP + CAMPAIGN | Enables/maps actual→effective_control_drr |
| `cpo_increase_on_headroom` | SHOP + CAMPAIGN | Positive headroom expansion policy |
| `cpo_decrease_on_overspend` | SHOP + CAMPAIGN | Negative headroom contraction policy |
| `cpo_safety_bounds` | SHOP + CAMPAIGN | min/max/step caps on CPO mutations |

No global `automation_enabled` flag (**NEW_PROPOSAL**, Owner requirement).

## INHERITANCE_PRECEDENCE

### ACCEPTED_EXISTING_DECISION (product DRR profile — whole object)

When shop `ENROLLED`: CAMPAIGN **not in product model today** for DrrProfile — product path is PRODUCT > SHOP > LEGACY for **single profile object**.

### NEW_PROPOSAL — unified precedence per feature

For each `AdControlFeatureId`, resolve configured contribution:

```text
1. If scope CAMPAIGN mode == OVERRIDE → use campaign configured payload (validated)
2. If scope CAMPAIGN mode == DISABLED → feature off at campaign (effective disabled; provenance CAMPAIGN_DISABLED)
3. If scope CAMPAIGN mode == INHERIT → fall through
4. If feature supports PRODUCT and binding resolves single primary nmid:
     PRODUCT mode OVERRIDE → product payload
     PRODUCT DISABLED → off
     PRODUCT INHERIT → fall through
5. SHOP OVERRIDE → shop payload
6. SHOP DISABLED → off
7. SYSTEM_LEGACY_DEFAULT → registry default or LEGACY_TIER bridge (AdvSetting/plan fields) with provenance LEGACY
```

**Shop master gate (ACCEPTED):** `NOT_ENROLLED` / `BLOCKED` shop enrollment → automation features fail closed or LEGACY bridge per feature policy (**OWNER_DECISION_REQUIRED** for per-feature behavior under NOT_ENROLLED).

**Live inheritance:** campaign OVERRIDE stores only delta; changing shop shop-level value immediately affects INHERIT campaigns (**NEW_PROPOSAL**).

**Forbidden:** copying shop effective values into campaign columns as authority (**NEW_PROPOSAL**).

## CONTROL_FUNCTIONS

Initial registry entries (parameters as settings, not constants):

### `configured_target_drr`

- Params: `target_drr_percent`, `max_drr_percent` (reuse `DrrProfile` invariants)
- **ACCEPTED_EXISTING_DECISION:** atomic profile, no field-level mix at product resolver — campaign-level OVERRIDE still atomic profile per feature

### `dynamic_drr_control`

- Params: enable flag (via mode), mapping policy id, smoothing, caps on effective_control_drr delta vs configured
- Output: contributes to `effective_control_drr` computation only

### `cpo_increase_on_headroom` / `cpo_decrease_on_overspend`

- Params: see DRR_CONTROLLER_MODEL
- Operate on **proposed CPO delta** per campaign/keyword policy (bounded, deterministic allocation — **not** uniform % across campaigns)

### `cpo_safety_bounds`

- Params: absolute min/max CPO, max step up/down per tick, relationship to `AdvSetting.max_price_for_order` during migration

## DRR_CONTROLLER_MODEL

Pure `HeadroomEvaluation` (NEW_PROPOSAL) inputs:

- `configured_target_drr` (shop scope for store headroom; campaign scope optional overlay)
- `actual_drr`, `measurement_window`, `data_sufficiency`, `attribution_lag_policy`
- spend, GMV (or allowed spend budget) for headroom rubles
- deadband/hysteresis around target
- `min_positive_headroom_before_increase`, `max_increase_per_iteration`, `max_decrease_per_iteration`
- `cooldown_ticks` / `cooldown_duration`
- stale/insufficient data → **fail closed** (no increase; decrease policy **OWNER_DECISION_REQUIRED**)

Outputs:

- `headroom_rub` (signed)
- `control_pressure` (normalized bounded scalar)
- `effective_control_drr` (optional override of static target for controller)
- `reason_codes[]` (deterministic)
- `blockers[]`

**Feedback loop (Owner):** configured shop DRR → actual shop DRR → headroom/pressure → effective policy → resolved campaign settings → target/max CPO proposal → ChangeSet dry-run → Apply Authority.

**Alignment with V3 (FACT):** today `COST_REALLOCATION` / PFO gates use campaign `fact` vs `resolve` — migration slice must map legacy `resolve` to resolver output or dual-run compare (**NEW_PROPOSAL** migration risk).

## DIAGNOSTICS_MODEL

`AdControlDiagnosticsReportV1` (NEW_PROPOSAL) — same `AdControlSettingsResolver` + headroom pure functions:

- Inputs: `shop_id`, optional `adv_id`, as-of timestamp, measurement window override (read-only)
- Sections: configured / inherited / effective tables per feature; DRR triple; sufficiency; headroom; current CPO; `proposed_cpo`; decision enum; reason codes; blockers; optional ChangeSet dry-run diff (delegate `wb_sky_control_plane.dry_run`)
- Transport: dedicated API/MCP/Telegram view later — **no second calculator**
- Production writes: **forbidden** in diagnostic mode (hard guard)

## PERSISTENCE_IMPACT

| Store | NEW_PROPOSAL |
|-------|----------------|
| `shop_ad_control_settings` | `shop_id`, version, JSONB or normalized rows per feature mode + payload |
| `campaign_ad_control_settings` | `adv_id` or `cmp_*` ref, per-feature mode + override payload only |
| Reuse `product_control` persistence change | Extend `ProductControlSettings` with per-feature modes OR keep DrrProfile columns as configured_target_drr product override (**OWNER_DECISION_REQUIRED**) |
| Resolved state | **Not persisted** as authority (optional cache with TTL for UI only, labeled non-authoritative) |
| History | New features registered in `campaign_settings_contract` only if mapped to AdvSetting legacy fields; pure automation params may need **new registry source** ADR (**NEW_PROPOSAL**) |

Alembic: separate from `campaign-settings-history` CH pipeline.

## UI_MODEL

Single human section **«Advertising Control» / «Automation Settings»** (NEW_PROPOSAL):

- **Shop settings:** all shop-scoped features in one screen
- **Campaign table:** one row per campaign; columns per feature: mode, configured, effective, source, action «return to inherit»
- Excel: projection/export only; mutations via ChangeSet/Apply when wired
- Does not replace Telegram campaign edit for unrelated fields

## AI_CONTROL_PLANE_IMPACT

Extend AI Package / future MCP read models (NEW_PROPOSAL):

- `configured_settings`, `effective_settings`, `inheritance_source`, `capabilities`, `control_state`, `diagnostic_reason_codes`
- Read via resolver ports + existing `wb_sky_control_plane` read snapshot where campaign-bound
- Mutations: new ChangeSet operation family `ad_control.set_feature` (future change) → Apply Authority
- **ACCEPTED:** LLM never production-writes; unknown feature fail-closed

## EVIDENCE_GAPS

| Gap | Impact |
|-----|--------|
| `PRICE_SEMANTICS_ACCEPTED = NO` | Blocks end-to-end DRR→CPO runtime (**ACCEPTED_EXISTING_DECISION**) |
| No `effective_control_drr` type/runtime | Dynamic loop unspecified in code |
| Shop-wide `actual_drr` SoT for control tick | Scripts vs attribution_facts vs shop-runner — pick authoritative reader |
| Campaign-level vs shop-level headroom allocation algorithm | Deterministic bounded split not specified |
| NOT_ENROLLED shop: per-feature LEGACY vs blocked | Owner matrix incomplete |
| Whether new settings are new PG tables vs extension of future `ShopControlSettings` | DDL ownership vs this change |

## OWNER_DECISIONS

1. Under `ShopControlEnrollment.NOT_ENROLLED`, do automation features expose LEGACY bridge per feature or global LEGACY_NOT_ENROLLED only?
2. Product scope: mandatory in precedence for all features or only `configured_target_drr`?
3. Campaign anchor: `adv_id` vs `CampaignResourceRef` / complex adv pair — single row per complex?
4. Persist product per-feature modes in same table as `DrrProfile` or generic JSON feature map?
5. Headroom allocation: proportional to spend, planned sales, or explicit weights table?
6. Stale actual_drr: block increases only vs also force decreases?
7. Accept deferring `dynamic_drr_control` implementation until price semantics accepted?

## IMPLEMENTATION_SLICES

### CRITICAL

1. **Domain registry + resolver (pure)** — feature ids, modes, precedence, provenance, validation tests
2. **DRR triple + headroom pure model** — reason codes, fail-closed matrix
3. **Diagnostics report using production resolver** — no writes

### HIGH

4. **Persistence ADR + schema** (coordinate `product-control-settings-persistence` — extend, don't duplicate)
5. **ChangeSet / capability extension design** (dry-run ops for shop/campaign automation settings)
6. **Legacy bridge** — map resolved CPO bounds ↔ AdvSetting fields for V3 tick

### MEDIUM

7. **UI projection** (Telegram section v1)
8. **AI Package export section** for effective/configured automation
9. **V3 executor integration** behind feature flags — per-function enablement

### LOW

10. Excel template columns for automation settings
11. MCP read transport wiring (separate change)

## FINAL_STATUS

**ARCHITECTURE_READY_FOR_OWNER_REVIEW**

No **BLOCKED_CONFLICT** with accepted ADRs if: (a) product tier retained in precedence, (b) campaign settings contract remains classification owner for AdvSetting columns, (c) new automation registry owns per-function semantics, (d) Apply Authority remains write gate.
