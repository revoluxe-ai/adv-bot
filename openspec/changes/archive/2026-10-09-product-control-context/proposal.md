## Why

WB Sky needs a **product-oriented control foundation** (`shop_id`, `nmid`) decoupled
from campaign execution, with fail-closed ambiguity rules and explicit price/economics
separation.

## What Changes (delivered — foundation only)

- ADDED: `app/modules/product_control/` Slice A — domain, ports, pure resolvers.
- ADDED: Slice B — read-only `CampaignProductBindingProjector`.
- ADDED: three architecture decisions (promoted on archive).
- ADDED: main spec `openspec/specs/product-control-context/spec.md` (foundation normative).

## Out of scope (this change — delivered boundary)

- PG persistence (`ShopControlSettings` / `ProductControlSettings`), Alembic, repos.
- Runtime shop-runner adapter, pricing API adapter, ChangeSet/Apply, UI/Excel/MCP.
- **`PRICE_SEMANTICS_ACCEPTED = NO`** — concrete WB price field not resolved.

Future work: `openspec/evolution/product-control-context-future-boundaries.md`.

## Capabilities

### New Capabilities

- `product-control-context`: foundation domain + binding projector (Slices A–B).

## Impact

- **Runtime campaign economics**: unchanged (no Slice D).
- **Data**: no new tables in this archive.
- **Risk**: multi-nmid and missing price remain domain blockers until future runtime.
