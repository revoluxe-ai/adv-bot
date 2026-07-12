## ADDED Requirements

### Requirement: Paid activation enables minus-phrases automation
The system SHALL enable automatic minus-phrases updates when a campaign is explicitly switched into paid bot management through the paid mode defaults.

#### Scenario: Paid bot management is enabled
- **GIVEN** a campaign is not currently in paid bot management
- **WHEN** the user enables paid bot management for that campaign
- **THEN** the campaign has paid bot management enabled
- **AND** automatic minus-phrases updates are enabled for that campaign

### Requirement: Free mode disables automatic minus-phrases automation
The system SHALL disable automatic minus-phrases updates when a campaign is switched into free or manual mode.

#### Scenario: Paid bot management is disabled
- **GIVEN** a campaign has automatic minus-phrases updates enabled
- **WHEN** the user disables paid bot management for that campaign
- **THEN** the campaign is not in paid bot management
- **AND** automatic minus-phrases updates are disabled for that campaign

### Requirement: Free mode does not execute automatic minus-phrases writes
The system MUST NOT execute automatic minus-phrases update writes for campaigns that are not in paid bot management, even if the minus-phrases automation flag is enabled.

#### Scenario: Legacy or manual flag remains enabled outside paid mode
- **GIVEN** a campaign has automatic minus-phrases updates enabled
- **AND** the campaign is not in paid bot management
- **WHEN** the automatic minus-phrases update process runs
- **THEN** the campaign is skipped for minus-phrases write updates
