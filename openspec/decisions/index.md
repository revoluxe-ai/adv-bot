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
- [neo4j-not-in-runtime-config-di](neo4j-not-in-runtime-config-di/decision.md)
  - Status: Accepted
  - Scope: Neo4j MUST NOT be a mandatory part of runtime app config /
    application DI; reintroduction requires an explicit change with real
    driver/DI wiring (test `NEO4J_*` stubs are not the architecture).
- [callback-start-entry-write-path](callback-start-entry-write-path/decision.md)
  - Status: Accepted
  - Scope: write-path — User creation belongs to message `/start` / write
    middleware (`sm(read_only=False)`); Callback Start is menu-return
    PURE_READ only and MUST NOT call `create_user`.
- [alembic-forward-only-head-convergence](alembic-forward-only-head-convergence/decision.md)
  - Status: Accepted
  - Scope: migration topology — parallel Alembic heads MUST converge via
    a forward-only merge revision without schema/data operations; published
    history is immutable.

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
