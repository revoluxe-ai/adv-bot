# Scenario Coverage Plan

CHANGE_ID: wb-sky-mcp-read-interface
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-caabac3b666cb5d4
LIFECYCLE_STATUS: DERIVED

Планирование требуемых доказательств. Тесты не объявлены существующими,
выполненными или пройденными. Это не PASS аудита и не GO архива.

## Lifecycle coverage

LIFECYCLE_COVERAGE:

- L1 → Authorize creates a one-time session; Authorize rejects weak or foreign requests
- L2 → Deep link is not an API credential
- L3 → Confirm binds the canonical principal; Opening the bot is not consent
- L4 → Return completes the original transaction
- L5 → Token exchange checks PKCE; Profile hides credentials
- L6 → Shop list follows current cabinets; Capabilities list only real read support; Package returns structured canonical content; One shop per package; Foreign shop id fails closed
- L7 → Disconnect invalidates tokens
- L8 → Removed shop disappears immediately; Already revoked connection stays denied
- инвариант записи → Write tool is not advertised; Mutation request is rejected
- отказ хранилища → Auth backend unavailable
- размер пакета → Oversized payload is omitted honestly
- возможности без права → Capabilities without a grant fail closed

gaps: []

Steady-state: сценарий «Already revoked connection stays denied» покрывает
уже отозванное подключение без нового события отключения. Сценарий
«Removed shop disappears immediately» покрывает уже снятую связь кабинета.

OPEN_QUESTIONS: нет
UNRESOLVED_GAPS: нет

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: wb-sky-mcp-read-interface
SOURCE_SPEC_SHA: 2aeccf0a2abb3f83512483b83847c9acb6e47473ce952536fb93520aa8577bbf
PLAN_STATUS: ready
SCENARIOS_TOTAL: 21

Общий production entry для чтения: MCP tool после проверки bearer.
Общий entry для согласия: OAuth authorize → бот → complete → token.
Тонкие концы: Redis, PostgreSQL кабинетов, ExportService, подпись JWT.
Проверяемое поведение (решение допуска, привязка принципала, отказ чужого
shop_id, прокидывание GAP) не мокается. Мок допустим только на краю сети WB
и Telegram Bot API. Экспортёр в сценарии пакета — реальный orchestration
с подмененными reader-краями, не подмена самого ExportService целиком.

SCENARIOS:

- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Write tool is not advertised
  REQUIRED_EVIDENCE: список инструментов равен четырём read tools
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Mutation request is rejected
  REQUIRED_EVIDENCE: неизвестное имя не доходит до WB write и до экспортёра
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Authorize creates a one-time session
  REQUIRED_EVIDENCE: Redis-транзакция 10 минут, ответ содержит только deep link бота
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Authorize rejects weak or foreign requests
  REQUIRED_EVIDENCE: нет записи транзакции при плохом PKCE, scope, redirect или client
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Deep link is not an API credential
  REQUIRED_EVIDENCE: txn id, ticket и code отвергнуты на /mcp
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Opening the bot is not consent
  REQUIRED_EVIDENCE: /start с payload не ставит статус confirmed
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Confirm binds the canonical principal
  REQUIRED_EVIDENCE: sub будущего токена равен User.id, не telegram id
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Return completes the original transaction
  REQUIRED_EVIDENCE: 302 только на сохранённый redirect_uri с исходным state; билет одноразовый
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Token exchange checks PKCE
  REQUIRED_EVIDENCE: верный verifier выдаёт токен; повтор кода отвергнут
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Profile hides credentials
  REQUIRED_EVIDENCE: белый список полей, нет bot token, WB token, password, telegram id
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Shop list follows current cabinets
  REQUIRED_EVIDENCE: только WBUserCabinet этого user_id; пустой список успешен
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Removed shop disappears immediately
  REQUIRED_EVIDENCE: после удаления связи тот же access token получает SHOP_NOT_GRANTED
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Foreign shop id fails closed
  REQUIRED_EVIDENCE: чужой shop_id не вызывает ExportService
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Disconnect invalidates tokens
  REQUIRED_EVIDENCE: version bump и отзыв refresh; следующий tool — UNAUTHENTICATED
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Already revoked connection stays denied
  REQUIRED_EVIDENCE: уже revoked строка без нового события отключения отвергает токен
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Capabilities list only real read support
  REQUIRED_EVIDENCE: запись и ChangeSet явно unsupported; список не шире четырёх tools
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Capabilities without a grant fail closed
  REQUIRED_EVIDENCE: нет grant — отказ, не пустой успешный capability
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Package returns structured canonical content
  REQUIRED_EVIDENCE: вызов ExportService.export; GAP/PARTIAL/UNKNOWN не переписаны
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Oversized payload is omitted honestly
  REQUIRED_EVIDENCE: sha256 и size сохранены, байты отсутствуют, статус не FULL inline
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::One shop per package
  REQUIRED_EVIDENCE: manifest shop совпадает с аргументом; ряды другого shop отсутствуют
- SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Auth backend unavailable
  REQUIRED_EVIDENCE: Redis down на authorize и PostgreSQL down на tool дают отказ без данных

BOUNDARY_INTEGRATION_WRITE: не требуется для WB. Для PostgreSQL подключения —
отдельный тест записи подключения и чтения версии. Для Redis — тест SET с TTL
и одноразового снятия.

MOCKING_CONSTRAINTS: не мокать решение shop grant и не мокать ExportService
целиком в сценарии пакета. Не подменять сравнение redirect_uri.

GENERATED_FROM:

- design.md 9bfbb9e796856ce915ed22af9b01ac8bc3d372813b107599ce7ab49891b4c6c7
- spec.md 2aeccf0a2abb3f83512483b83847c9acb6e47473ce952536fb93520aa8577bbf
- owner-contract.md 664a353651a56b9ae0c88907aa0ce7215bfb4e901d844cbd5ce68bec211faf9e
