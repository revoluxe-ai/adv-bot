## Why

Нужен повторяемый Owner-local способ безопасно читать WB API для выбранного
магазина, **собрать что реально доступно** по четырём семьям данных и сдать
research-архив на локаль через `/opsx-scripts` Job — без local Cursor→prod API
и без нового HTTP-стека. Сейчас такого entrypoint нет.

## Evolution Context

```text
STAR_ID: wb-safe-readonly-collect
STAR_TITLE: Безопасный постоянный сбор WB API-данных
INCREMENT_ID: INC-RO-01
CURRENT_INCREMENT: best-effort 4-family collect + gap report + Owner-local archive (secret-strip only) via /opsx-scripts; optional smallest preflight mode
CONTRIBUTION_TO_NORTH_STAR: повторяемый proof безопасного API-чтения + реального research-dump из Owner-bot Job
FORWARD_COMPATIBILITY_CONSTRAINTS:
- не вводить новый raw HTTP-клиент WB; только existing access + wb/api managers/adapters
- ретраи/лимиты — reuse production WB API patterns (shop-runner path), finite budget, no hang
- 4 endpoint aliases расширяемы до будущего Web CLEAN_DUMP / L2 package (не DoD)
- generated/.../vN/swagger остаётся будущим SoT для API Master
- policy: READ_ONLY_NO_MUTATION (не литерал HTTP GET_ONLY)
- API только из Owner-bot Job runtime; Cursor — plan/run/cp
- archive L0: payload+report locally; secret-strip only (не Web-sanitized RETURN)
OUT_OF_SCOPE (owed) — parked in WORKLOG / Future Increments:
- Web-sanitized RETURN / L2 package mode
- quarantine→transfer pipeline
- Web CLEAN_DUMP / Stage B contract + READ_ONLY_PREFLIGHT_PASS accept gate
- swagger status/sync (INC-RO-02; gap-triggered)
- API Master (INC-RO-03)
- read-only token hardening (INC-RO-05)
- finance/write; PROCESSOR/RHP
```

Future Increments / WORKLOG parks — только context, не DoD этого change.

## What Changes

### Intent

Один scripts-entrypoint + `/opsx-scripts` Job: по `shop_id` режимы
`preflight` (smallest probe) и `collect` (best-effort pull), отчёт по 4 семьям
(OK / PARTIAL / gap), Owner-local zip (payload + report, secret-strip).

### Current behavior

- Есть WB API clients/adapters и access по `shop_id` в Owner-bot runtime.
- Есть Job-инфра `/opsx-scripts`.
- Нет постоянного entrypoint для research collect/preflight с архивом на локаль.

### Desired behavior

- CLI: обязательный `--shop-id`; `--mode preflight|collect`.
- `preflight` — smallest read-only probe по 4 aliases.
- `collect` — best-effort read-only сбор по тем же 4 семьям в пределах bounded
  budget; PARTIAL с gap-логом допустим; MUST NOT silent «полный успех» при дырах.
- Reuse shop-runner WB API retry/rate-limit/timeout; finite ceiling на весь run.
- Архив L0: research payload + report (+ sha256); MUST strip token /
  Authorization / cookies из outputs/logs; Web-grade redaction тел/ID — не DoD.
- `/opsx-scripts RUN` копирует архив; отчёт с абсолютным локальным путём.
- «Дилера» только через arg `shop_id`.
- MUST NOT объявлять Web `READ_ONLY_PREFLIGHT_PASS`.

### Scope in

- Scripts entrypoint + Job + known outputs
- Modes preflight + best-effort collect
- 4 families via existing stack; POST-read ok; honest gaps
- Bounded retries + run ceiling
- L0 archive (secret-strip)
- Registry update after successful RUN (не `battle_tested` из RUN)

### Scope out

- Web L2 sanitize / quarantine→transfer / CLEAN_DUMP Web contract / accept gate
- Swagger sync / API Master / read-only token hardening
- Finance и mutation write
- Новый HTTP-клиент; local Cursor→prod API

### Risk

- Неполный mapping → PARTIAL/gap, не invent URL.
- Секреты в архиве → secret-strip MUST; не класть token в логи.
- Путаница с Web RETURN → явно Owner-local research dump, не Web PASS.
- Hang → production retries + run ceiling.

### Rollback idea

Удалить Job / не использовать entrypoint; откатить строку registry.
Product `app/**` по умолчанию не менять (только reuse).

## Capabilities

### New Capabilities

- `wb-api-read-only-preflight`: операторский read-only preflight/collect по
  `shop_id` через existing WB API stack (bounded retries), с Owner-local
  research-архивом (secret-strip) и запуском via `/opsx-scripts` Job.

### Modified Capabilities

- (нет)

## Impact

- Scripts capability для исследования; не меняет paid automation / Free-Paid.
- Зависит от Owner-bot tokens/DB, `wb/api`, shop-runner retry patterns.
- Gap endpoints → сигнал к Future swagger sync, не invent URL.
- Proposed decision: `decisions/scripts-wb-api-ops-stack/decision.md`.
