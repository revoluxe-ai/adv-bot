# OPSX command-only — Project + architect contract

**Дата:** 2026-10-06  
**Authority:** Owner preference + [adv-bot canonical workflow](/cursor/stores/self/docs/adv-bot-canonical-development-workflow.md)

## Правило

Любая **product** работа в adv-bot выполняется только через **одну активную slash-команду** (`PRIMARY_COMMAND`) из `.cursor/commands/opsx-*.md` на ход.

- Промпт вида `MODE:`, `TASK:`, `RUN CANONICAL …` **без** первой строки `/opsx-…` = **не исполнение**, только планирование до перевода в команду.
- Прямой `pytest` / `ruff` / `git commit` / правка `app/**` без предшествующего `/opsx-apply`, `/opsx-test`, `/opsx-verify` и т.д. = **обход OPSX**.
- Если нужной команды нет → **STOP** (`MISSING_OPSX_COMMAND`), фиксируем gap в meta-process (tiriel-game / OPSX spine), **не** «делаем так же руками».

## Роли

| Роль | Может | Не может |
|------|--------|----------|
| **Web architect** | Приоритет, ADR, owner-contract текстом, «какой change» | Раздавать implementation/verify промпты без `/opsx-*`; дублировать штаб |
| **Project coordinator (штаб)** | GO, приоритет, перевод architect intent → **одна** `/opsx-*` строка + change + HEAD; отклонять обход | Сам править product code; принимать prose-TASK как GO на код |
| **Feature chat** | Исполнять **только** PRIMARY_COMMAND; subagents в рамках той же команды | Смешивать несколько `/opsx-*` в одном ходе; имплементация по «OWNER GO bounded repair» без `/opsx-apply` или явного repair-команды из pipeline |

## Обязательный формат hop в feature-chat

Первая исполняемая строка сообщения:

```text
/opsx-<command> <args из контракта команды>
change=<change-id>
```

Далее только контекст, разрешённый **этой** командой (HEAD, read-only, GO scope). Блоки `MODE: implementation` без slash — **запрещены** для исполнения.

## Coordinator: отклонение architect bypass

При получении architect handoff с prose-TASK координатор:

1. Не пересылает текст как есть в worker.
2. Маппит intent → каноническая команда (таблица ниже).
3. Если маппинга нет → ответ Owner: `MISSING_OPSX_COMMAND: <intent>`.

| Intent (architect prose) | Команда |
|--------------------------|---------|
| Implement feature | `/opsx-apply change=<id>` |
| Planning only | `/opsx-continue change=<id>` или `/opsx-update change=<id>` |
| Unit/integration tests | `/opsx-test change=<id> …` |
| Scenario certify | `/opsx-spec-scenario-coverage mode=certify change=<id>` |
| Scenario audit | `/opsx-spec-scenario-coverage mode=audit change=<id>` |
| DoD verify | `/opsx-verify mode=impl change=<id>` |
| Archive | `/opsx-verify mode=archive change=<id>` |
| PG provider gap tests | `/opsx-test` + `SCENARIO_TEST_ONLY_PACKET` |
| Live provider certify | `/opsx-close-external-gap` / certify packet (не ad-hoc pytest) |
| Pyright coverage gate | `/opsx-pyright-strict-coverage change=<id> base=…` |
| Bounded style repair | Только если pipeline связывает с `/opsx-apply` или отдельной repair-командой; иначе meta |

## Чаты

- **Authority** для change = один feature agent (`bc-…`) + ветка PR.
- Historical / duplicate chat (например `381fb1d2` telegram) — **не** источник команд.
