# Tasks: product-control-context (foundation archive)

FOUNDATION_SCOPE: SLICES_A_B_ONLY
OWNER_SCOPE_DECISION: OPTION_A_FOUNDATION_ONLY
STAGE_BASELINE: `cb9489c17d2746aa3735cfdbe58d82d89d32cdd1`

## Slice A — Domain vocabulary + ports

- [x] 1.1–1.7 Domain foundation (`app/modules/product_control/domain/`, tests)

## Slice B — Binding projector (read-only)

- [x] 2.1–2.4 `CampaignProductBindingProjector` + tests + slice-b receipt

## Future changes (not in this archive)

- [x] 3.0 Record `product-control-settings-persistence` boundary — **not implemented**
- [x] 4.0 Record `product-control-shop-drr-runtime` boundary — **not implemented**
- [x] 5.0 Record SKU override / surfaces boundaries — **not implemented**

## Archive close

- [x] A.1 Reconcile proposal/contract/design/spec to foundation truth
- [x] A.2 `scenario-coverage/certify.receipt.json` (S01–S22)
- [x] A.3 Promote ADRs to `openspec/decisions/`
- [x] A.4 `openspec archive product-control-context` + post-archive verify

## Planning / governance

- [x] P.1–P.3 Planning complete
- [x] P.4 Promote decisions on archive
