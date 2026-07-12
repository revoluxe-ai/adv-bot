## ADDED Requirements

### Requirement: Paid auto-management landing opens without toggling campaign state
The system MUST open the paid auto-management landing view for the selected campaign without changing the campaign's `bot_active` state.

#### Scenario: Open landing keeps campaign state unchanged
- **WHEN** the user opens the paid auto-management landing from the campaign menu
- **THEN** the system shows the landing view for the selected campaign
- **AND THEN** the campaign `bot_active` state remains unchanged

### Requirement: How-it-works view opens and returns to landing
The system MUST show the detailed paid auto-management explanation view and MUST allow returning back to the paid landing view for the same campaign.

#### Scenario: Open details and return to landing
- **WHEN** the user opens the "how it works" view for paid auto-management
- **THEN** the system shows the detailed explanation view for the selected campaign
- **WHEN** the user presses back from that view
- **THEN** the system returns to the paid landing view for the same campaign

### Requirement: Back navigation returns to campaign menu
The system MUST return from the paid auto-management landing view to the campaign menu without changing the campaign state.

#### Scenario: Back from landing returns to menu
- **WHEN** the user presses back on the paid auto-management landing view
- **THEN** the system shows the campaign menu for the same shop and campaign context
- **AND THEN** the campaign `bot_active` state remains unchanged

### Requirement: Missing campaign context fails safely
The system MUST fail with a runtime error when the paid auto-management landing or back navigation is requested for a missing campaign or missing cabinet context.

#### Scenario: Missing context raises an error
- **WHEN** the selected campaign or cabinet cannot be resolved for the paid auto-management navigation flow
- **THEN** the system raises a runtime error
- **AND THEN** the system does not attempt to render the target view
