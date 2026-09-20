# Architecture Decision Registry

This directory is the permanent registry for architecture decisions that must
outlive a single OpenSpec change. It is the source of truth for ownership,
layering, write-path placement, and domain invariants that future changes must
respect.

Design files may explain how one change applies a decision, but reusable
architecture decisions belong here.

## Existing Decisions

- [mode-defaults-policy-ownership](mode-defaults-policy-ownership/decision.md)
  - Status: Accepted
  - Scope: ownership and placement of mode-specific defaults for paid, free,
    and common policy overlays.
- [clickhouse-sql-database-qualification](clickhouse-sql-database-qualification/decision.md)
  - Status: Accepted
  - Scope: domain invariant — working-contour ClickHouse SQL MUST qualify
    database as `default_db.<object>` in query text; SQL-contract proof
    required (not session DB alone / not SQL_REWRITE_MOCKED_AWAY).
- [scripts-wb-api-ops-stack](scripts-wb-api-ops-stack/decision.md)
  - Status: Accepted
  - Scope: ownership/layering for scripts/`/opsx-scripts` Job → existing
    `app/core/mp/wb/api` stack; `READ_ONLY_NO_MUTATION`; no raw HTTP;
    secret-strip Owner-local archive.
- [orders-or-sales-reports-read-identity](orders-or-sales-reports-read-identity/decision.md)
  - Status: Accepted
  - Scope: domain invariant — `ORDERS_OR_SALES_REPORTS_READ` means only
    statistics-api GET supplier orders/sales via generated Reports client +
    narrow `wb/api` adapter; anti-substitution vs funnel/fullstats/FBS;
    honest dateFrom/cursor period attestation.
- [wb-api-master-local-swagger-map](wb-api-master-local-swagger-map/decision.md)
  - Status: Accepted
  - Scope: ownership/layering for offline API Master map builder in `tools/`;
    entries only from local vN swagger; no invent URL, download, or codegen;
    map does not authorize WB calls.
- [strict-single-nmid-audit-evidence](strict-single-nmid-audit-evidence/decision.md)
  - Status: Accepted
  - Scope: strict single-NMID read-only audit evidence ownership; authoritative
    attribution/spend boundaries; `PARTIAL` vs `BLOCKED` output semantics;
    honest GAP provenance without inference or double physical spend.

## Change Requirements

- Every change that touches ownership, layering, write paths, or domain
  invariants must resolve decisions **context-first** (exact/
  `artifactPaths` / index), then bounded fallback under
  `openspec/decisions/` — not a full recursive dump of every decision file.
- Relevant decisions must be cited by path from proposal/design artifacts and
  implementation/verification summaries.
- If a relevant decision is missing after context-first + bounded fallback,
  create a proposed decision artifact before declaring the change
  implementation-ready (or record `Architecture Decision Missing` /
  `EVIDENCE_GAP`).
- Passing tests are not enough when implementation placement conflicts with an
  accepted architecture decision.
