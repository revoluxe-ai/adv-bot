# Owner Contract: product-control-context

## Owner intent

Introduce a **product-oriented control foundation** for WB Sky without rewriting the
campaign runtime. Canonical control identity is **`(shop_id, nmid)`**. WBCard remains
catalog/metadata authority only. Campaigns remain execution entities.

DRR-based control MUST use **current/effective product price**, not historical
`wb_common_stat` revenue/order aggregates, as implicit price authority.

## Required semantics

- **Control anchor**: `(shop_id, nmid)` for mutable product control; `shop_id` alone
  for shop defaults.
- **WBCard**: catalog identity, WB card JSON cache, category reference — **MUST NOT**
  accumulate mutable control fields (DRR, enrollment, derived CPO).
- **Shop rollout** — `ShopControlEnrollment`: `NOT_ENROLLED` | `ENROLLED` | `BLOCKED`
  (default `NOT_ENROLLED`). **Master gate** for the shop.
- **Product mode** — `ProductControlMode`: `INHERIT_SHOP` | `OVERRIDE_ENABLED` |
  `BLOCKED` (default `INHERIT_SHOP`). **MUST NOT** overload shop enrollment or use
  product `NOT_ENROLLED` to mean inheritance.
- **Pricing split**:
  - `ProductPricingReader` — authoritative **current/effective** unit price for control.
  - `ProductSalesEconomicsReader` — historical orders/GMV/revenue-per-order for
    analytics/capacity; `wb_common_stat` allowed here only.
- **DRR profile**: atomic `DrrProfile { target_drr_percent, max_drr_percent }`;
  inheritance replaces **whole profile** at each tier; **no** field-level mix.
- **NULL / missing profile** at a tier means **inherit**; MUST NOT mean zero.
- **DRR→CPO** (when price available): single `ProductCpoResolver`; canonical money at
  **0.01 RUB** for target and max; legacy int max via `LegacyCampaignCpoAdapter` only.
- **Campaign bindings**: PRIMARY MUST NOT be inferred from `main_nmid` or `sorted(nmids)[0]`.
- **Multi-nmid fail-closed**: `PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS` when no single
  control product is proven.
- **OVERRIDE_ENABLED** without product `DrrProfile`: invalid at write time; if read,
  fail closed (configuration-invalid / blocked) — MUST NOT silently equal `INHERIT_SHOP`.
- **Legacy vs blocked**: see effective enrollment matrix below.

### Effective enrollment matrix

| Shop enrollment | Product mode | Profiles | Runtime outcome |
|-----------------|--------------|----------|-----------------|
| NOT_ENROLLED | INHERIT_SHOP | any | `LEGACY_NOT_ENROLLED` |
| NOT_ENROLLED | OVERRIDE_ENABLED | product profile present | `LEGACY_NOT_ENROLLED` (no bypass) |
| NOT_ENROLLED | BLOCKED | any | `LEGACY_NOT_ENROLLED` |
| ENROLLED | INHERIT_SHOP | shop P | effective DRR = P |
| ENROLLED | INHERIT_SHOP | no shop, no product profile | LEGACY tier (campaign CPO) |
| ENROLLED | OVERRIDE_ENABLED | product P | effective DRR = P |
| ENROLLED | OVERRIDE_ENABLED | no product profile | invalid write; if read → blocked |
| ENROLLED | BLOCKED | any | `PRODUCT_CONTROL_BLOCKED` |
| BLOCKED | any | any | `PRODUCT_CONTROL_BLOCKED` |

No product mode may override shop `NOT_ENROLLED` or shop `BLOCKED`.

- **Category**: precedence `PRODUCT > CATEGORY > SHOP` documented; **no** category
  runtime in this change.

## Out of scope

- Attribution-facts, decision-experiment-memory, ChangeSet Apply Authority, MCP deploy,
  runtime code, migrations, AutoShelf migration.

## Owner acceptance

1. OpenSpec change validates strict; enrollment matrix and money boundary documented.
2. Scenario plan covers shop gate, override invalid, LEGACY tier without profiles.
3. Slice D blocked until price SoT accepted; slices A–C not blocked.
