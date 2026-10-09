# Future boundaries — changeset-apply-authority (non-normative)

Owner scope **Option A** closed apply authority at **PG-only V1 (Slices A–C)**.
The following are **separate future OpenSpec changes** — not delivered by the
archived `changeset-apply-authority` implementation.

## external-wb-apply-authority (concept)

- Inventory **existing** WB mutation adapters before defining mutation surface.
- External writer lifecycle: definitive rejection vs `UNKNOWN_EXTERNAL_STATE`.
- No blind retry; reconciliation before retry; WB post-write reread where applicable.
- Scenarios **S10**, **S11** (out of V1 main spec).

## apply-transport-adapters (concept)

- REST / MCP / Telegram Apply: thin adapters → `ApplyAuthorityService.apply` only.
- Scenarios **S15**, **S16** (out of V1 main spec).

## Optional apply cross-links (concept)

- History and decision memory may reference `apply_id`; they do not own execution truth.
- Scenarios **S18**, **S19** — boundaries only in V1.
