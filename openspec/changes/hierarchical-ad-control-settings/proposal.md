## Why

WB Sky needs a **canonical hierarchical automation settings** model: per-function
INHERIT | OVERRIDE | DISABLED at SHOP and CAMPAIGN, live inheritance, DRR triple
semantics, headroom eligibility, and diagnostics on the same pure resolver—without
a global automation flag or legacy disguised as hierarchical control.

## What Changes (Slice A — foundation)

- ADDED: `app/modules/ad_control_settings/` pure domain (registry, resolver,
  product DrrProfile adapter, DRR/headroom state, diagnostics contract, reason codes).
- ADDED: unit tests under `tests/unit/ad_control_settings/`.
- ADDED: change spec and owner-contract encoding Owner architecture decisions.

## Out of scope (this slice)

- PG persistence / Alembic / repositories.
- Runtime production writers, WB writes, CPO production actuation (`PRICE_SEMANTICS_ACCEPTED = NO`).
- UI / Excel / API / MCP transport, deployment.
- Production headroom ranking / allocation algorithm (protocol only).

## Capabilities

### New Capabilities

- `hierarchical-ad-control-settings`: foundation domain Slice A.

## Impact

- **Runtime**: unchanged (no shop-runner wiring).
- **Data**: no new tables.
