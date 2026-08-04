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
- [empty-keywords-pause-write-path](empty-keywords-pause-write-path/decision.md)
  - Status: Accepted
  - Scope: ownership of empty-keywords detect → Redis intent → activity-control
    pause/start + distinct reason + recheck + notify; orthogonal to Hold freeze
    and mode-defaults; stats window ≤7d.
- [card-ab-hold-write-path-ownership](card-ab-hold-write-path-ownership/decision.md)
  - Status: Accepted
  - Scope: A/B Hold setup/hold write-path ownership, structural freeze ACT,
    allowed-set snapshot/enforcement, stale-stats freeze, Search common-bid
    ENTER reset-then-freeze, Excel write-path out of MVP.
- [ab-hold-epoch-lifecycle-and-generation-ownership](ab-hold-epoch-lifecycle-and-generation-ownership/decision.md)
  - Status: Accepted
  - Scope: WARM_UP durable pre-epoch stage, epoch/generation model, durable
    PENDING intent before WB sync, partial-sync recovery, same-generation retry.
- [ab-hold-confirmed-epoch-parameters-sot](ab-hold-confirmed-epoch-parameters-sot/decision.md)
  - Status: Accepted
  - Scope: confirmed keyword set / target places / Auto participation / Auto
    bid as durable epoch SoT, separate from factual position; Auto bid freeze
    while ACTIVE.

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
