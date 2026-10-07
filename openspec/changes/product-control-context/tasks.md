# Tasks: product-control-context

Planning / domain apply only. No runtime until explicit slice GO.

## Slice A — Domain vocabulary + ports (no PG, no runtime)

- [ ] 1.1 Create `app/modules/product_control/domain/` package with module docstrings.
- [ ] 1.2 Add `ProductRef(shop_id, nmid)`, `DrrProfile`, `ShopControlEnrollment`, `ProductControlMode`.
- [ ] 1.3 Add ports: `ProductPricingReader`, `ProductSalesEconomicsReader`,
      `EffectiveControlResolver`, `ProductCpoResolver` (protocols).
- [ ] 1.4 Add `CampaignProductBinding`, `MembershipRole`, `LegRole`, blocker reason codes.
- [ ] 1.5 Implement pure `ProductCpoResolver` math + `EffectiveControlResolver` LEGACY/SKU/SHOP tiers (no I/O).
- [ ] 1.6 Unit tests: profile inheritance, NULL inherit, invariants, CPO rounding, blockers.
- [ ] 1.7 Unit tests: multi-nm ambiguity policy (pure policy helpers).

## Slice B — Binding projector (read-only)

- [ ] 2.1 Implement `CampaignProductBindingProjector` from `AdvSetting` + `ComplexAdv` shape.
- [ ] 2.2 Map Auto and Search legs to separate bindings with provenance `PG_NMIDS`.
- [ ] 2.3 Never assign PRIMARY from `main_nmid`; set UNKNOWN for multi-nmid complexes.
- [ ] 2.4 Unit tests: Auto+Search, one product→many complexes, multi-nm ambiguous.

## Slice C — Persistence (no runtime adapter)

- [ ] 3.1 Design Alembic models `ShopControlSettings`, `ProductControlSettings` (separate DDL change GO).
- [ ] 3.2 Repositories keyed `shop_id` and `(shop_id, nmid)`; default `NOT_ENROLLED`.
- [ ] 3.3 Integration tests with PG (enrollment defaults only).

## Slice D — First behavior change (shop DRR path)

- [ ] 4.1 Implement `ProductPricingReader` per accepted ADR C evidence closure.
- [ ] 4.2 Wire enrolled shop DRR → `ProductCpoResolver` → campaign adapter (feature flag + enrollment).
- [ ] 4.3 Preserve `LEGACY_NOT_ENROLLED`; map `PRODUCT_CONTROL_BLOCKED` without silent fallback.
- [ ] 4.4 Shop-runner tests: enrolled shop, single-nm complex, price present/missing.

## Slice E — SKU override

- [ ] 5.1 Product-level `DrrProfile` override atop shop profile.
- [ ] 5.2 Tests: SKU overrides shop; NULL product profile inherits shop.

## Slice F — Surfaces (separate GOs)

- [ ] 6.1 ChangeSet schema stubs `SET_SHOP_DRR_PROFILE`, `SET_PRODUCT_DRR_PROFILE` (no Apply).
- [ ] 6.2 `ProductControlContextV1` assembler (read-only export).
- [ ] 6.3 UI/Excel deferred subtasks per surface owner.

## Planning / governance (this change)

- [x] P.1 OpenSpec change artifacts + decisions
- [x] P.2 Scenario coverage plan
- [ ] P.3 `/opsx-planning-review` before Slice A apply GO
- [ ] P.4 Promote decisions to `openspec/decisions/` on archive
