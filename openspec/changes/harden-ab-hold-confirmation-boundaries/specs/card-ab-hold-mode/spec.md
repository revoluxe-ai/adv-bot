## ADDED Requirements

### Requirement: Confirmation and disable actions require current campaign ownership
Before accepting any A/B Hold confirmation or disable action, the system MUST
verify that the current Telegram user is associated with the campaign's cabinet
through the existing campaign ownership relation. A user who is not associated
with the campaign MUST receive a neutral rejection and the action MUST NOT
change campaign state, clear confirmation or coordination state, or cause a
lifecycle transition. The rejection MUST NOT disclose the state of the other
user's campaign.

#### Scenario: Associated user may continue confirmation
- **GIVEN** the current Telegram user is associated with the campaign's cabinet
- **AND** the confirmation context is otherwise current and valid
- **WHEN** the user confirms an A/B Hold parameter
- **THEN** the confirmation proceeds through the existing A/B Hold flow
- **AND** the existing explicit-confirmation requirement remains in force

#### Scenario: Foreign confirmation is rejected without side effects
- **GIVEN** the current Telegram user is not associated with the campaign's cabinet
- **WHEN** the user submits a confirmation action for that campaign
- **THEN** the action is rejected with a neutral message
- **AND** the campaign state is not changed
- **AND** no confirmation state, coordination state, or lifecycle state is cleared or advanced

#### Scenario: Foreign disable is rejected without side effects
- **GIVEN** the current Telegram user is not associated with the campaign's cabinet
- **WHEN** the user submits an A/B Hold disable action for that campaign
- **THEN** the action is rejected with a neutral message
- **AND** the campaign is not disabled
- **AND** no database write, coordination cleanup, or lifecycle transition is performed

## MODIFIED Requirements

### Requirement: After WARM_UP the system displays factual position and proposed target place as separate fields
Once WARM_UP completes, the system MUST evaluate every keyword in the current
confirmed keyword set. A keyword with a finite factual current position greater
than zero MUST be included in the confirmable set, and the system MUST display
its factual current position and, separately, a proposed target place computed
from that factual position. Factual position and target place are separate
semantic fields and MUST be displayed and tracked separately, even where their
numeric values coincide after rounding or clamping. A keyword with a missing,
zero, negative, or otherwise non-positive factual position MUST be excluded
from the confirmable set, MUST be shown to the user with the exclusion reason,
and MUST NOT be converted into factual position `0` or proposed target place
`0`.

#### Scenario: Post-warm-up display shows valid factual position and proposed target place separately
- **GIVEN** WARM_UP has completed for a campaign's confirmed keyword set
- **AND** a keyword has a finite factual current position greater than zero
- **WHEN** the user views the post-warm-up confirmation screen
- **THEN** the keyword's factual current position is shown
- **AND** a proposed target place computed from that factual position is shown as a separate field
- **AND** the keyword remains in the confirmable set

#### Scenario: Missing factual position excludes a keyword
- **GIVEN** WARM_UP has completed for a campaign's confirmed keyword set
- **AND** a keyword has no factual current position
- **WHEN** the user views the post-warm-up confirmation screen
- **THEN** the keyword is shown as excluded with a reason that its factual position is unavailable
- **AND** the keyword is not in the confirmable set
- **AND** no factual position `0` or proposed target place `0` is created for that keyword

#### Scenario: Non-positive factual position excludes a keyword
- **GIVEN** WARM_UP has completed for a campaign's confirmed keyword set
- **AND** a keyword has a factual current position less than or equal to zero
- **WHEN** the user views the post-warm-up confirmation screen
- **THEN** the keyword is shown as excluded with a reason that its factual position is invalid
- **AND** the keyword is not in the confirmable set
- **AND** no target place is proposed or saved for that keyword

#### Scenario: Numeric coincidence does not merge the fields
- **GIVEN** a keyword has a finite factual position greater than zero
- **AND** its factual position and proposed target place happen to be numerically equal after rounding or clamping
- **WHEN** the post-warm-up screen displays the keyword
- **THEN** factual position and target place are still presented as two distinct fields

### Requirement: Target place requires explicit confirmation and becomes immutable for the epoch
Fixing target places as confirmed epoch parameters MUST require an explicit user
confirmation of the proposed target places shown after WARM_UP. The
confirmation MUST include only the remaining keywords with finite factual
positions greater than zero. Keywords excluded because their factual position is
missing or non-positive MUST NOT be included in the confirmed keyword set and
MUST NOT receive a saved target place. If no valid keywords remain after
exclusion, the system MUST NOT continue confirmation or save any target place.
Once confirmed, each target place MUST become durable and MUST remain immutable
for the current epoch: neither a later setup tick nor an activation retry MUST
recalculate it. Ordinary drift of a keyword's factual position after
confirmation MUST NOT reopen confirmation or trigger recalculation of the
confirmed target place for that epoch. Changing confirmed target places is
possible only by starting a new epoch through the existing full confirmation
sequence.

#### Scenario: User confirms only the remaining valid target places
- **GIVEN** the post-warm-up screen contains both valid and excluded keywords
- **AND** the valid keywords have finite factual positions greater than zero
- **WHEN** the associated user explicitly confirms the proposed target places
- **THEN** only the valid keywords receive durable confirmed target places
- **AND** excluded keywords do not receive a target place
- **AND** the existing subsequent A/B Hold flow continues for the confirmed valid set

#### Scenario: Empty valid set cannot be confirmed
- **GIVEN** all keywords in the current confirmation set have missing or non-positive factual positions
- **WHEN** the user attempts to confirm target places
- **THEN** confirmation does not continue
- **AND** no target place is saved
- **AND** the user sees that no valid keywords remain and why

#### Scenario: Confirmed target place is not recalculated on a later setup tick or retry
- **GIVEN** a keyword has a confirmed target place for the current epoch
- **WHEN** a later A/B Hold setup tick or an activation retry runs for that epoch
- **THEN** the confirmed target place is not recalculated or overwritten

#### Scenario: Ordinary position drift after confirmation does not reopen confirmation
- **GIVEN** a keyword has a confirmed target place for the current epoch
- **AND** the keyword's factual position later drifts away from that confirmed target place
- **WHEN** the system observes the drifted factual position
- **THEN** the confirmation is not reopened
- **AND** the confirmed target place for that epoch is not recalculated

### Requirement: Existing A/B Hold lifecycle boundaries remain unchanged by confirmation hardening
The confirmation hardening MUST preserve the existing A/B Hold lifecycle,
durable state, and mutable-state boundaries. The confirmed keyword set,
positive confirmed target places, Auto participation, and Auto bid retain their
existing confirmation and hold semantics. Whitelist, blacklist/minus phrases,
keyword status/enable, bids, budgets, setup/hold writes, external Wildberries
writes, and PostgreSQL/Redis coordination retain their existing allowed,
frozen, restored/enforced, or out-of-scope status. This change MUST NOT add a
new ownership model, durable ACL, callback user identity, migration, or
lifecycle.

#### Scenario: Valid confirmation preserves the existing lifecycle
- **GIVEN** an associated user confirms a non-empty valid set of positive target places
- **WHEN** the existing A/B Hold confirmation flow continues
- **THEN** WARM_UP, generation, durable confirmation, PG/Redis coordination, and subsequent lifecycle transitions retain their existing semantics
- **AND** no new epoch is created solely by the ownership or position checks

#### Scenario: Hardening does not authorize unrelated writes
- **GIVEN** a campaign is in A/B Hold confirmation or hold
- **WHEN** the confirmation hardening checks are evaluated
- **THEN** they do not enable unrelated whitelist, blacklist/minus-phrase, keyword-status, bid, budget, or ordinary updater writes
- **AND** external Wildberries writes remain governed by the existing A/B Hold lifecycle and confirmed parameters
