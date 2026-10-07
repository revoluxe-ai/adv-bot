# telegram-ai-package-export

## ADDED Requirements

### Requirement: Shop menu exposes a distinct AI package button

Меню магазина MUST показывать кнопку `📦 Выгрузить AI-пакет` в FREE и PAID.
Callback MUST быть отдельным от Excel и MUST содержать только
`wb_user_cabinet_original_id`. Shop UUID, период, токены и секреты в
callback_data MUST NOT попадать. Длина callback_data MUST быть 1–64 байта UTF-8.

#### Scenario: Button packs the cabinet id

- **WHEN** строится главная клавиатура магазина для `WBUserCabinet.id`
- **THEN** кнопка `📦 Выгрузить AI-пакет` есть и в FREE, и в PAID
- **AND** её callback распаковывается в тот же id
- **AND** callback не равен Excel callback того же кабинета

### Requirement: Callback authorizes the current Telegram user

Handler MUST брать principal из `callback.from_user.id` и MUST проверять
владение через существующий `verify_user_owns_wb_user_cabinet`. При отказе
пользователь MUST увидеть `Нет доступа к этому магазину.` Handler MUST NOT
вызывать `PackageZipAssembler` и MUST NOT резолвить shop_id.

#### Scenario: Foreign user is denied

- **WHEN** callback приходит от пользователя без доступа к кабинету
- **THEN** ответ равен `Нет доступа к этому магазину.`
- **AND** assembler не вызывается

#### Scenario: Owner passes the ownership seam

- **WHEN** `verify_user_owns_wb_user_cabinet` успешен
- **THEN** handler продолжает resolve и export

### Requirement: Shop id is resolved server-side

После авторизации handler MUST прочитать `WBCabinet.shop_id` read-only
сессией по цепочке `WBUserCabinet.id` → `wb_cabinet` → `shop_id`. В assembler
MUST передаваться только этот shop id. Если mapping пустой или отсутствует,
пользователь MUST увидеть `Не удалось определить магазин для выгрузки.` и
assembler MUST NOT вызываться.

#### Scenario: Canonical shop id is passed through

- **WHEN** mapping возвращает shop id
- **THEN** `assemble_zip` получает этот shop id, а не id кабинета

#### Scenario: Broken mapping fails closed

- **WHEN** shop id не найден или пустой
- **THEN** пользователь видит `Не удалось определить магазин для выгрузки.`
- **AND** assembler не вызывается

### Requirement: V1 period uses ExportPeriod

Кнопка V1 MUST использовать период 2026-09-21..2026-10-04 включительно через
`ExportPeriod`. Выбор дат MUST жить в одной функции, чтобы позже заменить
окно без смены семантики exporter. UI выбора дат MUST NOT добавляться.

#### Scenario: Exact acceptance window

- **WHEN** handler строит период
- **THEN** это `ExportPeriod` со start 2026-09-21 и end 2026-10-04

### Requirement: Canonical assembler is the only export surface

Handler MUST получить ZIP только из `PackageZipAssembler.assemble_zip`.
Второй exporter, прямой запрос datasets, shell, локальный туннель и путь
машины пользователя MUST NOT использоваться. Возвращённые bytes MUST
отправляться документом с именем, которое заканчивается на `.zip` и содержит
санитизированный shop id и обе даты. Подпись MUST сообщать магазин, период и
успешную сборку и MUST укладываться в caption limit репозитория.

#### Scenario: Zip document is sent

- **WHEN** assembler возвращает bytes
- **THEN** бот вызывает `send_document` с этими bytes
- **AND** имя файла заканчивается на `.zip`
- **AND** перед сборкой отправлено `Формирую AI-пакет…`

### Requirement: Assembler and generic transport failures are redacted

The handler MUST keep assembler and non-size transport failures user-safe.
Исключение `assemble_zip` или отказ `send_document`, не связанный с размером,
MUST давать `Не удалось сформировать AI-пакет. Попробуйте позже.` Сырой
exception и секреты MUST NOT попадать пользователю.

#### Scenario: Assembler error is redacted

- **WHEN** `assemble_zip` выбрасывает исключение с секретом в тексте
- **THEN** пользователь видит только безопасную фразу отказа
- **AND** секрет и имя типа исключения отсутствуют в тексте

### Requirement: Telegram size rejection is explicit

Если Telegram отклоняет документ из-за размера, пользователь MUST получить
явную ошибку. ZIP MUST NOT урезаться и файлы пакета MUST NOT выкидываться.

#### Scenario: Size rejection is explicit

- **WHEN** `send_document` падает с TelegramBadRequest о слишком большом файле
- **THEN** пользователь получает явное сообщение про размер
- **AND** повторная отправка урезанного ZIP не выполняется

### Requirement: Export failure logs stay bounded

Логи MAY содержать telegram user id, `WBUserCabinet` id, shop_id и traceback.
Логи MUST NOT содержать WB token, bot token, credentials или сырые ZIP bytes.

#### Scenario: Logs omit secrets and raw zip bytes

- **WHEN** export завершается ошибкой assembler или transport
- **THEN** диагностические логи не содержат WB token, bot token, credentials
  или сырые ZIP bytes

### Requirement: Duplicate clicks do not double the export

The handler MUST NOT start a second export while the first one for the same user and cabinet is running.
Пока выгрузка для пары `telegram_user_id` + `wb_user_cabinet_id` идёт в этом
процессе, второй клик MUST NOT стартовать второй `assemble_zip` и MUST
ответить `Выгрузка для этого магазина уже формируется.`

#### Scenario: Second click waits outside the assembler

- **WHEN** первая сборка ещё не завершилась и приходит тот же callback
- **THEN** assembler вызывается один раз
- **AND** второй ответ содержит `Выгрузка для этого магазина уже формируется.`

### Requirement: Export path is read-only

Путь кнопки MUST NOT вызывать WB write adapter, запись настроек PostgreSQL
или запись ClickHouse. Сбой транспорта MUST NOT менять семантику пакета.

#### Scenario: Transport modules do not reference writers

- **WHEN** читаются исходники handler и flow
- **THEN** в них нет WBShopDataManager, ClickHouse client, ApplyManager,
  session.commit и локального script entry
