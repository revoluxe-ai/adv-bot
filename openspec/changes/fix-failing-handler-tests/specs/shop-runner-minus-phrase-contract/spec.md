## ADDED Requirements

### Requirement: Minus-phrase background sync targets only eligible campaigns
The system MUST consider a campaign eligible for minus-phrase background sync only when the campaign is active and has minus-phrase background sync enabled.

#### Scenario: Inactive or disabled campaigns are excluded
- **WHEN** the shop-runner prepares a minus-phrase background sync batch
- **THEN** campaigns with `bot_active = false` are excluded
- **AND THEN** campaigns with `auto_update_minus_phrases = false` are excluded
- **AND THEN** only campaigns that satisfy both conditions remain eligible

### Requirement: Minus-phrase updater is invoked only for eligible campaigns
The system MUST invoke the minus-phrase updater only for campaigns that satisfy the eligibility rule for background sync.

#### Scenario: Only eligible campaigns are processed
- **WHEN** a minus-phrase background sync run is executed
- **THEN** the updater is called for each eligible campaign
- **AND THEN** campaigns that do not satisfy the eligibility rule are not passed to the updater

### Requirement: No eligible campaigns results in no updater work
The system MUST avoid updater execution when there are no eligible campaigns for minus-phrase background sync.

#### Scenario: Empty eligible set short-circuits the run
- **WHEN** no campaigns satisfy the minus-phrase eligibility rule
- **THEN** the system completes the background sync run without invoking any minus-phrase update work
