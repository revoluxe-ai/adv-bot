## Why

Callback Start сейчас одновременно ведёт себя как «вернуться в главное меню» (read-only PG session) и как регистрация (вызывает создание User). Это техдолг и расхождение с Owner-контрактом: callback — alias страницы меню для уже существующих пользователей; создание User MUST оставаться на message `/start` и связанных write-путях. Нужно закрыть несогласованность до того, как unit-тесты закрепят смешанное поведение как норму.

## What Changes

- Зафиксировать контракт: callback Start = возврат в меню / gate / presentation UI для существующего User; session mode остаётся pure-read.
- Убрать создание User с callback Start-path.
- Явно описать поведение при отсутствии User на callback (без записи): безопасный UI/early outcome без `create_user`.
- Обновить targeted tests под новый контракт (не characterization текущего бага).
- **Не** менять message `/start` registration write-path и gate middleware create-user.

### Scope in

- Поведение callback Start entry (меню / gate / minimal presentation) без PG write.
- Согласование unit/integration assertions с этим контрактом.

### Scope out

- Изменение логики `start_registration` (message `/start`).
- Рефактор gate middleware / phone / channel subscription.
- Унификация gate/admin/minimal в `show_shops_list` и соседних handlers.
- Новые onboarding UX / invite flow redesign.
- PG session maker / replica topology.

## Capabilities

### New Capabilities

- `callback-start-menu-return`: контракт возврата в стартовое меню через callback без создания User; pure-read session; регистрация User остаётся на отдельных write entry-points.

### Modified Capabilities

- (нет — в `openspec/specs/` нет существующего onboarding/start capability)

## Impact

- Client bot start-flow: callback Start больше не пишет User.
- Риск: редкий сценарий, когда пользователь попадает на Start-callback без записи User (минуя `/start` / middleware) — получит non-write outcome вместо скрытого create; это желаемое поведение по Owner-контракту.
- Rollback: вернуть create на callback path (нежелательно); предпочтительный rollback — revert change commit.
- Risk низкий: узкий UI entry, без WB writes и без paid automation.

## Current vs desired behavior

- **Current:** callback Start открывает `sm(read_only=True)` и при отсутствии User вызывает `create_user` (контракт create требует write session) — смесь «меню» и «регистрация».
- **Desired:** callback Start только читает и показывает меню/gate/minimal; User MUST уже существовать или путь MUST NOT создавать его; создание остаётся на message `/start` / write middleware.
