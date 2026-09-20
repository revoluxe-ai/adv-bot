## ADDED Requirements

### Requirement: Generic bounded single-NMID audit

The system SHALL provide a reusable strict read-only audit for exactly one
NMID, without ProKraft-specific assumptions, campaign-specific hardcoding or
unbounded multi-NMID collection. The audit SHALL accept an explicit shop,
cabinet, NMID, size and timezone identity.

#### Scenario: Pilot identity is accepted as explicit input

- **GIVEN** `shop_id=5586b2ff-449c-4151-9518-60f46d32b7d9`, cabinet `573`,
  NMID `186069402`, size `305698863` and timezone `Europe/Moscow`
- **WHEN** the audit is requested
- **THEN** it SHALL use those values as the audit identity
- **AND** it SHALL not treat them as the only supported identity

#### Scenario: Audit does not widen to multiple NMIDs

- **WHEN** the requested audit has one NMID identity
- **THEN** it SHALL not silently collect or summarize unrelated NMIDs
- **AND** any required source that cannot preserve the identity SHALL produce a
  gap or unsupported result

### Requirement: Identity-safe routing and fail-closed source selection

Every collected evidence record SHALL preserve the exact shop, cabinet, NMID,
size and timezone identity. The audit MUST NOT use A1 fallback, an unrelated
collector or package substitution, or silent identity widening.

#### Scenario: Exact identity mismatch blocks evidence

- **GIVEN** a source response identifies another shop, cabinet, NMID or size
- **WHEN** the response is evaluated for the audit
- **THEN** it SHALL be rejected for the audit
- **AND** the report SHALL record a gap or blocked result with the mismatch

#### Scenario: A1 fallback is unavailable

- **WHEN** the requested source or contour is absent
- **THEN** the audit SHALL report `NONE`, `GAP` or `unsupported` according to
  the observed condition
- **AND** it MUST NOT substitute A1 or an unrelated package to fill the field

### Requirement: Current contour inventory

The audit SHALL report the current contour for the exact identity, including
NMID/OFFER, AdvSetting, Auto, Search, other relevant IDs, WB statuses, bot
settings, CPO and limits. A contour element with no supported evidence SHALL
be represented as `NONE` or an explicit gap, not guessed.

#### Scenario: Current contour is fully or partially available

- **WHEN** current-contour sources return evidence for the requested identity
- **THEN** the report SHALL include the available elements with provenance
- **AND** each unavailable element SHALL retain its own status rather than
  being promoted to overall success

#### Scenario: No contour exists for a requested element

- **WHEN** no authoritative contour evidence exists for an element
- **THEN** that element SHALL be reported as `NONE` or `GAP`
- **AND** the audit SHALL not infer a campaign, offer, setting or status from
  an unrelated identifier

### Requirement: Fourteen-calendar-day factual economics

The audit SHALL cover 14 calendar days including the current day in the
declared timezone and SHALL report factual orders, units, GMV and physical
spend for the exact identity. Each section SHALL attest the period actually
covered by its authoritative source.

#### Scenario: Current-day inclusive window

- **WHEN** the audit runs in `Europe/Moscow`
- **THEN** its requested window SHALL contain the current local day and the
  preceding 13 calendar days
- **AND** the machine-readable and human outputs SHALL state the timezone and
  window boundaries

#### Scenario: Source cannot represent the full window

- **WHEN** an authoritative source supports only a different period model or
  only a partial window
- **THEN** the affected metric SHALL be marked with an honest gap and period
  attestation
- **AND** the audit MUST NOT use glue inference to claim a complete
  14-calendar-day fact

### Requirement: Authoritative attribution and topology

The audit SHALL distinguish direct and associated attribution and SHALL include
topology only when an authoritative supported source provides it. It MUST NOT
infer association or topology from coincidental IDs, names, text or aggregate
metrics.

#### Scenario: Direct and associated evidence are supported

- **WHEN** authoritative sources provide direct and associated attribution for
  the exact identity
- **THEN** the report SHALL keep those evidence classes separate
- **AND** each class SHALL include source provenance and period coverage

#### Scenario: Association is not authoritative

- **WHEN** no supported authoritative source proves an association or topology
- **THEN** the relationship SHALL be reported as `GAP`, `NONE` or
  `unsupported`
- **AND** it SHALL not be synthesized from matching identifiers or totals

### Requirement: Canonical totals and physical-spend protection

The audit SHALL calculate totals, CPO and DRR only from identity-safe,
period-compatible evidence. Physical spend SHALL have one canonical
representation in the final economics, and overlapping evidence SHALL NOT be
counted twice.

#### Scenario: Overlapping physical-spend evidence is returned

- **WHEN** two sources cover the same physical spend for the same identity and
  period
- **THEN** reconciliation SHALL retain one canonical amount
- **AND** the output SHALL record the overlap/reconciliation provenance

#### Scenario: Evidence cannot be reconciled safely

- **WHEN** physical-spend sources overlap but no safe reconciliation is
  available
- **THEN** the physical-spend total SHALL be a gap or undefined result
- **AND** the audit MUST NOT add the amounts as a glue total

#### Scenario: Derived metric denominator is zero

- **WHEN** a CPO or DRR denominator is zero
- **THEN** the derived metric SHALL be `UNDEFINED`
- **AND** it MUST NOT be represented as zero or as a fabricated numeric value

### Requirement: Missing, null and unsupported semantics

The output SHALL distinguish at least `missing`, `null`, `unsupported` and
`GAP` states. A missing source/record, a present null value, an unavailable
capability and an incomplete/invalid collection SHALL not be conflated.

#### Scenario: Source is missing

- **WHEN** the required source or record is absent
- **THEN** the affected field SHALL carry `missing` or an equivalent explicit
  gap classification
- **AND** it SHALL not be converted to numeric zero

#### Scenario: Source value is null

- **WHEN** a present authoritative source returns a null value
- **THEN** the field SHALL retain `NULL`
- **AND** null SHALL remain distinct from missing, zero and unsupported

#### Scenario: Capability is unsupported

- **WHEN** the audit has no supported capability for a requested field
- **THEN** the field SHALL be marked `unsupported`
- **AND** the report SHALL not imply that the field was collected and found
  empty

#### Scenario: Denominator is absent

- **WHEN** a derived metric lacks a valid denominator
- **THEN** its value SHALL be `UNDEFINED` or `NULL` according to whether the
  denominator is undefined or explicitly null
- **AND** the output SHALL explain the denominator state

### Requirement: Stock coverage

The audit SHALL report FBO, FBS and TOTAL stock when authoritative evidence
supports those views. If one or more required views cannot be supported, the
affected view SHALL carry an explicit gap rather than an inferred quantity.

#### Scenario: Stock views are available

- **WHEN** authoritative stock evidence covers FBO, FBS and TOTAL for the exact
  identity
- **THEN** the output SHALL report the views separately
- **AND** TOTAL SHALL not be silently recomputed from incompatible or
  overlapping stock sources

#### Scenario: Stock view is unavailable

- **WHEN** an FBO, FBS or TOTAL view is not supported or not returned
- **THEN** that view SHALL be reported as an explicit `GAP` or `unsupported`
- **AND** the audit SHALL not present a guessed stock value

### Requirement: Machine-readable and human decision output

The audit SHALL emit a machine-readable result and a human-readable summary
derived from the same evidence. Both SHALL include exact identity, period,
section statuses, provenance, gaps, totals/derived metric states, stock
coverage and a decision block that separates confirmed facts from
`NONE`/`GAP`/`NULL`/`UNDEFINED` outcomes.

#### Scenario: Output contract validates

- **WHEN** the audit completes with full or partial evidence
- **THEN** the machine-readable result SHALL validate against the output
  contract
- **AND** the human summary SHALL agree with its normalized facts and statuses
- **AND** the decision block SHALL state whether the result is actionable,
  partial or blocked

#### Scenario: Collection has unresolved gaps

- **WHEN** one or more required sections contain unresolved gaps
- **THEN** the decision block SHALL expose those gaps
- **AND** it MUST NOT claim complete audit success
- **AND** if identity, output contract validation and write budget remain valid,
  `decision.status` MAY be `PARTIAL` rather than `BLOCKED`

#### Scenario: Fail-closed contract violation

- **WHEN** identity is ambiguous, substituted, write-capable execution occurs,
  output contract validation fails, or mandatory execution provenance is missing
- **THEN** `decision.status` SHALL be `BLOCKED` (or execution SHALL fail closed
  before a trustworthy artifact is emitted)
- **AND** `BLOCKED` MUST NOT be used solely because individual evidence sections
  have GAP or reader/runtime errors while the aggregate output contract is valid

### Requirement: Strict read-only safety and bounded execution

The audit SHALL run through the approved Owner-bot Job and existing WB API
stack with finite per-source and whole-run budgets. It MUST perform zero
production/shared writes, including WB, DB, Redis, Excel, campaign,
infrastructure and bot-state mutation.

#### Scenario: Mutation path is requested

- **WHEN** an execution path would create, update, delete, start, stop or
  otherwise mutate production/shared state
- **THEN** the audit SHALL refuse or prevent that path
- **AND** the output SHALL remain a read-only audit result

#### Scenario: Retry budget is exhausted

- **WHEN** a source remains unavailable after its bounded retry or timeout
  budget
- **THEN** the audit SHALL stop that source and record a gap
- **AND** it SHALL not retry indefinitely or silently report success

### Requirement: Targeted automated coverage

The implementation SHALL include targeted automated tests without live
production WB calls for exact identity routing, A1-fallback rejection,
missing/null/unsupported semantics, duplicate physical-spend prevention and
machine/human output-contract validation.

#### Scenario: Identity and fallback regression suite

- **WHEN** the targeted identity tests run
- **THEN** they SHALL verify exact shop/cabinet/NMID/size routing
- **AND** SHALL fail if A1 fallback or unrelated collector substitution is used

#### Scenario: Evidence and output regression suite

- **WHEN** the targeted evidence tests run
- **THEN** they SHALL verify distinct missing/null/unsupported states,
  `NULL`/`UNDEFINED` denominator semantics and no duplicate physical spend
- **AND** SHALL verify that machine-readable and human decision outputs satisfy
  the contract
