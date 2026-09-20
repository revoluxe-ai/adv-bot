## Context

Collectors on branch `scripts` share Owner-bot access (`get_access_for_wb_cabinet`,
`DIManager`, `WBManagerHubFactory`) and `scripts/wb_api_readonly_ops`, but
**orchestration** historically diverged between A1 strict collect and strict
single-NMID audit plane. Architecture review requires one reusable read layer
without ProKraft-specific forks.

### Current-state recheck (HEAD `fe0a28b097081012ef9e991475103fddea0239a5`)

| Finding (discovery baseline) | At current HEAD | Planning implication |
|----------------------------|-----------------|-------------------|
| Orphan `adapter.get_fullstats(...)` | **Fixed** — `strict_single_nmid_audit_owner_bot_plane.py` uses `FullstatsAdapter._request_chunk` via chunked fetcher (~L227–235) | No apply task to add API; **keep regression test** that forbids `get_fullstats` string on plane |
| Repeated `asyncio.run()` per sync reader | **Partially fixed** — plane owns one loop, `_run_coroutine`, `ensure_bundle`, `close()` with engine dispose (~L265–297, L356) | Verify under tests/Job harness; **harden** shared contract + PG path alignment |
| PG via module-level SQLAlchemy `get_async_session_maker` in strict plane | **Still present** — `_load_pg_rows` (~L136+) vs A1 `ch_a1_evidence.run_pg_query` | **In scope:** Job-safe reusable PG strategy shared with A1-stable path |
| Fullstats payload shape for attribution/spend | **Uncertain** — `_request_chunk` → `FullStatsItem.to_dict()` may not match dict shape A1/jsonable pipeline expects | **In scope:** normalize via shared mapper/jsonable seam; tests for attribution/spend readers |
| Untyped `Exception` → section GAP | **Still present** — `StrictSingleNmidAudit.run` (~L764–766) | **In scope:** typed reader failure provenance |
| Stock / full attribution catalog | strict `read_stock` empty; no shared stock source confirmed | **Out of scope** (follow-up) |

Reference paths rechecked:

- `scripts/a1_strict_read_only_contract_collect.py` — single `asyncio.run(_collect_wb)`; PG via `run_pg_query`; fullstats `_request_chunk`
- `scripts/ch_a1_evidence.py` — asyncpg PG reads
- `scripts/wb_api_readonly_ops/collect/orders_sales.py` — shared orders/sales pagination
- `scripts/wb_api_readonly_ops/collect/runner.py` — reference orchestration pattern
- `scripts/strict_single_nmid_audit_owner_bot_plane.py` — Job loop + bundle preload
- `app/core/mp/wb/api/adapter/promotion_client/fullstats/adapter.py` — supported API surface
- `app/utils/db/session_maker.py` — module-level async engines (lifecycle-sensitive)

## Goals / Non-Goals

**Goals:**

- One Job-scoped async lifecycle for shared evidence loading.
- Reuse `wb_api_readonly_ops` + official WB adapters; no parallel HTTP.
- Job-safe reusable PG read strategy aligned with A1-stable path.
- Typed reader failure contract for collector GAP provenance.
- A1 strict collect behavior preserved (regression tests).
- Strict single-NMID uses shared plane; zero production writes.

**Non-Goals:**

- ProKraft-specific readers; copying A1 collector ZIP body.
- New collector Registry entry; resolver semantic changes.
- Stock source invention; full attribution endpoint catalog.
- Mass refactor of unrelated scripts.

## Architecture Decision References

- `openspec/decisions/scripts-wb-api-ops-stack/decision.md` — Accepted scripts/Job
  → existing WB API stack, `READ_ONLY_NO_MUTATION`.
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` —
  Accepted ORDERS_OR_SALES_REPORTS_READ identity (orders path unchanged).
- `openspec/decisions/strict-single-nmid-audit-evidence/decision.md` —
  Accepted audit output semantics (`PARTIAL` vs `BLOCKED`); this change does not
  alter those requirements.
- `openspec/changes/owner-bot-read-only-evidence-plane-stability/decisions/owner-bot-job-evidence-plane-lifecycle/decision.md`
  — **Proposed** reusable Job evidence plane lifecycle invariant.

Context-first lookup performed; lifecycle invariant was missing from accepted
registry → proposed decision artifact added.

## Ownership & Placement

| Layer | Owner |
|-------|--------|
| Shared Job evidence loader / async runtime | New or extended module under `scripts/wb_api_readonly_ops/` (or thin `scripts/owner_bot_read_evidence/` if extract cleaner) — **not** `app/` product paths |
| Collector-specific NMID audit orchestration | `scripts/strict_single_nmid_audit.py` + plane adapter (consumer only) |
| A1 strict collect | Consumer + regression anchor; minimal diff preferred |
| WB adapters / DI | Existing `app/core/mp/wb/api` (no new transport) |
| PG Job-safe reads | Shared facade wrapping A1-proven asyncpg pattern or loop-bound factory |

Forbidden: Registry edits, new collector id, local Cursor→prod API, raw HTTP.

## Decisions

### 1. Single Job-scoped async entry

All async PG+WB loads for one plane instance run on one loop created at plane
construction; preload via `ensure_bundle` before sync section readers; `close()`
disposes engines and closes loop deterministically.

### 2. Shared primitives, not duplicated fetch logic

Orders/sales MUST remain on `collect_orders_sales`. Fullstats MUST use supported
adapter methods only. Prefer extracting a shared loader function callable from
A1 and strict plane over copying A1's ZIP/campaign-specific logic.

### 3. PG alignment

Replace ad-hoc SQLAlchemy session reads in strict plane with shared Job-safe PG
read API (reuse `ch_a1_evidence.run_pg_query` semantics or extract shared
helper). Do not introduce ProKraft-specific SQL.

### 4. Typed reader failures

Plane/loaders raise or return structured failure records; strict orchestrator
maps them to GAP provenance without leaking bare `RuntimeError` as the only
signal when lifecycle/adapter class is known.

### 5. Verification without new operational RUN in planning

Proof via unit/integration tests + optional existing Job harness patterns; no
requirement to re-run ProKraft Job during apply planning.

## Risks / Trade-offs

- [Risk] Shared extract breaks A1 edge cases → [Mitigation] A1 targeted regression suite first-class gate.
- [Risk] Engine dispose timing → [Mitigation] explicit tests simulating Job open/close.
- [Risk] Fullstats shape mismatch persists → [Mitigation] shared jsonable/mapper tests with real adapter types.

## Open Questions disposition

| Question | Disposition |
|----------|-------------|
| Shared PG module location | Resolve during apply (`wb_api_readonly_ops` vs small sibling package) |
| Stock shared source | **Deferred** — not in this change |
| Full attribution endpoint catalog | **Deferred** — not in this change |

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed for lifecycle gap
- [ ] implementation matches decision (pending apply)
