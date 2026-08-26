## Why

Нужно выровнять продукт и specs: free-бот после entry-gates, без dual
presentation-only onboarding; invite опционален; channel subscription
обязателен и fail-closed.

## What Changes

- Зафиксировать контракт free-client-entry (delta + README/design).
- Синхронизировать living `callback-start-menu-return` (без minimal
  presentation route).
- Runtime: `presentation_only` default false; `use_minimal_presentation_ui`
  всегда False; GateMiddleware без presentation fork; `/start` в whitelist.

## Capabilities

### New Capabilities

- `free-client-entry`: вход в полный free MainMenu после invite/channel.

### Modified Capabilities

- `callback-start-menu-return` (main): убран presentation-only minimal
  scenario; добавлен invite-off → full free menu.

## Scope

### In Scope

- entry UX / gate / start routing и согласованные specs/tests.

### Out of Scope

- billing/paid automation redesign;
- отключение channel subscription;
- migration/landing process (`land-free-bot-rebase-into-stage`).
