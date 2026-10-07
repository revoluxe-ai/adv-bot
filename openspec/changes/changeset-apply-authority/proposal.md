## Why

`ChangeSetV1` dry-run / validation is merged on `origin/stage`
(`campaign-settings-changeset-contract` archived; canonical types in
`app/modules/wb_sky_control_plane/`). Dry-run proves deterministic preview only;
it does **not** authorize production writes. WB Sky remains the sole
production-write authority. Transports (Telegram, future REST/MCP) and AI
clients may propose `ChangeSetV1` but must not call WB or PostgreSQL settings
writers directly.

Today, campaign settings mutations still flow through legacy paths
(`apply_adv_excel_rows`, Telegram handlers, shop-runner WB adapters) without a
unified Apply contract, durable execution evidence, or transport-independent
idempotency. This change defines **Apply Authority** as a separate feature from
dry-run.

## What Changes

- Transport-independent **`ApplyRequestV1`**, **`DryRunReceiptV1`**, **`ApplyEvidenceV1`**
  (immutable receipt), and internal **`ApplyPlanV1`** / writer orchestration contract.
- **WB Sky Apply Authority** service boundary: re-validate, bind to dry-run,
  authorize actor, enforce idempotency and `st1` concurrency, execute only via
  registered writer adapters, post-apply verification, append-only audit.
- **V1 scope:** one shop; bounded policy operations already in `ChangeSetV1`
  (`campaign.set_budget_policy`, `campaign.set_sales_policy`,
  `campaign.set_bid_control_policy`); **PostgreSQL settings authority only**
  (single transaction); **no WB HTTP writes** in V1.
- Proposed ADR **`changeset-apply-authority-ownership`** (placement, forbidden
  bypass paths).
- Scenario coverage plan **S01–S20** mapped to implementation slices (planning
  evidence only).

## Capabilities

### New Capabilities

- `changeset-apply-authority`: sole production apply gate for in-scope ChangeSet
  mutations; execution evidence; idempotency; verification.

### Modified Capabilities

- None. Does not modify `campaign-settings-changeset-contract` main spec or
  `validate_changeset` semantics.

## Impact

- Future modules under `app/modules/wb_sky_control_plane/apply/` (implementation
  slices — **not authorized in this planning change**).
- Future PG ledger tables (design only; **no migrations** in planning).
- **Out of scope:** REST/MCP handlers, WB writer adapters (Slice D), legacy path
  removal, Excel/Telegram rewiring.

## Dependencies

- Merged foundation: `openspec/specs/campaign-settings-changeset-contract/spec.md`
- `openspec/decisions/campaign-settings-contract-ownership/decision.md` (PG current
  settings authority)
- Archived decision evidence:
  `openspec/changes/archive/2026-10-07-campaign-settings-changeset-contract/decisions/campaign-settings-changeset-ownership/decision.md`
  (**not yet** in `openspec/decisions/index.md` — see design evidence gaps)

## Evidence Gaps (planning)

| Gap | Status |
|-----|--------|
| `preview_digest` (`pd1`) helper in repo | **Missing** — normative in this change only |
| Apply / receipt persistence tables | **Missing** — by design until Slice B |
| Promoted `campaign-settings-changeset-ownership` ADR in registry | **Missing** — use archive + main spec until promotion |
| Decision Experiment Memory product module | **Not found** in repo — boundary documented conceptually |
| Canonical domain `PrincipalRef` type | **Missing** — reuse `LogicalScopeV1` + new `PrincipalRefV1` in apply contract |
