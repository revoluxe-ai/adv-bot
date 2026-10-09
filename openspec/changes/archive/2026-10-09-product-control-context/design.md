## Context

Campaign-centric runtime vs product-oriented control. Foundation implemented in
`app/modules/product_control/` (Slices A–B on `stage`).

**Price:** `PRICE_SEMANTICS_ACCEPTED = NO`. Ports + pure resolver only.

## Goals / Non-Goals (archive boundary)

**Goals (delivered):**

- Domain vocabulary, pure resolvers, binding projector, unit tests.

**Non-Goals (future changes):**

- PG settings, Alembic, shop-runner adapter, pricing reader impl, UI/Excel/MCP,
  category tier runtime.

## Architecture Decision References (promoted)

- `openspec/decisions/product-control-aggregate-ownership/decision.md`
- `openspec/decisions/campaign-product-binding-ownership/decision.md`
- `openspec/decisions/product-pricing-and-cpo-ownership/decision.md`

## Implementation slices (archive truth)

| Slice | Content | Status |
|-------|---------|--------|
| A | Domain types, ports, pure resolvers, unit tests | **Delivered** |
| B | Read-only binding projector | **Delivered** |
| C | PG settings + repos | Future: `product-control-settings-persistence` |
| D | Runtime shop DRR + price + adapter | Future: `product-control-shop-drr-runtime` |
| E | SKU override runtime | Future |
| F | Surfaces / ChangeSet / export | Future |

See `openspec/evolution/product-control-context-future-boundaries.md`.

## Shop rollout and product control mode

Unchanged normative semantics — implemented in `EffectiveControlResolver`.
See `owner-contract.md` enrollment matrix.

## DrrProfile / ProductCpoResolver / bindings

Implemented as documented in main spec and ADRs.

## Review checklist

- [x] foundation delivered on stage
- [x] future boundaries recorded
- [x] owner Option A scope reconciled
