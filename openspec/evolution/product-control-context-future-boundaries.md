# Product control — future boundaries (non-normative)

Archived change `product-control-context` delivered **foundation only** (Slices A–B):
domain vocabulary, pure resolvers, read-only binding projector in
`app/modules/product_control/`.

## product-control-settings-persistence (concept)

- `ShopControlSettings` / `ProductControlSettings` PG models, Alembic, repositories.
- Absent-row logical defaults (`NOT_ENROLLED`, `INHERIT_SHOP`); no write-on-read.
- Dormant profile semantics (Owner): profiles may persist while enrollment/mode
  makes them ineffective; no silent runtime effect.
- Atomic DRR profile DB invariant (both NULL or both non-NULL with `max >= target`).
- Separate OpenSpec change + DDL GO. Alembic head at archive time: `f9c0a1b2d3e4`.
- Scenarios **S18** (integration defaults), persistence portions of **S21**.

## product-control-shop-drr-runtime (concept)

- Requires **`PRICE_SEMANTICS_ACCEPTED = YES`** before start.
- Concrete `ProductPricingReader` adapter, freshness, multi-size, SPP/Wallet policy.
- Shop `ENROLLED` path → `ProductCpoResolver` → `LegacyCampaignCpoAdapter` → campaign.
- Scenarios **S04**, **S06**, **S11**, **S12**, **S13**, **S14**, **S15**, runtime
  portions of **S19**–**S22**.

## product-control-sku-override-runtime (concept)

- Product `OVERRIDE_ENABLED` runtime atop persisted settings.
- Scenario **S08**.

## product-control-surfaces (concept)

- ChangeSet ops (`SET_SHOP_DRR_PROFILE`, `SET_PRODUCT_DRR_PROFILE`), Apply integration,
  `ProductControlContextV1` assembler, UI/Excel, REST/MCP.
- Must use WB Sky Apply Authority for mutations; not direct repository writes.
