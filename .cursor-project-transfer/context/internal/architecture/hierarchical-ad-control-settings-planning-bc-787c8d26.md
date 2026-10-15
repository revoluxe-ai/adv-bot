---
cursor:
  subagentId: "bc-787c8d26-1c03-557c-acf0-f99bf2b65b62"
---

# hierarchical-ad-control-settings — architecture planning (verified)

Cross-link: prior consolidated draft
[`hierarchical-ad-control-settings.md`](./hierarchical-ad-control-settings.md) (subagent `bc-1e7e744b`).

Slice A implemented: `app/modules/ad_control_settings/`, OpenSpec change
`openspec/changes/hierarchical-ad-control-settings/`, branch
`cursor/hierarchical-ad-control-settings-5b62` @ `89e6b48e0`.

## CHANGE

`hierarchical-ad-control-settings` — canonical hierarchical automation settings for
WB Sky: per-function policies at SHOP and CAMPAIGN/ADV (and compatible PRODUCT
tier), live INHERIT | OVERRIDE | DISABLED, DRR triple semantics, headroom/CPO
controller (design only), single resolver for production + diagnostics.

**Isolated from:** `wb-sky-mcp-read-interface`, `decision-experiment-memory`,
`campaign-settings-history`, shop-wide campaign collection.

## ARCHITECTURE_STATUS

Planning complete. **ARCHITECTURE_READY_FOR_OWNER_REVIEW**. No product code.

## CURRENT_STATE

| Item | Classification |
|------|----------------|
| `app/modules/product_control/` Slices A–B: `EffectiveControlResolver`, `DrrProfile`, `ProductCpoResolver`, binding projector | **FACT** |
| Product modes: whole-profile `INHERIT_SHOP` \| `OVERRIDE_ENABLED` \| `BLOCKED` only (not per-function) | **FACT** |
| Precedence for DRR profile: PRODUCT → SHOP → LEGACY when shop ENROLLED | **ACCEPTED_EXISTING_DECISION** (`openspec/specs/product-control-context/spec.md`) |
| `ShopControlSettings` / `ProductControlSettings` PG | **FACT** not implemented (`openspec/evolution/product-control-context-future-boundaries.md`) |
| Campaign CPO authority: `AdvSetting.target_price_for_order`, `max_price_for_order` | **FACT** |
| V3 PFO gates: campaign `fact`/`resolve` + env ratios (`campaign_pfo_gates.py`) | **FACT** — not shop configured DRR hierarchy |
| `compute_drr_fact` in `attribution_facts` | **FACT** — analytics grain, not control resolver |
| `ChangeSetV1` dry-run + Apply V1 (three `set_*_policy` ops) | **ACCEPTED_EXISTING_DECISION** |
| `campaign_settings_contract` field registry | **ACCEPTED_EXISTING_DECISION** |
| Shop DRR in scripts / AI `SHOP_DRR` blockers | **FACT** — not canonical control loop |
| `effective_control_drr` domain type | **EVIDENCE_GAP** |
| `PRICE_SEMANTICS_ACCEPTED = NO` | **ACCEPTED_EXISTING_DECISION** (`product-pricing-and-cpo-ownership`) |

## PROPOSED_MODEL

New domain package (name TBD, e.g. `ad_control_settings`) **extends** `product_control`:

- **Registry:** `AdControlFeatureId`, per-feature parameter schemas, scope support,
  deterministic validation, capability/fail-closed rules.
- **Modes:** `AdControlFeatureMode` = INHERIT \| OVERRIDE \| DISABLED **per feature**
  at campaign (and shop); product tier reuses/extends `ProductControlMode` for
  `configured_target_drr` or generic feature map (**OWNER_DECISION_REQUIRED**).
- **Configured vs resolved:** persist modes + override payloads only; `ResolvedAdControlState`
  + `ProvenanceV1` per effective field; no copy-on-write inheritance.
- **DRR triple (mandatory):**
  - `configured_target_drr` — business target from resolved feature params
  - `actual_drr` — metrics port (shop/campaign window)
  - `effective_control_drr` — pure output of `dynamic_drr_control` + headroom policy
- **CPO:** static baseline via existing `ProductCpoResolver`; headroom features
  adjust **proposed** CPO deltas only (**NEW_PROPOSAL**).

## INHERITANCE_PRECEDENCE

**NEW_PROPOSAL** per feature:

```text
CAMPAIGN OVERRIDE → CAMPAIGN DISABLED → CAMPAIGN INHERIT
  → PRODUCT (if supported) OVERRIDE → DISABLED → INHERIT
  → SHOP OVERRIDE → DISABLED → INHERIT
  → SYSTEM / LEGACY (registry default or AdvSetting bridge)
```

**ACCEPTED_EXISTING_DECISION:** shop `NOT_ENROLLED` / `BLOCKED` master gate;
**OWNER_DECISION_REQUIRED:** per-feature LEGACY bridge vs hard block when NOT_ENROLLED.

**ACCEPTED_EXISTING_DECISION:** atomic `DrrProfile` inheritance at product layer
(no field-level mix) — campaign `configured_target_drr` OVERRIDE remains atomic profile.

## CONTROL_FUNCTIONS

Minimum V1 registry (**NEW_PROPOSAL**, Owner list):

| FeatureId | Notes |
|-----------|--------|
| `configured_target_drr` | Reuse `DrrProfile` invariants |
| `dynamic_drr_control` | actual → `effective_control_drr` |
| `cpo_increase_on_headroom` | positive headroom expansion |
| `cpo_decrease_on_overspend` | negative headroom contraction |
| `cpo_safety_bounds` | steps, absolutes, migration vs `max_price_for_order` |

No global automation master flag (**NEW_PROPOSAL**).

## DRR_CONTROLLER_MODEL

Pure `HeadroomEvaluation` (**NEW_PROPOSAL**): configured vs actual shop DRR,
measurement window, data sufficiency, attribution lag, deadband/hysteresis,
min headroom before increase, max increase/decrease per iteration, cooldown,
absolute CPO bounds, stale-data fail-closed. Outputs: signed headroom, control
pressure, optional `effective_control_drr`, reason codes, blockers. Allocation
across campaigns: bounded, deterministic, **not** uniform % (**OWNER_DECISION_REQUIRED**
on algorithm).

Loop: configured → actual → headroom → effective policy → resolved campaign →
CPO proposal → ChangeSet dry-run → Apply Authority.

## DIAGNOSTICS_MODEL

`AdControlDiagnosticsReportV1` (**NEW_PROPOSAL**): same resolver + headroom pure
functions; optional `wb_sky_control_plane.dry_run` diff; **no production writes**.

## PERSISTENCE_IMPACT

Shop + campaign settings tables (or extend future `ShopControlSettings` /
`ProductControlSettings`); resolved state not authoritative in PG; new registry
source may be needed beyond `AdvSetting` columns (**NEW_PROPOSAL** ADR).

## UI_MODEL

Single «Advertising Control» / «Automation Settings»: shop panel + campaign table
(mode, configured, effective, source, return-to-inherit). Excel projection only.

## AI_CONTROL_PLANE_IMPACT

Read: configured/effective, provenance, capabilities, control state, reason codes
via resolver ports. Write: future ChangeSet ops → Apply Authority. **ACCEPTED_EXISTING_DECISION:**
LLM intent only; unknown fail-closed.

## EVIDENCE_GAPS

- Price semantics / DRR→CPO runtime adapter
- Authoritative `actual_drr` reader for shop-runner tick vs attribution_facts
- `effective_control_drr` specification
- Headroom split across campaigns
- NOT_ENROLLED per-feature behavior
- DDL: generic feature map vs typed columns

## OWNER_DECISIONS

1. NOT_ENROLLED: per-feature LEGACY vs global gate
2. PRODUCT in precedence for all features vs DRR-only
3. Campaign key: `adv_id` vs complex / `CampaignResourceRef`
4. Product persistence: `DrrProfile` columns vs feature JSON map
5. Headroom allocation algorithm
6. Stale `actual_drr`: block increase only vs force decrease
7. Defer `dynamic_drr_control` until price semantics accepted?

## MIGRATION / COMPATIBILITY RISKS

| Risk | Classification |
|------|----------------|
| Dual authority: new resolver vs `AdvSetting` CPO until bridge + enrollment | **NEW_PROPOSAL** — dual-run compare slice |
| V3 executors assume campaign-local `resolve`/`fact`, env PFO ratios | **FACT** — map legacy `resolve` to resolver output |
| Whole-profile `ProductControlMode` vs per-function modes at product tier | **NEW_PROPOSAL** — extend without breaking `EffectiveControlResolver` |
| `campaign_settings_history` CH snapshots only registered AdvSetting fields | **ACCEPTED_EXISTING_DECISION** — new automation params need registry source ADR |
| Shop-wide collection feeds metrics only; not settings SoT | **FACT** (Owner non-merge boundary) |
| `PRICE_SEMANTICS_ACCEPTED = NO` blocks full DRR→CPO runtime | **EVIDENCE_GAP** |

## IMPLEMENTATION_SLICES

**CRITICAL:** pure registry + resolver + provenance; DRR triple + headroom pure
model; diagnostics on same resolver.

**HIGH:** persistence ADR (coordinate `product-control-settings-persistence`);
ChangeSet extension design; legacy AdvSetting bridge for V3.

**MEDIUM:** UI projection; AI export section; V3 integration behind flags.

**LOW:** Excel columns; MCP transport (separate change).

## FINAL_STATUS

**ARCHITECTURE_READY_FOR_OWNER_REVIEW** — no **BLOCKED_CONFLICT** if product tier
preserved, `campaign_settings_contract` stays field classifier, automation registry
owns per-function semantics, Apply Authority stays write gate.
