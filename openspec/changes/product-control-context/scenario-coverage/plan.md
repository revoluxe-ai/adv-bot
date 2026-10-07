# Scenario Coverage Plan

CHANGE_ID: product-control-context
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: PCC-SCP-20261007-002
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
SCENARIOS_TOTAL: 22

| ID | Title | Primary seam | Slice |
|----|-------|--------------|-------|
| S01 | One product → Auto + Search bindings | Binding projector | B |
| S02 | One product → multiple campaign complexes | Binding projector | B |
| S03 | Single-nm complex resolves control product safely | Resolver policy | A |
| S04 | Multi-nm complex fails closed for derived CPO | Adapter policy | D |
| S05 | main_nmid cannot establish PRIMARY | Binding projector | B |
| S06 | Shop NOT_ENROLLED → legacy CPO unchanged | Adapter | D |
| S07 | INHERIT_SHOP uses shop DrrProfile | EffectiveControlResolver | A/D |
| S08 | OVERRIDE_ENABLED uses product DrrProfile | EffectiveControlResolver | E |
| S09 | ENROLLED shop, no profiles → LEGACY tier | EffectiveControlResolver | A |
| S10 | Invalid target>max profile rejected | Validation | A/C |
| S11 | Missing price blocks derived CPO | ProductCpoResolver | D |
| S12 | Stale/unknown price no fabricated CPO | PricingReader | D |
| S13 | Zero shop ENROLLED → zero behavior change | Deployment invariant | C/D |
| S14 | Rollout + ambiguous multi-nm → BLOCKED | Adapter | D |
| S15 | BLOCKED ≠ LEGACY_NOT_ENROLLED | Adapter | D |
| S16 | wb_common_stat not used as price | Port boundary | A |
| S17 | Auto/Search physical state separate | Bindings | B |
| S18 | Empty settings → shop NOT_ENROLLED defaults | Integration | C |
| S19 | Product OVERRIDE cannot bypass shop NOT_ENROLLED | Enrollment gate | A/D |
| S20 | Shop BLOCKED beats product OVERRIDE | Enrollment gate | A/D |
| S21 | OVERRIDE_ENABLED without product profile invalid | Validation | A/C |
| S22 | Domain max CPO 0.01 RUB; legacy int in adapter | ProductCpoResolver / adapter | A/D |

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

GIVEN nmids=[N1,N2] and shop ENROLLED with effective DRR
WHEN product-derived CPO requested
THEN `PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS`

### S05 — main_nmid not authority

GIVEN nmids=[N2,N1] sorted so main_nmid=N1
WHEN assigning PRIMARY
THEN PRIMARY MUST NOT be set solely because N1 is main_nmid

### S06 — Shop not enrolled legacy

GIVEN shop ShopControlEnrollment NOT_ENROLLED
WHEN adapter resolves pay-for-order
THEN uses AdvSetting legacy fields only (`LEGACY_NOT_ENROLLED`)

### S07 — INHERIT_SHOP uses shop profile

GIVEN shop ENROLLED with shop DrrProfile P
AND product (S,N) ProductControlMode INHERIT_SHOP
WHEN effective DRR resolved
THEN effective profile P

### S08 — OVERRIDE_ENABLED product profile

GIVEN shop ENROLLED with shop profile P1
AND product OVERRIDE_ENABLED with product profile P2
WHEN effective DRR resolved
THEN P2 (atomic override)

### S09 — Enrolled shop no DRR profiles → LEGACY

GIVEN shop ENROLLED
AND product INHERIT_SHOP
AND no shop DrrProfile and no product DrrProfile
WHEN effective control resolved
THEN LEGACY tier (campaign CPO fields), not zero, not BLOCKED

### S10 — Profile invariant

GIVEN target_drr > max_drr
WHEN save profile
THEN validation error

### S11 — Missing price

GIVEN shop ENROLLED with effective DRR
AND pricing unavailable
WHEN ProductCpoResolver runs
THEN `BLOCKED_BY_PRODUCT_PRICE_SOURCE`

### S12 — Stale price

GIVEN pricing returns STALE/UNKNOWN per policy
WHEN resolver runs
THEN blocked, no CPO fabrication

### S13 — Zero shop enrollment deploy

GIVEN migrations applied, no shop ShopControlEnrollment ENROLLED
WHEN shop-runner tick
THEN identical legacy CPO path

### S14 — Blocked on ambiguity

GIVEN shop ENROLLED + multi-nm without control SKU
WHEN adapter invoked
THEN `PRODUCT_CONTROL_BLOCKED`

### S15 — No silent legacy on block

GIVEN PRODUCT_CONTROL_BLOCKED outcome
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

### S18 — Empty settings defaults

GIVEN no ShopControlSettings rows
WHEN resolver loads
THEN shop NOT_ENROLLED and product INHERIT_SHOP defaults

### S19 — Shop gate blocks product override

GIVEN shop NOT_ENROLLED
AND product OVERRIDE_ENABLED with valid product DrrProfile
WHEN runtime resolves outcome
THEN LEGACY_NOT_ENROLLED; product-control path MUST NOT activate

### S20 — Shop BLOCKED beats product override

GIVEN shop BLOCKED
AND product OVERRIDE_ENABLED with valid product DrrProfile
WHEN runtime resolves outcome
THEN PRODUCT_CONTROL_BLOCKED

### S21 — Override without profile invalid

GIVEN shop ENROLLED
WHEN write sets OVERRIDE_ENABLED without product DrrProfile
THEN validation failure at write
AND if invalid row read at runtime THEN configuration-invalid / blocked

### S22 — Domain money vs legacy int

GIVEN effective price and DrrProfile
WHEN ProductCpoResolver runs
THEN target and max canonical at 0.01 RUB ROUND_HALF_UP
AND LegacyCampaignCpoAdapter alone converts max to AdvSetting int

## Traceability

- Spec: `specs/product-control-context/spec.md`
- Tasks: Slice A = S03,S07,S09,S10,S16,S19-S21,S22; B = S01,S02,S05,S17; C = S13,S18,S21; D = S04,S06,S11,S12,S14,S15,S19,S20,S22; E = S08
