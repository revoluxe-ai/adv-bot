## Purpose

Контракт Callback Start как menu-return entry: PURE_READ session, UI routing
для существующего User без создания записи; регистрация User остаётся на
message `/start` и других явных write entry-points.

После entry-gates (invite при включённом `invite_gate`, channel subscription,
phone где применимо) клиент получает полный free MainMenu. Legacy
`PRESENTATION_ONLY_MODE` / minimal presentation UI не является отдельным
маршрутом Callback Start.

## Requirements

### Requirement: Callback Start is menu-return without User creation
Callback Start entry MUST restore start menu or gate for an existing user
using a PURE_READ PG session. The callback path MUST NOT create a User record.
When the user is eligible for the client UI, the bot MUST show the full free
MainMenu (not a presentation-only minimal menu).

#### Scenario: Existing user with passed gate sees full main menu
- **WHEN** an existing user with `passed_gate=true` triggers the Start callback
- **THEN** the bot shows the full client MainMenu
- **AND** no User create/write is performed

#### Scenario: Existing gated user sees gate screen
- **WHEN** invite gate is enabled and an existing non-admin user with
  `passed_gate=false` triggers the Start callback
- **THEN** the bot shows the gate screen
- **AND** no User create/write is performed
- **AND** the bot MUST NOT show a presentation-only minimal MainMenu

#### Scenario: Invite gate off shows full free menu without passed_gate
- **WHEN** invite gate is disabled and an existing non-admin user with
  `passed_gate=false` triggers the Start callback
- **THEN** the bot shows the full client MainMenu
- **AND** no User create/write is performed

### Requirement: Missing user on Callback Start is non-write
If Callback Start cannot load a User, the path MUST NOT call User creation.
When invite gate is enabled, the path MUST show the gate screen; otherwise it
MUST return without MainMenu.

#### Scenario: Missing user with invite gate shows gate without create
- **WHEN** no User exists for the Telegram id and invite gate is enabled
- **AND** the Start callback is triggered with a message chat target
- **THEN** the bot shows the gate screen
- **AND** User creation MUST NOT run

#### Scenario: Missing user without invite gate returns without create
- **WHEN** no User exists for the Telegram id and invite gate is disabled
- **AND** the Start callback is triggered with a message chat target
- **THEN** the bot MUST NOT show full MainMenu as a registered client
- **AND** User creation MUST NOT run

### Requirement: Message start registration remains the write entry
Message `/start` registration MAY create a User on a write session. Callback
Start MUST NOT replace that write entry-point.

#### Scenario: Registration write stays on message start
- **WHEN** a new Telegram user needs a User row created
- **THEN** creation MUST happen on the message `/start` (or other explicit
  write entry), not on Callback Start
