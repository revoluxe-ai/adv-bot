# Decision: WB Sky MCP OAuth bridge through Telegram

## Status

Proposed

## Context

Нужен стандартый OAuth 2.1 для удалённого MCP и человеческое согласие без
нового сайта логина. Репозиторий уже связывает личность так:

- `User.user_telegram_id` уникален и является ключом поиска человека в боте
- `User.id` — внутренний принципал
- `WBUserCabinet` связывает `user_id` с `WBCabinet`
- `WBCabinet.shop_id` — идентификатор магазина для экспорта
- `create_user` / message `/start` создают User
- `email` и `password_hash` есть у User, но маршрутов логина и IdP нет
- Redis уже используется для коротких ключей
- Криптографии OAuth нет; есть `secrets.token_urlsafe` и SHA-256
- `/start` не читает payload глубокой ссылки

Внешний IdP не подключён. Отдельный логин-сайт запрещён решением Owner.

## Decision

1. WB Sky сам реализует OAuth Authorization Server для этого клиента.
   Auth0, Keycloak и иной внешний IdP MUST NOT добавляться.
2. Человеческий UI согласия — существующий клиентский бот. HTTP-маршруты
   OAuth — только протокол и технический редирект.
3. Субъект access token — `User.id`. Telegram user id MUST NOT быть bearer
   и MUST NOT быть `sub`.
4. Права на магазины MUST читаться на каждом вызове из текущих
   `WBUserCabinet` → `WBCabinet`. Отдельная копия списка магазинов в токене
   MUST NOT быть источником прав.
5. Незавершённая OAuth-транзакция, билет возврата и код авторизации живут
   в Redis с TTL и одноразовым снятием. Подключение ChatGPT и хеш refresh
   живут в PostgreSQL, чтобы отключение пережило очистку Redis и сразу
   поднимало `authorization_version`.
6. Недоступность Redis на пути авторизации или PostgreSQL на пути
   принципала, версии или кабинетов MUST быть отказом.

## Applies to

- OAuth-мост MCP WB Sky
- Подключение и отключение ChatGPT в клиентском боте
- Проверка shop grant на read tools

## Allowed

- Протокольные маршруты authorize, token, complete и metadata на том же
  FastAPI, что и webhook
- Глубокая ссылка в существующего бота с одноразовым payload
- Подтверждение, список подключений и отключение в боте
- Поиск принципала по `User.user_telegram_id` и создание User тем же
  `create_user`, что и `/start`, до явного подтверждения

## Forbidden

- Сайт логина, форма пароля, новый IdP
- Telegram bot token, webhook secret или user id как MCP bearer
- Постоянный shop list внутри access token как authority
- Выдача scope кроме `wbsky:read` этим change
- Fail-open, если Redis или PostgreSQL недоступны

## Examples

Хорошо: токен `sub` = `User.id`, scope чтения; инструмент сверяет shop_id с
живой связью кабинета.

Плохо: бот кладёт `user_telegram_id` в Authorization, или токен содержит
замороженный список shop_id и им верят после снятия кабинета.

## Related specs

- delta `openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md`

## Related changes

- `wb-sky-mcp-read-interface`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because OAuth/MCP identity placement отсутствует
- [x] implementation layer matches decision
