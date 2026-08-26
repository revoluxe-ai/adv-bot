## Purpose

Контракт входа в free-клиент UI: entry-gates, затем полный free MainMenu;
без dual presentation-only onboarding.

## Requirements

### Requirement: Free client UI after entry gates
После прохождения включённых entry-gates бот MUST показывать полный free
MainMenu. Paid automation MUST NOT быть единственным способом открыть
магазины / токен / ручные сценарии free-слоя.

#### Scenario: Passed invite and channel see full free menu
- **WHEN** invite gate is satisfied (or disabled) and channel subscription
  middleware allows the update
- **AND** the user triggers `/start` or an eligible menu-return entry
- **THEN** the bot shows full free MainMenu
- **AND** MUST NOT show presentation-only minimal MainMenu

### Requirement: Invite gate remains optional entry control
When `invite_gate` is enabled, users with `passed_gate=false` (non-admin)
MUST see the invite gate screen on `/start` / Callback Start instead of
full MainMenu. When `invite_gate` is disabled (default), `passed_gate`
MUST NOT block full free MainMenu, and partner-invite buttons MUST NOT
appear in MainMenu / shops list.

#### Scenario: Invite required blocks full menu
- **WHEN** `invite_gate` is true and user has `passed_gate=false` and is not
  admin
- **THEN** `/start` and Callback Start show the gate screen
- **AND** GateMiddleware allows `/start` through to the handler whitelist

#### Scenario: Invite disabled allows full free menu
- **WHEN** `invite_gate` is false (default when unset) and user has
  `passed_gate=false`
- **THEN** `/start` and Callback Start show full free MainMenu
- **AND** MainMenu / shops list MUST NOT show «Показать инвайт»
### Requirement: Channel subscription remains mandatory and fail-closed
Channel subscription middleware MUST remain an entry control independent of
presentation mode. Cache/API uncertainty MUST fail closed (block), not open.

#### Scenario: Unsubscribed user is blocked
- **WHEN** live Telegram membership check reports not subscribed
- **THEN** the update MUST NOT reach free MainMenu handlers

### Requirement: Presentation-only does not fork entry UX
`PRESENTATION_ONLY_MODE` MUST NOT switch GateMiddleware or `/start` /
Callback Start onto a separate minimal presentation menu path. Default MUST
be free-after-gates (`presentation_only` false when unset).

#### Scenario: Legacy flag does not unlock minimal dual path
- **WHEN** `PRESENTATION_ONLY_MODE=true` and invite gate blocks the user
- **THEN** the bot shows the invite gate screen (same as without the flag)
- **AND** MUST NOT show MainMenu with `full_client_ui=False` as the primary
  onboarding path
