## 0. Ворота реализации

- [x] 0.1 Не писать продуктовый код, миграции и не включать endpoint, пока нет отдельного GO на реализацию и пока proposed decisions этого change не приняты
- [x] 0.2 Потреблять scenario plan `SCPV1-caabac3b666cb5d4` (`PLAN_STATUS: ready`). Не объявлять тесты пройденными до их написания

## 1. Тесты доступа и OAuth

- [x] 1.1 Тест: authorize с PKCE S256 создаёт Redis-транзакцию и отдаёт только deep link существующего бота, без формы пароля
- [x] 1.2 Тест: отказ без S256, с чужим scope, неточным redirect_uri и неизвестным client не создаёт транзакцию
- [x] 1.3 Тест: payload, билет возврата и код авторизации не принимаются как bearer MCP
- [x] 1.4 Тест: открытие `/start` с payload не подтверждает сессию; подтверждение пишет `User.id`, а не telegram id
- [x] 1.5 Тест: complete редиректит на сохранённый адрес с исходным state и сгорает со второго раза
- [x] 1.6 Тест: обмен кода требует верный PKCE verifier; повтор кода отвергается
- [x] 1.7 Тест: отключение поднимает authorization_version и гасит refresh; уже отозванная строка отвергает старый токен без нового события
- [x] 1.8 Тест: недоступные Redis на authorize и PostgreSQL на чтении дают отказ и не отдают магазин

## 2. Тесты чтения

- [x] 2.1 Тест: список инструментов равен профилю, списку магазинов, возможностям и AI-пакету; иное имя не доходит до записи WB
- [x] 2.2 Тест: профиль не содержит токен бота, токен WB, пароль и telegram id
- [x] 2.3 Тест: список магазинов берёт только текущие `WBUserCabinet` принципала, пустой список успешен
- [x] 2.4 Парный тест: свой shop_id допускается, чужой и уже снятый дают `SHOP_NOT_GRANTED` и не вызывают сбор пакета
- [x] 2.5 Тест: возможности явно помечают запись и ChangeSet неподдерживаемыми и отказывают без права на магазин
- [x] 2.6 Тест: AI-пакет вызывает `ExportService.export`, сохраняет GAP, PARTIAL и UNKNOWN и не объявляет опущенные байты полным вложением
- [x] 2.7 Тест: один магазин в пакете; файл больше предела отдаёт хеш и размер без байт

## 3. Реализация после ворот

- [x] 3.1 Добавить таблицы подключения и хеша refresh вперёд-только миграцией, не копируя список магазинов
- [x] 3.2 Добавить протокольные маршруты OAuth, metadata и `/mcp` на существующий FastAPI бота
- [x] 3.3 Добавить в боте подтверждение, список подключений и отключение, не меняя обычный `/start` без префикса `mcp_`
- [x] 3.4 Подключить presenter AI-пакета к существующему экспортёру и белому списку полей

## Telegram UI / Message Safety

- [x] 4.1 Покрыть тексты подтверждения, возврата и отключения лимитами из `openspec/policies/telegram_bot_api_limits.md` на худших динамических данных
- [x] 4.2 Проверить `callback_data` в байтах UTF-8 и что пользователю не уходит сырой токен транзакции целиком в обычном тексте ошибки

```text
TASK_GENERATION_READINESS

UNRESOLVED_DESIGN_CHOICES: none
UNRESOLVED_PRODUCT_CHOICES: none
UPSTREAM_NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
SCENARIO_REQUIREMENTS_CONSUMED: yes
SCENARIO_PLAN_EVIDENCE_ID: SCPV1-caabac3b666cb5d4
SCENARIO_PLAN_STATUS: ready
SCENARIO_PLAN_FRESHNESS: current
TASKS_STATUS: READY
REASON: none
```
