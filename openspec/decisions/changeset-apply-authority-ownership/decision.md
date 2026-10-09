# Decision: Ownership of ChangeSet Apply Authority

## Status

Accepted

## Context

Accepted `openspec/decisions/campaign-settings-contract-ownership/decision.md`:
PostgreSQL is authority of **current** campaign settings; registry classifies fields.

Main spec `openspec/specs/campaign-settings-changeset-contract/spec.md` and
`app/modules/wb_sky_control_plane/` own **dry-run only** (`validate_changeset`,
`dry_run` — no production writes).

Legacy settings mutation paths remain outside Apply: e.g.
`apply_adv_excel_rows`, Telegram `AdvSetting` handlers, shop-runner WB writers.

Archived change `changeset-apply-authority` delivered **PG-only V1** (Slices A–C).

## Decision

**WB Sky Apply Authority** is the sole production-write gate for **in-scope
`ChangeSetV1` apply protocol** operations on the V1 PG policy path. It is **not**
global exclusivity for all campaign settings mutations until legacy paths migrate.

| Layer | Owner |
|-------|--------|
| `ChangeSetV1`, dry-run, `sd1` / `st1` | `app/modules/wb_sky_control_plane/` (existing) |
| Apply request/plan/evidence, idempotency ledger, orchestration | `app/modules/wb_sky_control_plane/apply/` |
| Field registry / `normalize_value` | `app/modules/campaign_settings_contract/` (reuse) |
| Settings **history** (CH) | `app/modules/campaign_settings_history/` (not apply receipt) |
| WB HTTP side effects | Existing shop-runner / activity-control ADRs — **not V1 Apply** |

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED (V1 PG policy fields only)
BUSINESS_TERM: authorized application of bounded campaign settings ChangeSet (PG policy)
TARGET_ENTITY_OR_LEG: CampaignResourceRef / cmp_* ; AdvSetting row lock under resolver
ALLOWED_ADAPTERS (V1): pg.campaign_settings_policy_v1 invoked only from Apply Authority orchestrator
FORBIDDEN_ADAPTERS: direct PG settings UPDATE or WB writers bypassing Apply Authority; dry_run → write
```

**V1 implemented scope:** three `campaign.set_*_policy` operations, one shop,
one PostgreSQL transaction, post-write PG reread, immutable `ApplyEvidenceV1`.

**Not V1:** external WB mutation, REST/MCP/Telegram Apply transports, optional
history/decision-memory cross-links — separate future changes.

Apply Authority MUST:

1. Re-run validation at execution time.
2. Persist durable idempotency and immutable `ApplyEvidenceV1` (repository insert-only in V1).
3. Never treat dry-run OK as write permission.

Transport adapters MUST NOT define alternate domain semantics; they call
`ApplyAuthorityService.apply(request, context)` when implemented in a future change.

Writer adapters MUST NOT contain business policy (capabilities, tokens, authz).

## Applies to

- Future transports that apply campaign settings via `ChangeSetV1` (not yet wired).
- V1 code path: PG policy apply only.

## Allowed

- `SELECT … FOR UPDATE` on touched `AdvSetting` rows during apply transaction.
- `ApplyAuthorityService.apply(request, context)` with server-built `ApplyInvocationContext`.
- Post-apply re-read via authoritative resolver / transaction-local verification.

## Forbidden

- Client-trusted `preview_digest` without server recompute + equality check.
- `PARTIALLY_APPLIED` as success for V1 PG atomic apply.
- Decision Experiment Memory owning apply receipt SoT.
- Claiming global sole write gate while legacy bypass paths remain.

## Related specs

- `openspec/specs/changeset-apply-authority/spec.md`
- `openspec/specs/campaign-settings-changeset-contract/spec.md`

## Related changes

- `openspec/changes/archive/2026-10-09-changeset-apply-authority`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] implementation layer matches decision
