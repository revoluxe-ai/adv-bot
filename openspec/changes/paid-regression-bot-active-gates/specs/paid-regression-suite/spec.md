## ADDED Requirements

### Requirement: Paid regression suite exists as blocking gate

The project SHALL provide an automated test suite marked `paid_regression` that MUST pass before merging changes that affect free tier, shop-runner, billing, or client bot automation.

#### Scenario: Developer runs paid regression before free PR

- **WHEN** a developer runs the documented paid regression command
- **THEN** the command executes only tests marked `paid_regression` and reports pass or fail for paid tier contracts

#### Scenario: Paid regression fails on paid behavior regression

- **WHEN** a change breaks paid automation behavior for campaigns with bot active enabled
- **THEN** at least one test in the paid regression suite fails

### Requirement: Bot activation requires balance check

When a user enables the bot on a campaign (paid path), the system MUST verify cabinet balance covers the daily tariff before setting bot active to enabled.

#### Scenario: Insufficient balance blocks activation

- **WHEN** user requests bot activation for a campaign
- **AND** cabinet balance plus bonus is below the required daily price
- **THEN** bot active remains disabled
- **AND** user receives an insufficient funds message

#### Scenario: Sufficient balance enables activation

- **WHEN** user requests bot activation for a campaign
- **AND** cabinet balance plus bonus covers the required daily price
- **THEN** bot active is set to enabled for that campaign

### Requirement: Billing charges only bot-active campaigns

Daily billing MUST include only campaigns where bot active is enabled for tariff calculation and charging.

#### Scenario: Inactive campaign excluded from tariff count

- **WHEN** billing calculates price for a shop
- **AND** some campaigns have bot active disabled
- **THEN** only bot-active campaigns are counted toward the daily tariff

### Requirement: Paid automation coroutines run for bot-active campaigns

When bot active is enabled and relevant automation flags are on, shop-runner ACT coroutines MUST invoke their WB mutation paths (subject to other guards such as stats freshness).

#### Scenario: Common search bid updates when paid and configured

- **WHEN** bot active is enabled
- **AND** common bid update in search campaign is configured and allowed
- **THEN** the common search bid update path executes

#### Scenario: Cluster bids update when paid and bidder active

- **WHEN** bot active is enabled
- **AND** bidder is active for the campaign
- **THEN** cluster bid update path executes for that campaign

### Requirement: Curated existing tests documented

The paid regression documentation MUST list existing test modules that supplement the dedicated paid regression folder for billing, balance, and shop menu tariff display.

#### Scenario: Curated list is discoverable

- **WHEN** a developer reads paid regression documentation
- **THEN** they find a list of additional existing test paths recommended for paid safety checks
