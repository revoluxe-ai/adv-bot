## ADDED Requirements

### Requirement: ORDERS period collect with cursor follow

For `--mode collect` of family `ORDERS_OR_SALES_REPORTS_READ` under INC-RO-08
period rules, the system SHALL follow Statistics/Reports pagination /
`lastChangeDate` continuation after the initial `dateFrom`-aligned request,
for both supplier orders and supplier sales, until the research window
`2026-07-04..2026-08-02` Europe/Moscow is covered per the honest
`DATE_FROM_CURSOR` model **or** a documented finite stop condition fires.
The system MUST NOT claim a classic exact start+end query model when the API
only supports `dateFrom`/cursor continuation. The system MUST NOT silently
substitute yesterday→today for the attested window start. Stage A / preflight
first-page behavior (no cursor follow) MUST remain unchanged for Stage A
paths.

#### Scenario: Collect follows cursor within period window

- **GIVEN** collect runs `ORDERS_OR_SALES_REPORTS_READ` for the pilot window
  starting `2026-07-04` Europe/Moscow with research end `2026-08-02`
- **WHEN** the first page for supplier orders (and separately sales) returns
  and continuation is available before a stop condition
- **THEN** the Job SHALL follow next-page / `lastChangeDate` continuation
- **AND** SHALL record `next_page_followed` as yes (or equivalent affirmative)
  when at least one continuation page was requested
- **AND** SHALL NOT claim classic exact start+end period semantics in
  attestation

#### Scenario: Stage A first-page path unchanged

- **WHEN** preflight or Stage A collect rules apply to ORDERS
- **THEN** the system MUST NOT follow `lastChangeDate` continuation under
  Stage A
- **AND** MUST keep Stage A attestation as first-page / no next-page follow

#### Scenario: Forbidden silent yesterday-today for period collect

- **WHEN** period collect runs ORDERS under the pilot window rules
- **THEN** the system MUST NOT substitute a default yesterday→today range in
  place of attested `dateFrom=2026-07-04`

### Requirement: Finite ceiling and honest stop attestation for ORDERS period collect

Period collect for `ORDERS_OR_SALES_REPORTS_READ` SHALL enforce a finite
budget (maximum pages and/or maximum wall-time, or an equivalent dual
ceiling). When the budget is exhausted, the system MUST stop further
continuation requests, retain already collected rows, and record an honest
stop reason such as ceiling hit (not silent success-as-complete). Other stop
reasons MUST be distinguishable in the structured report, including at least:
period/window coverage heuristic met, empty page / no continuation, and API
or transport error. Infinite pagination without a ceiling is forbidden.

#### Scenario: Ceiling stops pagination honestly

- **GIVEN** period collect is following cursor pages for orders or sales
- **WHEN** the configured finite page or time budget is exhausted
- **THEN** the system MUST stop requesting further continuation pages
- **AND** MUST record a ceiling-hit (or equivalent) stop reason in the report
- **AND** MUST retain rows already collected for the L0 research archive

#### Scenario: Distinct stop reasons

- **WHEN** period collect ends
- **THEN** the structured report MUST include a stop reason that distinguishes
  ceiling hit from empty-page/no-continuation and from API/transport error
- **AND** MUST include period-model attestation consistent with
  `DATE_FROM_CURSOR`

### Requirement: Bound Dilera cabinet by argument for ORDERS period collect

Period collect for this capability SHALL bind the pilot cabinet «Дилера» /
`WB-TEST-CABINET-001` only via Job/`--shop-id` (or equivalent) argument. The
system MUST NOT hard-code that shop identity as a permanent production
default in the operator path.

#### Scenario: Shop identity from argument

- **WHEN** operator runs period collect for the Dilera pilot
- **THEN** the shop/cabinet identity MUST come from the invocation argument
- **AND** MUST NOT be permanently baked into code as the only runnable shop

### Requirement: Owner-local L0 research archive for ORDERS period collect

Successful or partial period collect that obtained ORDERS and/or sales rows
SHALL produce an Owner-local L0 research archive (payload + structured
report, secret-strip only) suitable for delivery via the scripts Job contour
(`/opsx-scripts`). The archive MUST NOT be treated as Web CLEAN_DUMP,
RETURN pack, or `READ_ONLY_PREFLIGHT_PASS`. Tokens, Authorization headers,
and cookies MUST NOT appear in archive or report outputs.

#### Scenario: L0 archive without Web PASS claim

- **WHEN** period collect finishes with ORDERS and/or sales rows retained
- **THEN** the system SHALL emit Owner-local L0 research outputs (payload +
  report) with secret-strip
- **AND** MUST NOT declare Web CLEAN_DUMP, RETURN, or
  `READ_ONLY_PREFLIGHT_PASS` from this path

### Requirement: Targeted automated coverage for ORDERS period cursor collect

The system SHALL have targeted automated tests (without live production WB
API) that cover period-collect cursor follow for `ORDERS_OR_SALES_REPORTS_READ`,
including: at least one continuation page followed; finite ceiling stop with
honest attestation; and residual/repeated-invocation behavior that does not
silently claim full period coverage after a ceiling stop.

#### Scenario: Unit coverage of cursor follow without live WB

- **WHEN** the targeted automated suite for period collect runs
- **THEN** it MUST exercise cursor/continuation follow for ORDERS (orders
  and/or sales paths as required by family contract) without calling live
  production WB API
- **AND** MUST assert that continuation was requested when mocked pages
  provide a next cursor

#### Scenario: Unit coverage of ceiling stop

- **WHEN** mocked pages would continue beyond the configured finite budget
- **THEN** tests MUST assert stop with ceiling-hit (or equivalent) attestation
- **AND** MUST assert retained partial rows are not discarded solely because
  the ceiling fired
