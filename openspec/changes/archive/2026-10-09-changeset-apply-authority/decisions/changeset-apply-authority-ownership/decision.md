# Decision: Ownership of ChangeSet Apply Authority

## Status

Accepted (canonical copy: `openspec/decisions/changeset-apply-authority-ownership/decision.md`)

## Context

Accepted `openspec/decisions/campaign-settings-contract-ownership/decision.md`:
PostgreSQL is authority of **current** campaign settings; registry classifies fields.

Merged main spec `openspec/specs/campaign-settings-changeset-contract/spec.md` and
`app/modules/wb_sky_control_plane/` own **dry-run only** (`validate_changeset`,
`dry_run` — no production writes).

Legacy settings mutation paths remain outside Apply: e.g.
`apply_adv_excel_rows` (`app/client_bot/user_interface/services/adv_excel_roundtrip/import_apply.py`),
Telegram `AdvSetting` handlers, shop-runner WB writers.

## Decision

**WB Sky Apply Authority** is the sole production-write gate for **in-scope
`ChangeSetV1` apply protocol** operations. It is **not** global exclusivity for all
campaign settings mutations until legacy Excel/Telegram/shop-runner paths migrate.

| Layer | Owner |
|-------|--------|
| `ChangeSetV1`, dry-run, `sd1` / `st1` | `app/modules/wb_sky_control_plane/` (existing) |
| **Apply request/plan/evidence, idempotency ledger, orchestration** | `app/modules/wb_sky_control_plane/apply/` (new — implementation slices) |
| Field registry / `normalize_value` | `app/modules/campaign_settings_contract/` (reuse) |
| Settings **history** (CH) | `app/modules/campaign_settings_history/` (read/collector; not apply receipt) |
| WB HTTP side effects (bids, budget deposit, pause, …) | Existing shop-runner / activity-control write-path ADRs — **not** V1 Apply |

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED (V1 PG policy fields only)
BUSINESS_TERM: authorized application of bounded campaign settings ChangeSet
TARGET_ENTITY_OR_LEG: CampaignResourceRef / cmp_* ; AdvSetting row lock under resolver
ALLOWED_ADAPTERS (V1): pg.campaign_settings_policy_v1 writer invoked only from Apply Authority orchestrator
FORBIDDEN_ADAPTERS: MCP/REST/Telegram/LLM → WB writers or PG settings UPDATE bypassing Apply Authority; dry_run → write; apply_adv_excel_rows on Apply path (until migrated)
```

Apply Authority MUST:

1. Re-run validation pipeline (or equivalent) at execution time.
2. Persist durable idempotency and immutable `ApplyEvidenceV1`.
3. Classify writer outcomes; never map `UNKNOWN_EXTERNAL_STATE` to success.

Writer adapters MUST NOT contain business policy (capabilities, tokens, authz).

## Applies to

- All future transports that apply campaign settings via `ChangeSetV1`.
- V1: three `campaign.set_*_policy` operations, one shop, PG transaction.

## Allowed

- `SELECT … FOR UPDATE` on touched `AdvSetting` rows during apply transaction.
- Optional shop advisory lock only if proven necessary (not required for V1 default).
- `ApplyAuthorityService.apply(request, context)` with server-built `ApplyInvocationContext`.
- Post-apply re-read via existing `resolve_changeset_snapshots` / local policy projection.
- Audit append-only events referencing `ApplyEvidenceV1.apply_id`.

## Forbidden

- Treating `DryRunResultV1.status == OK` as write permission.
- Client-trusted `preview_digest` without server recompute + equality check.
- `PARTIALLY_APPLIED` as success for V1 PG atomic slice.
- Automatic retry of external WB calls on ambiguous timeout (Slice D+).
- Decision Experiment Memory owning apply receipt SoT.

## Related specs

- `openspec/changes/changeset-apply-authority/specs/changeset-apply-authority/spec.md`
- `openspec/specs/campaign-settings-changeset-contract/spec.md`
