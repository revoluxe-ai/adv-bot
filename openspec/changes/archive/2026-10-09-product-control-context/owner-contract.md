# Owner Contract: product-control-context (foundation archive)

## Owner intent

Deliver **product control foundation** in `app/modules/product_control/` without
changing campaign runtime economics.

## Delivered semantics (Slices A–B)

- Control anchor `(shop_id, nmid)`; WBCard not mutable control store.
- `ShopControlEnrollment` / `ProductControlMode` vocabulary + `EffectiveControlResolver`.
- Atomic `DrrProfile` + `ProductCpoResolver` pure math (0.01 RUB).
- `ProductPricingReader` / `ProductSalesEconomicsReader` ports (no adapters).
- `CampaignProductBinding` + read-only projector; Auto/Search legs; no `main_nmid` authority.
- Multi-nm fail-closed policy helpers.

## Owner scope decision (2026-10-09)

**OPTION A — FOUNDATION ONLY.** Slices A–B are the implemented boundary of this change.
Persistence, runtime, and surfaces are **separate future OpenSpec changes**.

## Dormant profile semantics (future persistence)

DRR profiles are configuration data independent of activation. Storing a profile while
`NOT_ENROLLED` / `BLOCKED` / non-override modes is allowed; ineffective until explicit
enrollment/mode transition with validation. No write-on-read; no auto-delete on state change.

## Absent-row defaults (future persistence)

- No shop row → logical `NOT_ENROLLED`.
- No product row → logical `INHERIT_SHOP`.
- Logical defaults only; no materialized default rows required.

## Out of scope (not delivered)

- Migrations, repositories, shop-runner wiring, price adapter, ChangeSet product ops,
  Apply integration, `ProductControlContextV1` runtime assembler, deploy.

## Owner acceptance (archive)

1. Foundation spec + scenario certification truthful for A–B.
2. ADRs promoted with pricing `EVIDENCE_GAP` preserved.
3. `PRICE_SEMANTICS_ACCEPTED` remains **NO**.
