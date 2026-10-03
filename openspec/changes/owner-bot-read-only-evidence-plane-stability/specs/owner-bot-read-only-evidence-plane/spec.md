## ADDED Requirements

### Requirement: Job-scoped async evidence lifecycle

Owner-bot read-only evidence plane used by Job collectors SHALL use exactly one
compatible asyncio event loop per plane instance for all async PG and WB loads
during that Job execution. The plane SHALL preload shared evidence once before
sync section readers run and SHALL deterministically release async DB/API
resources at Job boundary.

#### Scenario: Single loop per Job plane instance

- **WHEN** a collector runs a bounded Owner-bot Job using the shared evidence plane
- **THEN** async PG and WB operations for that run SHALL execute on one Job-owned loop
- **AND** the plane SHALL NOT call `asyncio.run()` repeatedly in a pattern that re-binds module-level async SQLAlchemy engines across incompatible loops

#### Scenario: Deterministic cleanup

- **WHEN** the Job run completes or aborts at the plane boundary
- **THEN** the plane SHALL close/dispose async resources tied to that execution
- **AND** subsequent Job runs SHALL NOT inherit stale loop-bound sessions or clients

### Requirement: Shared read-only WB/PG primitives

Evidence loading SHALL reuse existing shared modules and official adapters:

- `scripts/wb_api_readonly_ops/collect/orders_sales.py` for orders/sales;
- supported `FullstatsAdapter` methods (`_request_chunk` / `get_full_adv_stat` family);
- existing `DIManager` / WB hub access;
- Job-safe reusable PG read strategy aligned with A1-stable asyncpg path
  (`scripts/ch_a1_evidence.py` semantics or extracted equivalent).

Collectors MUST NOT invoke non-existent adapter methods or parallel raw HTTP clients.

#### Scenario: Supported Fullstats seam

- **WHEN** fullstats/spend evidence is loaded
- **THEN** the loader SHALL call only supported Fullstats adapter APIs
- **AND** MUST NOT reference orphan methods (for example `get_fullstats`) absent from the adapter

#### Scenario: Orders identity preserved

- **WHEN** orders/sales are collected for evidence plane consumers
- **THEN** the loader SHALL use the shared orders/sales collect path
- **AND** SHALL preserve accepted `ORDERS_OR_SALES_REPORTS_READ` identity semantics

### Requirement: Typed reader failure provenance

Reader and lifecycle failures SHALL be represented as structured provenance
(source, phase, error class, safe message) consumable by collector output
contracts. Collectors MAY emit `PARTIAL` when contract validation and write budget
remain valid.

#### Scenario: Adapter failure becomes typed GAP

- **WHEN** a supported reader fails due to adapter, network, or lifecycle error
- **THEN** the failure SHALL be recorded with typed provenance
- **AND** MUST NOT rely solely on an unqualified section-level exception name without source context

#### Scenario: Zero writes preserved

- **WHEN** evidence loading runs under this plane
- **THEN** production/shared writes SHALL remain zero
- **AND** mutation guard violations SHALL fail closed

### Requirement: Consumer compatibility without Registry change

Strict single-NMID audit and A1 strict read-only collect SHALL consume the shared
plane without new Registry ids, resolver semantic changes, or new collector
registration.

#### Scenario: A1 non-regression

- **WHEN** shared plane changes are applied
- **THEN** A1 strict read-only collect targeted regression tests SHALL pass
- **AND** existing A1 output contract behavior SHALL not regress

#### Scenario: Strict-NMID uses shared plane

- **WHEN** strict single-NMID Job runs after apply
- **THEN** it SHALL use the shared evidence loader/primitives
- **AND** SHALL NOT introduce a parallel ProKraft-specific access stack

### Requirement: Focused automated verification

The change SHALL add or extend targeted automated tests proving:

- no cross-incompatible-loop reuse of async SQLAlchemy engines in the plane path;
- supported Fullstats adapter seam (regression forbidding orphan API names);
- resource cleanup at plane `close()`;
- typed failure mapping at orchestration boundary;
- A1 strict collect regression coverage for shared loader integration;
- SQLAlchemy `RowMapping` (or equivalent execute/result mapping type) → plain
  `dict` without GAP recast; unsupported non-mapping → explicit `TypeError`.

#### Scenario: Cross-loop regression test

- **WHEN** unit/integration tests simulate multiple plane open/close cycles
- **THEN** tests SHALL fail if module-level engines are used across closed loops
- **AND** SHALL pass when Job-scoped lifecycle is correct

#### Scenario: Orphan API guard

- **WHEN** static or unit tests inspect strict plane fullstats loading
- **THEN** tests SHALL fail if disallowed adapter method names are introduced

### Requirement: SQLAlchemy PG row mapping normalization

Shared PG row normalization used by the Owner-bot Job evidence plane SHALL
accept actual SQLAlchemy mapping results from the Job execute/result path and
normalize them deterministically to a plain `dict` with unchanged column names
and values. The normalizer SHALL use Python/SQLAlchemy mapping protocol
semantics (`collections.abc.Mapping`), not a `dict`-only type check.

SQLAlchemy `engine.row.RowMapping` SHALL be accepted as mapping data.
If SQLAlchemy `Row` is a supported upstream result at another seam, the
normalizer SHALL use the documented mapping interface (`row._mapping`) rather
than positional or private field guessing. Unsupported arbitrary objects SHALL
fail closed with an explicit `TypeError`.

This TypeError is an implementation defect. Collectors MUST NOT convert it into
a legitimate evidence GAP. Job-local PG engine/session ownership, one
Job-scoped loop, deterministic dispose, typed `EvidenceReaderFailure`,
read-only posture, and existing WB/fullstats/orders behavior SHALL be
preserved. The change SHALL NOT rewrite the plane to asyncpg or introduce a
ProKraft-specific reader.

#### Scenario: RowMapping normalizes to plain dict

- **WHEN** the Job PG path yields `sqlalchemy.engine.row.RowMapping` (or an
  execute/result seam that returns the same concrete mapping type)
- **THEN** shared `_pg_row_as_dict` SHALL return a plain `dict`
- **AND** column names and values SHALL be unchanged
- **AND** the failure SHALL NOT be recorded as a legitimate evidence GAP

#### Scenario: SQLAlchemy Row uses documented mapping

- **WHEN** a supported seam yields SQLAlchemy `Row`
- **THEN** the normalizer SHALL obtain mapping data via `row._mapping`
- **AND** SHALL NOT infer columns from positional or undocumented private
  attributes

#### Scenario: Unsupported object fails closed

- **WHEN** `_pg_row_as_dict` receives a non-mapping object that is not a
  supported SQLAlchemy row/mapping result
- **THEN** it SHALL raise an explicit `TypeError`
- **AND** SHALL NOT silently coerce the object into a dict or GAP

#### Scenario: RowMapping regression evidence

- **WHEN** the required automated regression runs against real SQLAlchemy
  `RowMapping` (preferably via execute/result)
- **THEN** a dict-only / current-broken helper SHALL fail on that type
- **AND** the corrected normalizer SHALL produce the expected plain dict
- **AND** a negative case SHALL still fail closed for an unsupported
  non-mapping object

### Requirement: Bundle result-shape normalization for section readers

Shared Owner-bot evidence loading SHALL produce bundle collections that section
readers consume as plain `dict` trees at every `.get()` boundary:

- `OwnerBotEvidenceBundle.pg_rows` — plain `dict` per PG advsetting row (post
  `_pg_row_as_dict`);
- `orders` — plain `dict` supplier order rows (post `jsonable` / pagination
  merge semantics);
- `fullstats` — plain `dict` per campaign stats item with recursively
  JSON-safe `days` / `apps` / `nms` nodes (post `FullStatsItem.to_dict()` +
  `jsonable`, or equivalent supported adapter mapping).

Non-dict rows or campaign stats objects (for example attrs `FullStatsItem`
instances) MUST NOT reach `OwnerBotStrictSingleNmidReadOnlyPlane` section
readers. Failures from unsupported shapes are **implementation defects** and
MUST NOT be reported as legitimate typed source GAPs solely because the
orchestrator caught `AttributeError`.

#### Scenario: PG rows are dict-safe for current_contour

- **WHEN** the Job bundle is loaded for a supported cabinet
- **THEN** each `pg_rows` entry SHALL be a plain `dict` usable with `.get()`
- **AND** `read_current_contour` SHALL NOT raise `AttributeError` for supported
  SQLAlchemy mapping inputs already accepted by `_pg_row_as_dict`

#### Scenario: Orders rows are dict-safe for ORDERS reader

- **WHEN** orders are loaded via shared `collect_orders_sales`
- **THEN** each `bundle.orders` entry SHALL be a plain `dict` with WB field names
- **AND** `read_orders` SHALL NOT raise `AttributeError` on supported supplier
  order payloads

#### Scenario: Fullstats tree is dict-safe for attribution and spend

- **WHEN** fullstats are loaded via supported `FullstatsAdapter._request_chunk`
- **THEN** each `bundle.fullstats` entry and nested day/app/nm nodes SHALL be
  plain dicts (or explicitly typed GAP at load with provenance)
- **AND** `read_attribution` / `read_physical_spend` SHALL NOT raise
  `AttributeError` on supported production-shaped payloads

### Requirement: Implementation failure vs legitimate GAP at section boundary

`StrictSingleNmidAudit.run` SHALL distinguish:

- legitimate source absence / adapter failure → typed `EvidenceReaderFailure` or
  contract GAP with provenance;
- malformed or unsupported **bundle/result shape** caused by loader/reader code →
  implementation failure (fix shape or raise typed implementation failure), not
  silent `{section}: AttributeError` as the only signal.

Arbitrary `AttributeError` from `.get()` on non-dict bundle entries MUST NOT be
treated as authoritative evidence absence. Wrapping all `AttributeError` into
`EvidenceReaderFailure` without fixing shapes is forbidden.

#### Scenario: AttributeError from shape mismatch is not authoritative GAP

- **WHEN** a section reader raises `AttributeError` because a bundle entry is not
  dict-shaped at a `.get()` boundary
- **THEN** apply fixes SHALL normalize bundle data or harden the load contract
- **AND** the collector MUST NOT treat that bare exception class alone as proof
  that the upstream WB/PG source is unavailable

#### Scenario: Typed source failure remains GAP

- **WHEN** shared loading raises `EvidenceReaderFailure` for a supported source
  (network, adapter, identity, lifecycle)
- **THEN** orchestration SHALL record typed provenance (`source`, `phase`,
  `error_class`)
- **AND** `write_budget.writes` SHALL remain `0`

### Requirement: Physical spend canonical reconciliation matches section evidence

When `read_physical_spend` yields confirmed `SpendEvidence` for the audit
identity and period, `reconcile_physical_spend` SHALL populate canonical
`physical_spend` (`status`, `value`, `evidence`) consistently with the strict
single-NMID audit contract. Confirmed spend facts MUST NOT appear only in
top-level `evidence[]` while canonical `physical_spend` remains `missing`.

#### Scenario: Confirmed spend in reader reconciles to canonical object

- **WHEN** the physical spend reader yields confirmed `SpendEvidence` with an
  explicit overlap key for the audit window
- **THEN** `physical_spend.status` SHALL be `confirmed`
- **AND** `physical_spend.value` SHALL match the reconciled total
- **AND** `physical_spend.evidence` SHALL include the spend records used

#### Scenario: t0055 regression shape

- **WHEN** regression tests replay t0055-like bundle/output shapes (confirmed
  spend fact `562.01` with overlap keys from promotion fullstats)
- **THEN** canonical `physical_spend` SHALL NOT remain `missing`
- **AND** `decision.gaps` SHALL NOT include `physical spend evidence is missing`
  unless spend is genuinely absent

## OUT OF SCOPE (explicit)

- Inventing authoritative stock views or full direct/associated attribution endpoint catalogs without an already accepted shared source.
- Registry/resolver semantic changes.
- New collector registration.
- Production/shared writes.
