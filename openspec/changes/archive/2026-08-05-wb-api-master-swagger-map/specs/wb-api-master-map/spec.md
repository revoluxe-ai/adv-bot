## ADDED Requirements

### Requirement: Offline API Master map from local swagger

The system SHALL provide an operator/tooling command that builds an API Master
inventory map of path × method × family strictly from already-saved local
versioned swagger documents. The command MUST NOT download swagger from the
network and MUST NOT generate or regenerate an API client as part of the same
run.

#### Scenario: Successful map from local specs

- **GIVEN** one or more local versioned swagger documents for known API
  families exist on disk
- **WHEN** the operator runs the API Master map command against those local
  sources
- **THEN** the system SHALL produce a reproducible inventory map artifact
  whose entries include path, HTTP method, and family
- **AND** every path and method in the map MUST appear in the parsed local
  swagger documents
- **AND** the run MUST NOT perform network download of swagger
- **AND** the run MUST NOT invoke client code generation

#### Scenario: No invent URL

- **WHEN** the map command builds the inventory
- **THEN** the system MUST NOT add path or method entries that were not
  present in the local swagger documents
- **AND** MUST NOT hardcode WB URLs as map entries outside swagger parsing

### Requirement: Family bound to swagger source

Each map entry's family MUST identify the swagger source family of the
document that contributed the path and method, not an arbitrary label
unrelated to that source.

#### Scenario: Family matches source family

- **GIVEN** a local swagger document belonging to a known family source
- **WHEN** the map command includes operations from that document
- **THEN** each included entry SHALL carry that source family identity

### Requirement: Deterministic inventory artifact

For the same set of local swagger inputs, the system SHALL emit a
deterministic machine-readable inventory artifact (stable ordering of
entries) suitable for later allowlist use. A human-readable view MAY be
produced in addition, but MUST NOT be the only artifact.

#### Scenario: Repeatable output

- **GIVEN** unchanged local swagger inputs
- **WHEN** the operator runs the map command twice with the same options
- **THEN** the machine-readable inventory content SHALL be identical
  (aside from any explicitly non-compared timestamp metadata, if present)

### Requirement: Honest gaps without fabricated entries

When a configured family source is missing, empty, or not parseable, the
system SHALL report an honest gap or failure for that source and MUST NOT
fabricate path or method entries to fill the gap.

#### Scenario: Missing or unreadable swagger source

- **GIVEN** a configured family source has no usable local swagger document
- **WHEN** the map command runs
- **THEN** the system SHALL record a gap or failure for that source
- **AND** MUST NOT invent endpoints for that family

#### Scenario: Total source failure is not silent success

- **GIVEN** no configured swagger sources can be parsed into any entries
- **WHEN** the map command completes
- **THEN** the system MUST NOT report overall success as if a valid allowlist
  were produced from invented data

### Requirement: Map does not authorize WB calls

Producing or possessing an API Master inventory map MUST NOT by itself
authorize calls to the Wildberries API, require shop credentials, or declare
collect Job / Web Stage B success.

#### Scenario: Offline build needs no shop access

- **WHEN** the operator runs the API Master map command
- **THEN** the system MUST NOT require a shop identifier or cabinet token
- **AND** MUST NOT call the Wildberries API

### Requirement: Mutation filter out of scope for this capability

This capability SHALL inventory methods as declared in local swagger,
including non-GET methods when present. Restricting the map to read-only or
mutation-safe subsets for collect policy is out of scope for this capability.

#### Scenario: Declared methods are inventoried

- **GIVEN** a local swagger document declares multiple HTTP methods under a
  path
- **WHEN** the map command parses that document successfully
- **THEN** the inventory SHALL include those declared methods for that path
  and family
- **AND** SHALL NOT silently drop methods solely because they are not GET
