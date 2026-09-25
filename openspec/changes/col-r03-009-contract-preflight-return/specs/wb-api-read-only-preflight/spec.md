## ADDED Requirements

### Requirement: Explicit contract and artifact-class CLI surface

The operator read-only preflight/collect entrypoint SHALL accept explicit
contract and artifact-class controls: contract identifier COL-R03-009,
artifact class values `contract_preflight`, `l0_research`, and `clean_dump`,
bound account alias, period start/end, and a require-preflight-pass input
path for clean_dump. When contract COL-R03-009 or artifact class
`contract_preflight` is selected, the run MUST follow the contract primary
RETURN rules of capability `wb-readonly-contract-preflight-return` and MUST
NOT treat an L0 research archive as the primary Web COLLECTOR accept
artifact.

#### Scenario: Contract flags select contract preflight path

- **WHEN** the operator supplies contract COL-R03-009 and artifact class
  `contract_preflight` with bound alias and period bounds
- **THEN** the system SHALL enter the contract preflight packaging path
- **AND** MUST NOT present L0 research output as the primary COLLECTOR
  handoff

#### Scenario: Default L0 research remains available without contract

- **WHEN** the operator runs preflight or collect without contract
  COL-R03-009 and without artifact class `contract_preflight`
- **THEN** the existing Owner-local L0 research archive path MAY still
  operate as before
- **AND** MUST NOT claim Web COLLECTOR handoff readiness solely from that
  L0 archive

### Requirement: Collect without accept cannot claim clean dump readiness

When the operator requests artifact class `clean_dump` or otherwise requires
a preflight-pass accept file, the system MUST fail closed without API calls
unless `READ_ONLY_PREFLIGHT_PASS=YES` is evidenced. The system MUST NOT
declare Web `READ_ONLY_PREFLIGHT_PASS` from the Job itself.

#### Scenario: Ungated collect is not Web pass

- **WHEN** a collect or clean_dump path runs without evidenced
  `READ_ONLY_PREFLIGHT_PASS=YES`
- **THEN** clean_dump MUST fail closed with no API calls
- **AND** the Job MUST NOT assert Web `READ_ONLY_PREFLIGHT_PASS`
