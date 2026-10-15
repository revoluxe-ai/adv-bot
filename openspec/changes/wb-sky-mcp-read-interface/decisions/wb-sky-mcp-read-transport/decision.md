# Decision: WB Sky MCP read transport

## Status

Accepted

## Owner acceptance

Accepted by Owner on 2026-10-06 in the implementation GO for change
`wb-sky-mcp-read-interface` (PR #452, branch
`cursor/wb-sky-mcp-read-interface-127c`).

Evidence: Owner marked `wb-sky-mcp-read-transport` ACCEPTED. Canonical read
semantics stay on the existing Full AI Package / `ExportService`. MCP V1
exposes only `get_profile`, `list_shops`, `get_capabilities`, and
`get_ai_package`. ChangeSet and write tools are out of this version. The
transport is Streamable HTTP on `/mcp` in the existing FastAPI process.
Oversized payloads are `OMITTED_OVER_BUDGET` rather than silently truncated.

## Context

Accepted `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` отдаёт
сбор Full AI Package модулю `app/modules/ai_package_v1/` и запрещает делать
Telegram или GUI точкой входа экспорта. Точка входа v1 — Job/CLI. Тот же
decision требует `READ_ONLY_NO_MUTATION` и запрещает второй экспортёр.

Accepted `openspec/decisions/shop-data-source-strategy/decision.md` держит
сбор данных и управление кампаниями разными контурами. MCP не должен стать
третьим контуром аналитики и не должен запускать сбор, чтобы «закрыть пробел».

В репозитории нет отдельного HTTP API продукта, кроме FastAPI процесса
клиентского бота (`client_bot_run.py`: webhook, `/health`, `/readiness`) и
постороннего error-collector. Отдельного микросервиса под чтение нет.

## Decision

1. MCP — транспортный адаптер. Семантика чтения MUST оставаться у Full AI
   Package / `ExportService`. Второй аналитический контракт MUST NOT
   появляться.
2. Разрешённая точка вызова экспорта для этого канала — read-adapter MCP,
   который вызывает существующий `ExportService.export` и существующий
   каталог GAP. ZIP-кодировщик не становится обязательным телом MCP.
3. Telegram-обработчики MUST NOT собирать пакет и MUST NOT быть экспортёром.
   Бот в этом канале только связывает личность и согласие.
4. Процесс размещения — тот же FastAPI, что уже обслуживает webhook бота.
   Новый микросервис MUST NOT создаваться для этого транспорта.
5. Путь MCP MUST оставаться `READ_ONLY_NO_MUTATION`: без WB API write, без
   запуска коллекторов и shop-runner, без ChangeSet.

## Applies to

- Read-only MCP WB Sky и любой будущий granular read tool того же канала
- Вызов AI Package из MCP

## Allowed

- Тонкий presenter: manifest, карточки, GAP-каталог, ограниченные байты уже
  собранных payload
- Монтирование маршрута `/mcp` на существующее FastAPI-приложение бота
- Явный отказ, если payload больше транспортного предела

## Forbidden

- Второй экспортёр или своя формула покрытия/GAP
- Сборка пакета внутри Telegram handler
- Возврат ZIP как обязательного контракта MCP
- Запись в WB, запуск сбора «чтобы заполнить GAP», ChangeSet apply
- Отдельный сервис только ради MCP

## Examples

Хорошо: инструмент AI-пакета вызывает `ExportService.export` и отдаёт те же
карточки, помечая крупный CSV как опущенный по размеру.

Плохо: бот по кнопке собирает ZIP, или MCP сам читает ClickHouse другим SQL.

## Related specs

- `openspec/specs/ai-package-v1-exporter/spec.md`
- `openspec/specs/ai-package-full-export/spec.md`
- delta `openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md`

## Related changes

- `wb-sky-mcp-read-interface`
- Accepted exporter ownership остаётся в силе для Job/CLI и запрета Telegram
  как экспортёра. Этот decision только добавляет MCP read-adapter как
  разрешённого вызывающего. Пока decision Proposed, реализация MUST NOT
  начинаться.

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision не разрешает MCP entry
- [x] implementation layer matches decision
