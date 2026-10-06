## Context

Базовая линия: `origin/stage` `d2166b2d805b27a6656f46c6ccb8e56066b4e888`.

Сейчас человек входит в клиентский бот. Message `/start` ищет `User` по
`user_telegram_id` и при отсутствии вызывает `create_user`. Кабинеты связаны
через `WBUserCabinet` (`user_id`, `wb_cabinet_id`, уникальная пара) с
`WBCabinet.shop_id`. Экспорт читает этот `shop_id` как строку и собирает
`ExportResult` (manifest + payloads) в `ExportService.export`. ZIP — отдельный
транспорт `encode_package`, не доменная семантика. Покрытие и пробелы уже
выражены карточками (`FULL` / `PARTIAL` / `UNKNOWN`) и каталогом
`PACKAGE_FAMILY_GAPS` со статусом `GAP`.

HTTP продукта — FastAPI в `client_bot_run.py`: webhook Telegram, `/health`,
`/readiness`. Отдельного OAuth, session middleware и IdP нет. Колонки
`email` / `password_hash` миграции web-user не имеют маршрутов логина.
`CommandStart` не разбирает payload глубокой ссылки. Redis asyncio уже есть.
Готового bearer для пользователя нет. JWT в коде относится к токенам WB API,
не к сессии человека.

PR #449 (ChangeSet, не влит) и PR #450 (ремонт Full AI Package) этот change
не редактирует. Модуля `app/modules/wb_sky_control_plane` на этой базе нет.
Инструменты ChangeSet в MCP не входят.

## Goals / Non-Goals

**Goals:**

- Read-only MCP: профиль, список магазинов, возможности, AI-пакет.
- OAuth 2.1 Authorization Code + PKCE между ChatGPT и backend WB Sky.
- Согласие и отключение в существующем боте, без сайта логина.
- Права магазина динамически с живой связи кабинета.
- Тот же Full AI Package, ограниченный только транспортом.

**Non-Goals:**

- Сайт логина, внешний IdP, scope записи.
- `validate_changeset`, `dry_run_changeset`, `apply_changeset`, мутации WB,
  эксперименты, депозит, пауза, ставки, минус-фразы, размещения.
- Боевой endpoint, правка бота, миграции и код в этом планировании.
- Обязательный ZIP в ответе MCP.
- Гранулярные read tools. Они допустимы позже тем же адаптером, но не входят
  в первую версию.

## Architecture Decision References

- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` — экспорт
  только в `ai_package_v1`, `READ_ONLY_NO_MUTATION`, Telegram не экспортёр.
- `openspec/decisions/shop-data-source-strategy/decision.md` — сбор и
  управление кампаниями раздельны; MCP не запускает сбор.
- `openspec/decisions/clickhouse-sql-database-qualification/decision.md` —
  MCP не пишет свой ClickHouse SQL; читает через экспортёр.
- Accepted `decisions/wb-sky-mcp-read-transport/decision.md` — MCP adapter
  может звать `ExportService`, не становясь вторым экспортёром.
- Accepted `decisions/wb-sky-mcp-oauth-telegram-bridge/decision.md` —
  свой OAuth-мост, субъект `User.id`, магазины с живой связи.

Оба decision Accepted Owner GO 2026-10-06 (PR #452). Реализация этого
change идёт по тому GO: CIMD, resource indicator, `offline_access` как
технический refresh, точный `iss`, флаг `MCP_ENABLED` по умолчанию false.

Протокольный ремонт той же ветки не меняет границу чтения. Сервер заявляет
только MCP `2025-03-26` (`SUPPORTED_PROTOCOL_VERSIONS`). Метод token endpoint
выбирается пересечением CIMD с `{"none"}`; единственное поле клиента — лишь
предпочтение, если оно входит в пересечение. Ошибки authorize после
проверенных client/redirect уходят редиректом с `error`, `state` и точным
`iss`. До проверки redirect отказ локальный. Недействительный bearer на
`/mcp` — HTTP 401 и `WWW-Authenticate`, не успешный tool result.

## Ownership & Placement

| Зона | Владелец | Запрещено |
| --- | --- | --- |
| Семантика пакета | `ExportService` и домен `ai_package_v1` | MCP, Telegram handler, новый SQL |
| Транспорт MCP и presenter размера | новый read-adapter в том же приложении, маршрут `/mcp` на FastAPI бота | отдельный микросервис, error-collector |
| Протокол OAuth | те же процесс и приложение, маршруты `/oauth/*` и metadata | сайт логина, внешний IdP |
| Согласие человека | существующий клиентский бот | выдача bearer из Telegram |
| Принципал | `User.id` | `user_telegram_id` как `sub` |
| Права магазина | живые `WBUserCabinet` + `WBCabinet.shop_id` | список магазинов в токене |
| Незавершённый OAuth | Redis TTL + одноразовое снятие | PostgreSQL как единственное место короткой транзакции |
| Подключение и refresh | новые таблицы PostgreSQL у пользователя | Redis как единственная память отключения |
| Запись в WB | нет владельца в этом change | любой адаптер |

Размещение совпадает с proposed decisions: адаптер тонкий, семантика и
кабинеты остаются на своих слоях.

## Decisions

### Транспорт

Предпочтительный транспорт — Streamable HTTP на `POST /mcp`. SSE не
требуется доказательством репозитория и в первую версию не входит.
Аннотации всех четырёх инструментов: только чтение, не разрушают данные,
не ходят во внешний мир сами по себе.

Таймаут обычного инструмента — 30 секунд. AI-пакет — 60 секунд. Превышение
возвращает ошибку таймаута и MUST NOT выглядеть как успешный полный пакет.

### Что считается AI-пакетом в MCP

Выбрана комбинация, без второй семантики:

- Всегда структурированный конверт из результата `ExportService.export`:
  версия схемы, магазин, период, карточки датасетов, каталог GAP.
- Всегда дескрипторы файлов: логическое имя, dataset id, sha256, размер.
- Байты вкладываются, только если это текст или JSON, файл не больше
  256 КиБ и сумма вложений не больше 1 МиБ.
- Иначе байты опущены, дескриптор честно помечен `OMITTED_OVER_BUDGET`.
- Отдельный аргумент одного логического имени возвращает этот payload,
  если он не больше 2 МиБ. Иначе ошибка `PAYLOAD_TOO_LARGE` с хешем и
  размером, без байт.
- ZIP в инструмент не кладётся. Повторная сборка смысла не делается.

Период — включительные календарные даты, конец не раньше начала, длина не
больше 366 дней. Это предел транспорта от перегрузки, не новое правило
полноты пакета.

### OAuth и глубокая ссылка

Клиент ChatGPT — публичный: PKCE S256 обязателен, секрета клиента нет.
`redirect_uri` сравнивается точным совпадением с заранее зарегистрированным
списком. Scope запроса MUST быть ровно `wbsky:read`.

`GET /oauth/authorize` создаёт транзакцию в Redis на 10 минут:
`client_id`, `redirect_uri`, `state`, `code_challenge`, scope, статус
`pending`. Идентификатор транзакции — `secrets.token_urlsafe(32)`.
Ответ — не логин. Это минимальная страница с одной ссылкой
`https://t.me/wb_adv_master_bot?start=mcp_<txn>` либо эквивалентный
технический переход. Формы пароля нет. Префикс `mcp_` плюс идентификатор
укладывается в лимит payload Telegram 64 символа.

`/start` с таким payload MUST найти транзакцию и показать подтверждение.
Открытие ссылки — не согласие. Обычный `/start` без payload остаётся
прежним меню. Если User ещё нет, подтверждению предшествует тот же
`create_user`, что и у `/start`. Без явной кнопки подтверждения код не
выдаётся. Нет `from_user` или транзакция протухла — отказ, меню бота само
по себе доступ не открывает.

После подтверждения транзакция хранит `principal_id` = `User.id` и
одноразовый билет возврата на оставшийся TTL. Бот присылает ссылку
`/oauth/complete?ticket=`. Билет не принимается на `/mcp`.

`GET /oauth/complete` снимает билет один раз, выпускает код на 60 секунд и
отвечает 302 на сохранённый `redirect_uri` с `code` и исходным `state`.
Чужой адрес возврата не используется.

`POST /oauth/token` проверяет PKCE и выдаёт access token на 15 минут.
Refresh живёт 30 дней, хранится только как SHA-256, вращается при обмене.
Повтор отозванного refresh гасит всё подключение.

Metadata: protected resource и authorization server на том же хосте, чтобы
удалённый клиент нашёл authorize и token без ручной схемы в промпте.

### Токен и права

Claims access token: `iss`, `sub` (`User.id`), `aud` (этот MCP), `exp`,
`iat`, `scope` = `wbsky:read`, `authorization_version`, `jti`.
Магазинов в токене нет.

Каждый инструмент заново читает подключение. Версия в токене MUST совпасть
с живой строкой подключения. Затем shop-инструмент обязан найти
`WBUserCabinet` этого `user_id` с `WBCabinet.shop_id`, равным аргументу.
Нет строки, кабинет не найден, подключение отозвано — отказ.
`list_shops` без аргумента возвращает только свои текущие кабинеты:
`shop_id`, имя связи `WBUserCabinet.name`, признак `WBCabinet.active`.
Пустой список допустим.

Отключение в боте ставит `revoked_at`, увеличивает
`authorization_version` и гасит refresh. Пользователя и кабинеты это не
удаляет. Снятие кабинета само по себе убирает магазин со следующего вызова.

Ключ подписи — отдельный секрет процесса, не токен бота и не ключ WB.
Вращение: новый `kid` подписывает новые токены; старый проверяет не дольше
максимального TTL access token.

### Ошибки, лимиты, аудит

Структурная ошибка: код, короткое сообщение, `correlation_id`. Коды:
`UNAUTHENTICATED`, `FORBIDDEN_SCOPE`, `SHOP_NOT_GRANTED`,
`INVALID_ARGUMENT`, `PAYLOAD_TOO_LARGE`, `AUTH_BACKEND_UNAVAILABLE`,
`RATE_LIMITED`, `TIMEOUT`, `UNSUPPORTED`.

Лимиты, счётчики в Redis, при недоступности Redis — отказ:
авторизация 10 в час на клиент и IP; обмен токена 30 в час на принципала;
инструменты 60 в минуту на принципала; AI-пакет 6 в час на принципала и
магазин.

Аудит: correlation id, principal id, shop id если был, имя инструмента,
решение allow/deny, версия авторизации. В логах MUST NOT быть access token,
refresh, кода, билета, payload ссылки, токена WB и заголовка Authorization.

Данные магазина в ответе — недоверенное содержимое. Сервер MUST отдавать их
структурным JSON и MUST NOT класть туда инструкции модели. Секреты кабинета
в presenter не попадают: ответ собирается белым списком полей.

Редирект завершения ходит только на зарегистрированный `redirect_uri`.
Сервер не скачивает произвольный URL.

### Жизненный цикл

`LIFECYCLE_STATUS: DERIVED`

1. ChatGPT вызывает authorize с PKCE и scope чтения. SOURCE: owner-contract «протокол OAuth»; spec «Authorize creates a one-time session».
2. Сервер создаёт одноразовую сессию и отдаёт глубокую ссылку в существующего бота. SOURCE: owner-contract «согласие в Telegram-боте»; spec «Deep link is not an API credential».
3. Пользователь явно подтверждает. Сервер связывает сессию с `User.id`. SOURCE: owner-contract «Telegram-идентичность решает принципала»; spec «Confirm binds the canonical principal». Открытие без кнопки согласия не переходит дальше. SOURCE: spec «Opening the bot is not consent».
4. Бот даёт одноразовую ссылку возврата. Complete редиректит на исходный callback с кодом и state. SOURCE: owner-contract поток возврата; spec «Return completes the original transaction».
5. Обмен кода с PKCE выдаёт access token принципала. SOURCE: spec «Token exchange checks PKCE» и «Access token identifies the principal».
6. Инструменты чтения проверяют scope, версию подключения и текущие кабинеты. SOURCE: owner-contract «сервер каждый раз смотрит кабинеты»; spec профиля, списка, возможностей и пакета.
7. Отключение в боте сразу делает старый токен недействительным. SOURCE: owner-contract «отключение сразу закрывает доступ»; spec «Disconnect invalidates tokens».
8. Уже отсутствующая связь магазина или уже отозванное подключение при следующем чтении получает отказ без нового события. SOURCE: spec «Removed shop disappears immediately» и «Already revoked connection stays denied».

Недоступность Redis или PostgreSQL не создаёт обходной переход: отказ.
SOURCE: spec «Auth backend unavailable».

### Семантическая цель записи

```text
SEMANTIC_WRITE_TARGET_STATUS: NOT_APPLICABLE
```

Этот change не мутирует WB API, жизненный цикл кампании, биллинг и не
пишет ChangeSet. Конкурирующей ноги записи нет: запись запрещена.
Единственное новое состояние — OAuth-подключение. Его место уже выбрано:
короткая транзакция в Redis, подключение и refresh в PostgreSQL, права
магазина остаются в существующих кабинетах.

```text
PRODUCT_ACCEPTANCE_REQUIRED: true
```

Причина: у человека есть наблюдаемый цикл подключения и отключения ChatGPT.
Подтверждение цикла владельцем отдельно не требуется: шаги выведены из
owner-contract и spec без развилки.

### Устойчивое состояние

```text
WHAT is durable: подключение ChatGPT, хеш refresh, authorization_version
WHO owns canonical state: OAuth-мост владеет подключением; кабинеты остаются у существующих User/WBUserCabinet/WBCabinet; пакет остаётся у экспортёра
WHERE canonical state lives: PostgreSQL для подключения и кабинетов; Redis только для незавершённого OAuth и счётчиков
WHO may write it: протокол OAuth создаёт подключение после подтверждения в боте; отключение пишет бот; инструменты MCP не пишут кабинеты и не пишут WB
HOW it is read / recovered: access token проверяется подписью и версией в PostgreSQL; потеря Redis убивает только незавершённые транзакции; отключение переживает перезапуск
```

## Risks / Trade-offs

- [Тот же процесс, что webhook] → маршруты изолированы префиксами; падение экспорта не должно принимать webhook secret как токен MCP. Отдельный сервис не вводится, пока один процесс тянет нагрузку пакета.
- [Повторный export на один большой файл] → нет нового файлового хранилища; предел 2 МиБ и честный отказ вместо тихого ZIP.
- [PR #450 меняет состав пакета] → presenter не копирует схему, он вызывает текущий `ExportService` после вливания. До реализации состав не фиксируется вторым документом.
- [Payload `/start` уже занят онбордингом] → ветка только для префикса `mcp_`; прочий `/start` не меняет смысл.
- [Кража глубокой ссылки] → одноразовость, TTL 10 минут, привязка к client/redirect/state, ссылка не является bearer.
- [Инъекция через названия кампаний] → JSON-конверт и белый список, без системных инструкций в данных.

## Migration Plan

Реализация, когда будет отдельный GO: сначала таблицы подключения и refresh
вперёд-только миграцией, секрет подписи, регистрация redirect URI клиента,
затем маршруты и ветка бота. Откат — выключить маршруты флагом и отозвать
строки подключений. Этот план не выполняется в текущем change.

Боевой MCP не включается этим планированием.

## Open Questions

Нет. Имена кнопок бота — деталь реализации и на семантику не влияют.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision

```text
DESIGN_READINESS

PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none

DESIGN_STATUS: READY
REASON: none
```
