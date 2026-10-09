## Why

`ChangeSetV1` dry-run / validation is merged on `origin/stage`
(`campaign-settings-changeset-contract` archived; canonical types in
`app/modules/wb_sky_control_plane/`). Dry-run proves deterministic preview only;
it does **not** authorize production writes. WB Sky remains the sole
production-write authority. Transports (Telegram, future REST/MCP) and AI
clients may propose `ChangeSetV1` but must not call WB or PostgreSQL settings
writers directly.

Campaign settings mutations still flow through legacy paths
(`apply_adv_excel_rows`, Telegram handlers, shop-runner WB adapters) without a
unified Apply contract, durable execution evidence, or transport-independent
idempotency. This change delivers **Apply Authority** as a separate feature from
dry-run.

## What Changes (implemented V1 — Slices A–C)

- Transport-independent **`ApplyRequestV1`**, **`DryRunReceiptV1`**, **`ApplyEvidenceV1`**
  (immutable receipt), and internal **`ApplyPlanV1`** / writer orchestration contract.
- **WB Sky Apply Authority** (`ApplyAuthorityService`): re-validate, bind to dry-run,
  authorize actor, enforce idempotency and `st1` concurrency, execute via
  **`pg.campaign_settings_policy_v1`**, post-apply PG reread verification, durable ledger.
- **V1 scope (delivered):** one shop; three bounded policy operations
  (`campaign.set_budget_policy`, `campaign.set_sales_policy`,
  `campaign.set_bid_control_policy`); **PostgreSQL settings authority only**
  (single transaction); **no WB HTTP writes**.
- Accepted ADR **`changeset-apply-authority-ownership`** (promoted on archive).
- Scenario certification **S01–S35** with D/E/F scenarios moved to future changes
  (see `FUTURE_BOUNDARIES.md`).

## Capabilities

### New Capabilities

- `changeset-apply-authority`: production apply gate for in-scope PG policy
  `ChangeSetV1` mutations; execution evidence; idempotency; verification.

### Modified Capabilities

- None. Does not modify `campaign-settings-changeset-contract` main spec or
  `validate_changeset` semantics.

## Impact

- `app/modules/wb_sky_control_plane/apply/` (models, persistence, service, PG writer).
- Alembic `f9c0a1b2d3e4` apply ledger tables.

## Out of scope (separate future OpenSpec changes)

- External WB writer adapters (`external-wb-apply-authority` concept).
- REST/MCP/Telegram Apply transport (`apply-transport-adapters` concept).
- Optional history / decision-memory cross-links.
- Legacy path removal, Excel/Telegram rewiring, production deploy.

See `FUTURE_BOUNDARIES.md`.

## Dependencies

- Merged foundation: `openspec/specs/campaign-settings-changeset-contract/spec.md`
- `openspec/decisions/campaign-settings-contract-ownership/decision.md`
- `openspec/decisions/campaign-settings-changeset-ownership/decision.md`

## Evidence (close)

| Item | Status |
|-----|--------|
| `preview_digest` (`pd1`) | **Implemented** (Slice A) |
| Apply persistence tables | **Implemented** (Slice B migration) |
| `changeset-apply-authority-ownership` ADR | **Promoted** on archive |
| Production migration / transport | **Not in this change** |
