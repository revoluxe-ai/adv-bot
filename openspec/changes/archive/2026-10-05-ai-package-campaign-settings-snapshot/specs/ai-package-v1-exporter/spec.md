## MODIFIED Requirements

### Requirement: PostgreSQL campaign inventory and relations (minimal v1)

The export MAY include a PostgreSQL **campaign inventory / relations** dataset
(manifest card id `campaign_settings_snapshot`). When change
`ai-package-campaign-settings-snapshot` is applied, export MUST materialize the
**detailed** read-only campaign settings snapshot defined by
`ai-package-campaign-settings-snapshot` spec (`CampaignSettingsSnapshotV1`) for
in-scope shop inventory rows. Until that implementation lands, export MAY continue
minimal shop-scoped fields only: `AdvSetting` rows joined to `WBCabinet.shop_id`,
campaign identifiers, and Auto/Search id linkage per repo evidence.

Minimal-only export MUST NOT claim detailed field-level advertising settings
coverage. Detailed export MUST NOT treat this dataset as a **detailed** snapshot
without the dedicated domain contract, provenance, and leg model from change
`ai-package-campaign-settings-snapshot`.

Inclusion requires a proven read-only PG seam (`get_async_session_maker(read_only=True)`,
shop-scoped SELECT only, no WB writes, no `WBShopDataManager` orchestrator).
When the seam is not defensible at apply time, export MUST emit dataset-level
`UNKNOWN` or omit with explicit `reason_codes`, not fabricated inventory or
detailed settings rows. When included with partial discovery, `coverage` MUST
reflect **PARTIAL** inventory or **PARTIAL** detailed settings — not FULL WB
cabinet campaign universe.

#### Scenario: PG inventory is read-only minimal grain

- **GIVEN** PG inventory dataset is enabled per design
- **WHEN** export reads PG for shop S
- **THEN** only SELECT/read-only session patterns MUST be used
- **AND** `bot_active`, mode defaults, or WB write side effects MUST NOT occur
- **AND** rows MUST represent shop-scoped inventory/relations (not full
  detailed settings field export unless detailed snapshot change is applied)

#### Scenario: Detailed settings not implied by inventory card

- **GIVEN** v1 export for shop S without detailed snapshot implementation
- **WHEN** manifest describes `campaign_settings_snapshot`
- **THEN** export MUST NOT claim complete detailed advertising settings coverage
- **AND** absence of detailed settings MUST NOT be masked as FULL settings snapshot

#### Scenario: Detailed settings export uses dedicated contract when applied

- **GIVEN** change `ai-package-campaign-settings-snapshot` is implemented
- **WHEN** export materializes `campaign_settings_snapshot` for shop S
- **THEN** payload MUST conform to `CampaignSettingsSnapshotV1`
- **AND** manifest card MUST declare detailed settings export semantics
- **AND** Auto and Search legs MUST remain distinguishable in payload
- **AND** export MUST NOT serialize control-plane `CampaignResourceSnapshotV1` as the payload
