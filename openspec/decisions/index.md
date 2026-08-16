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
    pause/start + distinct reason + recheck + notify; TARGET_ENTITY_OR_LEG=SEARCH
    (`pause_auction_campaign`; forbid `pause_auto_campaign` for this reason);
    settled-empty / two-tick / shop-linked notify; orthogonal to Hold freeze
    and mode-defaults; stats window ≤7d.
- [auto-bid-module-coexistence-write-path](auto-bid-module-coexistence-write-path/decision.md)
  - Status: Accepted
  - Scope: mutual exclusion of automated Auto bid writers («для Авто» vs
    «в полках»); reason split vs `cost_rule_failed`; orthogonal to empty-keywords,
    mode-defaults, and Hold freeze.
- [auto-shelf-exhausted-pause-write-path](auto-shelf-exhausted-pause-write-path/decision.md)
  - Status: Accepted
  - Scope: ownership of shelf-exhausted Auto terminal pause/retest
    (detect/PG SoT → activity-control `pause_auto_campaign` + Redis Auto-lane
    mirror → clear-our-block / conditional start / notify); TARGET_ENTITY_OR_LEG=AUTO;
    forbid `pause_auction_campaign` for this reason; mid-cycle cost gate while
    shelves ON; orthogonal to empty-keywords, coexistence, and Hold freeze.
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
- [billing-fair-leg-metering-write-path](billing-fair-leg-metering-write-path/decision.md)
  - Status: Accepted
  - Scope: ownership of fair leg-pause billing metering (anchor by
    `search_adv_id`, Auto/Search 0.5 slots, UTC-day latch, AdvPayment split);
    TARGET_ENTITY_OR_LEG = auto-setting anchor + slot roles; ALLOWED billing
    adapters; forbid shop-runner/pause managers writing latch/AdvPayment;
    orthogonal to empty-keywords and shelf-exhausted pause write-paths.

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
