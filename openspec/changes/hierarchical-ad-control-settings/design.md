# Design — hierarchical-ad-control-settings (Slice A + B)

## Architecture Decision References

- `openspec/decisions/product-control-aggregate-ownership/decision.md`
- `openspec/decisions/product-pricing-and-cpo-ownership/decision.md`
- `openspec/decisions/campaign-settings-contract-ownership/decision.md`
- `openspec/decisions/campaign-settings-changeset-ownership/decision.md`
- `openspec/decisions/changeset-apply-authority-ownership/decision.md`
- `openspec/specs/product-control-context/spec.md`

## Ownership & Placement

| Concern | Owner |
|---------|--------|
| Per-function automation registry + resolver | `app/modules/ad_control_settings/` |
| Product DrrProfile semantics | `app/modules/product_control/` (adapter only) |
| Campaign settings field classification | `campaign_settings_contract` |
| ChangeSet dry-run (ad control) | `wb_sky_control_plane` (`AdControlChangeSetV1`) |
| Configured persistence | `app/modules/ad_control_settings/persistence/` |

Checklist:

- [x] context-first decision lookup performed
- [x] relevant decisions cited
- [x] new placement in dedicated module (no fork of product_control)
- [x] implementation layer matches decision (domain + persistence; Apply unwired)

## Slice A deliverables

Registry, scope model, resolver, product adapter, DRR triple types, headroom state +
eligibility, diagnostics contract, reason codes, exhaustive unit tests.

## Slice B deliverables

- PG tables with logical identity shop `(shop_id, feature_id)` and campaign
  `(shop_id, advert_id, feature_id)`; `schema_version` column on the authoritative row.
- `payload_codec` + `AdControlSettingsRepository` (validate via `FEATURE_REGISTRY`).
- `AdControlChangeSetV1` ops `shop.set_ad_control_feature`,
  `campaign.set_ad_control_override` / `disable` / `clear` + dry-run validator (read-only).

## Task 4.1 runtime

Read-only shop evaluation lives in `app/modules/ad_control_settings/runtime/`.
Shop-runner calls it from `hierarchical_ad_control_diagnostics` and does not
apply changes. One `ReportsManager.get_supplier_orders` pagination per shop
and closed window. Shop spend is `full_adv_wb_stat` over
`shop_campaign_inventory`. Campaign economics use `AttributionFactsReader`
DIRECT facts only. Campaign ids prefer settings history, then inventory.

Decisions:

- `openspec/decisions/drr-cpo-price-semantics/decision.md` (`V1_ORDER_VALUE_BASIS`)
- `openspec/changes/hierarchical-ad-control-settings/decisions/shop-order-gmv-runtime-authority/decision.md`
- `openspec/changes/hierarchical-ad-control-settings/decisions/hierarchical-ad-control-settings-ownership/decision.md`

`HEADROOM_ALLOCATOR_NOT_ACCEPTED` stays. Catalog-price CPO stays blocked when
the builder is not on the order-value path. No migration and no 4.2 UI edits.

## Non-merge

Isolated from `wb-sky-mcp-read-interface`, `decision-experiment-memory`,
`campaign-settings-history`, shop-wide campaign collection.
