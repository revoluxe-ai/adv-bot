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

- PG tables `adcontrolshopfeaturerow` / `adcontrolcampaignfeaturerow` with identity
  `(shop_id, feature_id, schema_version)` and `(shop_id, advert_id, feature_id, schema_version)`.
- `payload_codec` + `AdControlSettingsRepository` (validate via `FEATURE_REGISTRY`).
- `AdControlChangeSetV1` ops `shop.set_ad_control_feature` /
  `campaign.set_ad_control_feature` + `validate_ad_control_changeset` (read-only).

## Non-merge

Isolated from `wb-sky-mcp-read-interface`, `decision-experiment-memory`,
`campaign-settings-history`, shop-wide campaign collection.
