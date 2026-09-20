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
- A1 strict collect regression coverage for shared loader integration.

#### Scenario: Cross-loop regression test

- **WHEN** unit/integration tests simulate multiple plane open/close cycles
- **THEN** tests SHALL fail if module-level engines are used across closed loops
- **AND** SHALL pass when Job-scoped lifecycle is correct

#### Scenario: Orphan API guard

- **WHEN** static or unit tests inspect strict plane fullstats loading
- **THEN** tests SHALL fail if disallowed adapter method names are introduced

## OUT OF SCOPE (explicit)

- Inventing authoritative stock views or full direct/associated attribution endpoint catalogs without an already accepted shared source.
- Registry/resolver semantic changes.
- New collector registration.
- Production/shared writes.
