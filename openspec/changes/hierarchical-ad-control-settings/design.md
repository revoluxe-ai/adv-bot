# Design — hierarchical-ad-control-settings (Slice A)

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
| ChangeSet dry-run / Apply | `wb_sky_control_plane` (future ops) |

Checklist:

- [x] context-first decision lookup performed
- [x] relevant decisions cited
- [x] new placement in dedicated module (no fork of product_control)
- [x] implementation layer matches decision (pure domain only)

## Slice A deliverables

Registry, scope model, resolver, product adapter, DRR triple types, headroom state +
eligibility, diagnostics contract, reason codes, exhaustive unit tests.

## Non-merge

Isolated from `wb-sky-mcp-read-interface`, `decision-experiment-memory`,
`campaign-settings-history`, shop-wide campaign collection.
