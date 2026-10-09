# Future boundaries (non-normative for V1 archive)

Owner scope decision **Option A** closed `changeset-apply-authority` at **PG-only
V1 (Slices A–C)**. The following are **separate future OpenSpec changes** — not
delivered by this archive.

## external-wb-apply-authority (concept)

- Inventory **existing** WB mutation adapters (shop-runner, activity-control, …)
  before defining mutation surface; do not assume budget/status/bid are all in scope.
- External writer lifecycle: definitive rejection vs `UNKNOWN_EXTERNAL_STATE`.
- No blind retry; reconciliation before retry; WB post-write reread where applicable.
- External idempotency limits; evidence linkage to Apply attempt/receipt.
- Scenarios **S10**, **S11** (moved out of V1 normative spec).

## apply-transport-adapters (concept)

- REST / MCP / Telegram Apply entrypoints are **thin adapters** only.
- Parse `ApplyRequestV1`; build trusted `ApplyInvocationContext`; call
  `ApplyAuthorityService.apply`; **never** call PG/WB writers directly.
- `transport_channel` is audit metadata only.
- Scenarios **S15**, **S16** (moved out of V1 normative spec).

## Optional apply cross-links (concept)

- `campaign_settings_history` and decision experiment memory may **reference**
  `apply_id` / evidence; they do **not** own execution truth.
- No linkage implementation in V1.
- Scenarios **S18**, **S19** — architectural boundaries only (certified
  `NOT_APPLICABLE_TO_V1` for implementation).
