## ADDED Requirements

### Requirement: Contract preflight produces COL-R03-009 primary RETURN

When the operator runs read-only preflight under contract COL-R03-009 with
artifact class `contract_preflight`, the system SHALL produce a primary
RETURN package named exactly
`REQ-WBSKY-AUDIT-METHODOLOGY-V1-PILOT-DATA-COLLECTION-001_COL-R03-009_RETURN.zip`
and a matching `.sha256` sidecar. The RETURN zip MUST contain the contract
file set required by COL-R03-009 (including `00_STATUS.yaml`, mapping and
preflight registers, per-alias evidence files, cleanup and secret-scan
attestations, and `SHA256SUMS.txt`). Absence of the primary zip or sidecar
MUST yield a non-zero exit even if some endpoint families otherwise succeed.

#### Scenario: Contract preflight emits primary RETURN and sidecar

- **WHEN** the operator runs with contract COL-R03-009 and artifact class
  `contract_preflight`
- **THEN** the system SHALL write the exact COL-R03-009 RETURN zip name as
  the primary artifact
- **AND** SHALL write a `.sha256` sidecar whose digest matches that zip
- **AND** MUST NOT treat success as complete if the primary zip is missing

#### Scenario: Honest REFUSED still packages RETURN

- **WHEN** one or more required endpoint aliases are refused with exact
  blockers under contemporaneous mapping rules
- **THEN** the system SHALL still produce the primary RETURN zip
- **AND** SHALL record `api_preflight` as `REFUSED` (or equivalent refused
  disposition) with those blockers in `00_STATUS.yaml`
- **AND** MUST NOT retrofit a prior L0 research dump into a PASS or
  PASS_CANDIDATE disposition

### Requirement: L0 research archive is side-only under contract preflight

Under artifact class `contract_preflight` / contract COL-R03-009, an L0
research archive (Owner-local research zip) MAY be emitted only as a side
artifact. The L0 archive MUST NOT be the primary Web COLLECTOR handoff and
MUST NOT alone authorize `WEB_COLLECTOR_HANDOFF` / external handoff ready.

#### Scenario: L0 cannot satisfy Web handoff

- **WHEN** contract preflight completes with an L0 research zip present and
  the primary RETURN zip absent
- **THEN** the system MUST exit non-zero or otherwise fail the contract
  artifact gate
- **AND** MUST NOT report Web COLLECTOR handoff as ready

#### Scenario: Optional L0 side with primary present

- **WHEN** contract preflight produces both primary RETURN and an optional
  L0 research zip
- **THEN** the report SHALL identify RETURN as `PRIMARY_ARTIFACT`
- **AND** SHALL identify the L0 zip as side (`L0_SIDE_ARTIFACT` or
  equivalent)
- **AND** MAY set Web COLLECTOR handoff ready only when primary exists and
  its sha matches

### Requirement: Contract RETURN excludes secrets and raw rows

The COL-R03-009 RETURN package MUST NOT contain token values, Authorization
headers, cookies, passwords, `shop_id`, raw response rows/bodies, or raw
request headers. Secret scan attestation in the RETURN MUST reflect that
constraint.

#### Scenario: RETURN has no shop_id or token material

- **WHEN** a contract RETURN package is produced
- **THEN** it MUST NOT include token or Authorization material
- **AND** MUST NOT include `shop_id` or raw response row payloads
- **AND** SHALL record secret-scan disposition consistent with that absence

### Requirement: Clean dump requires preflight pass input

When artifact class is `clean_dump` (or collect is gated by
`--require-preflight-pass`), the system MUST require evidence that
`READ_ONLY_PREFLIGHT_PASS=YES`. Without that evidence the run MUST exit
non-zero and MUST NOT perform API calls for that collect path.

#### Scenario: Clean dump without pass fails closed

- **GIVEN** no accept input asserting `READ_ONLY_PREFLIGHT_PASS=YES`
- **WHEN** the operator requests artifact class `clean_dump`
- **THEN** the system MUST exit non-zero
- **AND** MUST NOT perform API calls for that run

### Requirement: Operator report exposes contract artifact fields

For contract / artifact-class runs the structured operator report (and any
SCRIPTS_REPORT derived from it) MUST expose at least: `ARTIFACT_CLASS`,
`PRIMARY_ARTIFACT`, `PRIMARY_SHA256`, `L0_SIDE_ARTIFACT` (or equivalent side
field), `WEB_COLLECTOR_HANDOFF` (or equivalent external handoff ready), and
`CONTRACT_ID`. `PRIMARY_SHA256` MUST equal the digest of the primary zip on
disk when a primary is declared. Web COLLECTOR handoff ready MUST be YES only
when the primary exists and the digest matches.

#### Scenario: Report fields for contract preflight

- **WHEN** contract preflight writes a primary RETURN zip
- **THEN** the report SHALL set `ARTIFACT_CLASS` to `contract_preflight`
- **AND** SHALL set `CONTRACT_ID` to `COL-R03-009`
- **AND** SHALL set `PRIMARY_ARTIFACT` and `PRIMARY_SHA256` to that zip and
  its digest
- **AND** MUST set Web COLLECTOR handoff ready to YES only if the digest
  matches the file on disk

#### Scenario: Archive digest matches primary zip

- **WHEN** the run records an archive or primary sha in the report
- **THEN** that digest MUST match the primary contract zip bytes on disk
- **AND** MUST NOT claim a matching handoff when the digests differ

### Requirement: Targeted automated coverage without live production API

The system SHALL have targeted automated tests (without live production WB
API) covering: contract packager exact required file set; non-zero exit when
contract mode lacks RETURN; clean_dump / require-pass without accept yields
non-zero and zero API calls; L0 research mode still can write a research zip;
sha sidecar equals zip digest; secret-strip / RETURN exclusions for shop_id
and token material.

#### Scenario: Unit suite covers packager gates

- **WHEN** the targeted automated suite for this capability runs
- **THEN** it MUST exercise packager and CLI gates without calling live
  production WB API
- **AND** MUST assert primary naming and required RETURN membership
- **AND** MUST assert fail-closed behavior when primary is missing or
  clean_dump lacks pass input
