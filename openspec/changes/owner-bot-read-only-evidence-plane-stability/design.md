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

### Runtime follow-up (published Job `ops-script-strict-nmid-186069402-20260921t0055`)

Operational Job `ops-script-strict-nmid-186069402-20260921t0055` (`prod-adv-bot`,
resolver `REUSE`, image `adv-bot:3a5a0e77f3b0f75598dab5a91c0a91eff29913c9`,
digest `sha256:803ec314ef8f1572f0d8ce8bef1760b1a52eb5edcdbed7728c15075004b93de9`)
exited **0** with artifact SHA256 `ba0f46e9e0cb4adfd3e8d0a3c493797d25e8df25dde5769c0f62e0b386bcd1bf`.
Contract / handoff / `write_budget.writes=0` / identity NMID `186069402` confirmed.
Prior defects removed in logs: `Event loop is closed`, PG cross-loop
`RuntimeError`, `RowMapping` `TypeError`, orphan `get_fullstats`.

**Remaining acceptance gap:** `decision.status=PARTIAL` with untyped
`{section}: AttributeError` for `current_contour`, `orders`, `attribution`,
`topology` (not legitimate `EvidenceReaderFailure` GAPs). Additional shape
signal: top-level `evidence[]` contains confirmed physical spend `562.01` from
`owner-bot-promotion-fullstats` while canonical `physical_spend` object stays
`missing` with gap `physical spend evidence is missing`.

| Section | Code path (HEAD) | Operation raising `AttributeError` | Expected shape | t0055 / local repro | Class |
|---------|------------------|-------------------------------------|----------------|---------------------|-------|
| `current_contour` | `OwnerBotStrictSingleNmidReadOnlyPlane.read_current_contour` → `_read_int` / `row.get` on `bundle.pg_rows` (`strict_single_nmid_audit_owner_bot_plane.py` ~L172–L242) | `row.get(...)` when row is not `dict` | `list[dict[str, Any]]` plain column keys | Local repro: PG ORM/row objects without `.get` → `current_contour: AttributeError` | **Normalization** (loader must emit dict rows; reader must not assume SQLAlchemy row objects) |
| `orders` | `read_orders` → `_read_int` / `_row_day` on `bundle.orders` (~L244–L274) | `row.get(...)` on non-dict order row | `list[dict]` supplier order payloads (`nmId`, `date`, `quantity`, …) | Local repro: non-dict order objects → `orders: AttributeError` | **Normalization** (orders must stay dict-shaped after `collect_orders_sales` + bundle load) |
| `attribution` | `read_attribution` → `item.get("days")` on `bundle.fullstats` (~L276–L315) | `item.get(...)` when fullstats entry is not `dict` (e.g. `FullStatsItem` attrs object) | `list[dict]` campaign-day trees with dict `days` / `apps` / `nms` | Local repro: `FullStatsItem`-like object in `bundle.fullstats` → `attribution: AttributeError` | **Normalization** (deep `jsonable` / `to_dict` at load boundary) |
| `topology` | `read_topology` → `bundle.memberships` + `evidence(...)` (~L361–L391) | `bundle.memberships` access or `evidence()` construction when bundle/membership shape invalid | `dict[int, set[int]]` membership map | t0055 gap present; local dict-shaped bundle does not reproduce — treat as **same bundle contract** failure until apply reproduces t0055 membership payload | **Reader adapter / bundle contract** (investigate with t0055-shaped fixture) |
| `physical_spend` (canonical) | `StrictSingleNmidAudit.run` → `spend_records` filter + `reconcile_physical_spend` (`strict_single_nmid_audit.py` ~L777–L788) vs section reader `read_physical_spend` | Reconcile sees **empty** `spend_records` while `evidence[]` already projects confirmed spend `562.01` | `SpendEvidence` in `raw_items` → canonical `physical_spend.status=confirmed` | t0055 artifact: `evidence[].value=562.01`, `physical_spend.status=missing`, `physical_spend.evidence=[]` | **Orchestration / result-shape** (projection vs reconciliation split — not new spend semantics) |

Orchestrator still maps unknown `Exception` to bare `{section}: AttributeError`
(`strict_single_nmid_audit.py` ~L773–L775), which **masks implementation
defects** as legitimate section GAPs. Apply MUST fix shapes first; optional
typed implementation-failure provenance is allowed only where it does not
replace normalization.

### Runtime follow-up (published Job `3474164f687cb506e3760b30946673504c4c8d44`)

Operational Job `ops-script-strict-nmid-186069402-20260921t0050` (`prod-adv-bot`,
resolver `REUSE`, collector `scripts/strict_single_nmid_audit.py`) exited 1
without artifact. Prior defects (`Event loop is closed`, PG cross-loop
`RuntimeError`, reader `AttributeError`) were **absent**.

Exact remaining defect: `EvidenceReaderFailure` `source=owner-bot-pg-advsetting`
`phase=pg_load` caused by
`TypeError: PG row is not mapping-like: <class 'sqlalchemy.engine.row.RowMapping'>`
in shared `_pg_row_as_dict` (`scripts/wb_api_readonly_ops/collect/owner_bot_evidence.py`).
Dict-only / incomplete mapping assumptions fail on the actual Job execute/result
type. This is an **implementation compatibility defect**, not a legitimate GAP
and not a reason to revert Job-local PG ownership or rewrite to asyncpg.

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
- Job-safe reusable PG read strategy; Job-local SQLAlchemy ownership retained
  with Mapping-protocol row normalization (`RowMapping` / `Row._mapping`).
- Typed reader failure contract for collector GAP provenance; implementation
  TypeError on supported mapping rows is not a legitimate GAP.
- A1 strict collect behavior preserved (regression tests).
- Strict single-NMID uses shared plane; zero production writes.

**Non-Goals:**

- ProKraft-specific readers; copying A1 collector ZIP body.
- New collector Registry entry; resolver semantic changes.
- Stock source invention; full attribution endpoint catalog.
- Mass refactor of unrelated scripts.
- Asyncpg rewrite; reverting Job-local PG ownership; recasting RowMapping
  TypeError as legitimate evidence GAP.

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

Shared Job-safe PG reads remain **lifecycle-bound** (Job-local engine/session,
one Job-scoped loop, deterministic dispose). Do not introduce ProKraft-specific
SQL. Do **not** reopen an asyncpg rewrite as owed work for this change.

**PG row normalization (runtime 2026-09-21):** shared `_pg_row_as_dict` MUST
accept mapping protocol data used by the Job SQLAlchemy path:

- `collections.abc.Mapping` (including `sqlalchemy.engine.row.RowMapping`) →
  deterministic plain `dict`;
- SQLAlchemy `Row` at another seam → documented `row._mapping`, not positional
  or private guessing;
- unsupported arbitrary objects → explicit `TypeError` (fail closed);
- this TypeError MUST NOT be converted into a legitimate evidence GAP.

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
- [Risk] Dict-only PG row helper rejects SQLAlchemy `RowMapping` on Job path →
  [Mitigation] Mapping-protocol normalizer + regression using real `RowMapping`
  (or execute/result seam); negative test for non-mapping objects.

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
- [x] implementation matches decision
