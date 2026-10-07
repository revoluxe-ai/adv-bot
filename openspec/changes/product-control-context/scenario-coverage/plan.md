# Scenario Coverage Plan

CHANGE_ID: product-control-context
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: PCC-SCP-20261007-001
LIFECYCLE_STATUS: DERIVED

Planning evidence only — does not assert apply/archive PASS.

## Architecture Decision References

- `openspec/changes/product-control-context/decisions/product-control-aggregate-ownership/decision.md`
- `openspec/changes/product-control-context/decisions/campaign-product-binding-ownership/decision.md`
- `openspec/changes/product-control-context/decisions/product-pricing-and-cpo-ownership/decision.md`
- `openspec/decisions/strict-single-nmid-audit-evidence/decision.md`

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: product-control-context
SCENARIOS_TOTAL: 18

| ID | Title | Primary seam | Slice |
|----|-------|--------------|-------|
| S01 | One product → Auto + Search bindings | Binding projector | B |
| S02 | One product → multiple campaign complexes | Binding projector | B |
| S03 | Single-nm complex resolves control product safely | Resolver policy | A |
| S04 | Multi-nm complex fails closed for derived CPO | Adapter policy | D |
| S05 | main_nmid cannot establish PRIMARY | Binding projector | B |
| S06 | NOT_ENROLLED → legacy CPO unchanged | Adapter | D |
| S07 | Shop DRR applies when no SKU profile | EffectiveControlResolver | A/D |
| S08 | SKU DRR overrides shop atomically | EffectiveControlResolver | E |
| S09 | NULL profile inherits (not zero) | EffectiveControlResolver | A |
| S10 | Invalid target>max profile rejected | Validation | A/C |
| S11 | Missing price blocks derived CPO | ProductCpoResolver | D |
| S12 | Stale/unknown price no fabricated CPO | PricingReader | D |
| S13 | Zero enrollment → zero behavior change | Deployment invariant | C/D |
| S14 | ENROLLED + ambiguous → PRODUCT_CONTROL_BLOCKED | Adapter | D |
| S15 | ENROLLED blocked ≠ LEGACY_NOT_ENROLLED | Adapter | D |
| S16 | wb_common_stat not used as price | Port boundary | A |
| S17 | Auto/Search physical state separate | Bindings | B |
| S18 | Deployment tables empty → legacy only | Integration | C |

## Scenario details (GIVEN/WHEN/THEN)

### S01 — One product → Auto + Search bindings

GIVEN ComplexAdv with auto adv_id A, search adv_id B, single nmid N  
WHEN projector runs for shop S  
THEN bindings include (S, A, AUTO, N) and (S, B, SEARCH, N)

### S02 — One product → multiple complexes

GIVEN N on two adv_setting rows in shop S  
WHEN listing bindings for (S, N)  
THEN count ≥ 2 with distinct adv_setting_id or physical_adv_id

### S03 — Single-nm safe resolve

GIVEN nmids=[N] only  
WHEN control product resolved  
THEN (S, N) is unambiguous

### S04 — Multi-nm fail closed

GIVEN nmids=[N1,N2] and enrollment active  
WHEN product-derived CPO requested  
THEN `PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS`

### S05 — main_nmid not authority

GIVEN nmids=[N2,N1] sorted so main_nmid=N1  
WHEN assigning PRIMARY  
THEN PRIMARY MUST NOT be set solely because N1 is main_nmid

### S06 — Legacy not enrolled

GIVEN enrollment NOT_ENROLLED  
WHEN adapter resolves pay-for-order  
THEN uses AdvSetting legacy fields only (`LEGACY_NOT_ENROLLED`)

### S07 — Shop profile inheritance

GIVEN shop ENROLLED with profile P, product without profile  
WHEN effective DRR resolved  
THEN profile P

### S08 — SKU override

GIVEN shop P1, product P2  
WHEN effective DRR resolved for product  
THEN P2 (full atomic profile)

### S09 — NULL inherit

GIVEN no SKU profile, no shop profile, not legacy tier trigger  
WHEN resolving enrolled shop without shop profile  
THEN LEGACY tier (campaign fields), not zero DRR

### S10 — Profile invariant

GIVEN target_drr > max_drr  
WHEN save profile  
THEN validation error

### S11 — Missing price

GIVEN enrolled + effective DRR + pricing unavailable  
WHEN ProductCpoResolver runs  
THEN `BLOCKED_BY_PRODUCT_PRICE_SOURCE`

### S12 — Stale price

GIVEN pricing returns STALE/UNKNOWN per policy  
WHEN resolver runs  
THEN blocked, no CPO fabrication

### S13 — Zero enrollment deploy

GIVEN migrations applied, all enrollment NOT_ENROLLED  
WHEN shop-runner tick  
THEN identical legacy CPO path

### S14 — Blocked on ambiguity

GIVEN ENROLLED + multi-nm  
WHEN adapter invoked  
THEN `PRODUCT_CONTROL_BLOCKED`

### S15 — No silent legacy on block

GIVEN ENROLLED + blocked  
WHEN adapter invoked  
THEN MUST NOT read legacy target_price as fallback

### S16 — Sales economics boundary

GIVEN sales reader returns revenue/order from wb_common_stat  
WHEN ProductCpoResolver invoked  
THEN sales reader output unused

### S17 — Leg separation

GIVEN search leg paused, auto active  
WHEN bindings exported  
THEN leg_role and physical_adv_id reflect distinct state

### S18 — Empty settings tables

GIVEN no ShopControlSettings rows  
WHEN resolver loads  
THEN NOT_ENROLLED defaults

## Traceability

- Spec: `specs/product-control-context/spec.md`
- Tasks: Slice A = S03,S09,S10,S16; B = S01,S02,S05,S17; C = S13,S18; D = S04,S06,S07,S11,S12,S14,S15; E = S08
