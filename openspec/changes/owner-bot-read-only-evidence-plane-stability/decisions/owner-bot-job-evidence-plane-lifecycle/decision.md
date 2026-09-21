# Decision: Owner-bot Job evidence plane lifecycle

## Status

Proposed

## Context

Accepted `openspec/decisions/scripts-wb-api-ops-stack/decision.md` задаёт
scripts/Job ownership и WB stack, но не фиксирует reusable invariant для
**Job-scoped async lifecycle** shared evidence loading (PG + WB) между
collectors. Strict single-NMID и A1 strict collect оба читают Owner-bot plane,
но historically использовали разные PG/async orchestration patterns, что
приводило к cross-loop failures и orphan adapter calls.

## Decision

Shared read-only evidence loading для Owner-bot Job collectors MUST:

1. Использовать **один Job-scoped asyncio event loop** на execution для всех
   async PG/WB operations в рамках одного plane instance.
2. **Не** вызывать `asyncio.run()` repeatedly on paths that bind module-level
   async SQLAlchemy engines across incompatible loops.
3. Вызывать WB only through existing `app/core/mp/wb/api` adapters and
   `scripts/wb_api_readonly_ops` collect helpers (`orders_sales`, pagination,
   cards where applicable).
4. Use **supported** Fullstats adapter methods (`_request_chunk` /
   `get_full_adv_stat` family) — never invent parallel method names on adapters.
5. Prefer **Job-safe reusable PG read** (A1-stable `ch_a1_evidence.run_pg_query`
   pattern or extracted shared factory with identical safety properties) over
   ad-hoc SQLAlchemy session usage in collector planes unless explicitly scoped
   and lifecycle-bound to the Job loop with proven cleanup.
6. Map reader failures to **typed provenance** (source, error class, lifecycle
   phase) consumable by collector output contracts; raw unhandled exceptions
   MUST NOT be the only signal. An implementation `TypeError` from rejecting a
   supported SQLAlchemy mapping row (`RowMapping`) MUST NOT be recast as a
   legitimate evidence GAP.
7. Preserve `READ_ONLY_NO_MUTATION` and `write_budget.writes=0`.
8. When the Job-local SQLAlchemy path is retained, shared PG row normalization
   MUST accept mapping-protocol results (`collections.abc.Mapping`, including
   `sqlalchemy.engine.row.RowMapping`) and SQLAlchemy `Row` via documented
   `row._mapping`, emitting a plain `dict` with unchanged keys/values.
   Unsupported objects fail closed with explicit `TypeError`. This does **not**
   authorize an asyncpg rewrite or a ProKraft-specific reader.

## Applies to

- Owner-bot Job read-only collectors sharing WB/PG evidence plane
- `strict_single_nmid_audit_owner_bot_plane` and A1 strict read-only collect
- Future generic read-only audits using the same plane

## Allowed

- Extract shared loader from existing stable paths (not copy A1 ZIP contract)
- Single preload (`ensure_bundle`) before sync section readers
- Explicit `close()`/dispose hooks at Job boundary
- `PARTIAL` collector outcomes when evidence gaps remain after typed failures
- Job-local SQLAlchemy engine/session ownership with Mapping-protocol row
  normalization (`RowMapping` / `Row._mapping` → plain `dict`)

## Forbidden

- ProKraft-specific parallel DB/WB readers
- New raw HTTP clients
- Registry/resolver semantic changes to mask runtime defects
- Production/shared writes

## Related specs

- `openspec/changes/owner-bot-read-only-evidence-plane-stability/specs/owner-bot-read-only-evidence-plane/spec.md`
- `openspec/specs/strict-single-nmid-read-only-audit/spec.md`

## Related changes

- `owner-bot-read-only-evidence-plane-stability`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed for missing lifecycle invariant
- [x] implementation layer matches decision
