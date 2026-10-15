# Стратегический бриф: ChatGPT share `6abd1faa`

**Источник:** partial raw capture (dehydrated RSC payload в HTML; DOM сообщений не отрисовался)  
**URL share:** https://chatgpt.com/share/6abd1faa-9cc4-83ed-8620-25ff5dc9065b  
**Заголовок в capture:** «Стратегия доработки»  
**Файл на диске (фактический путь):** `C:\Users\vkita\Documents\Ссылка в markdown\_chatgpt_share_downloads\CHATGPT_SHARE_6abd1faa_20260930_raw_capture.zip`  
*(В задании указана папка `markdown_chatgpt_share_downloads` — на vkita-pc архив лежит в `Ссылка в markdown\_chatgpt_share_downloads`.)*

**Извлечение:** 111 message-like фрагментов из embedded JSON (`internal/chatgpt-6abd1faa-messages.txt`, скрипт `internal/_extract_6abd1faa.py`). Полный пошаговый transcript с ролями user/assistant **не восстановлен** — capture `PARTIAL_RAW_CAPTURE` (`capture_status.json`).

**Ограничение:** без секретов, без вложений handoff-архивов, без токенов из HTML.

---

## Это тот чат, который нужен?

| Ожидание | Факт в `6abd1faa` |
|---|---|
| Мета-стратегия Cursor Project OPSX, перенос tiriel→adv-bot, Tempo, PR #26 | **Частично:** OPSX preflight и inventory есть, но **фокус — продукт WB Sky / adv-bot**, не Project store |
| Продолжение Tiriel «Промокоды» (`6abcdb39`) | **Нет** — другой share, другой продукт |
| Направление разработки adv-bot: workstreams, CPO, AI, сбор данных | **Да** — это основное содержание |

**Вывод:** `6abd1faa` — **главный продуктово-архитектурный стратегический чат по adv-bot / WB Sky** в веб-ChatGPT. `6abcdb39` — **узкий OPSX-continuation по промокодам Tiriel**, не замена этой стратегии (см. [chatgpt-strategy-6abcdb39.md](chatgpt-strategy-6abcdb39.md), §7.1 [opsx-working-instruction.md](opsx-working-instruction.md)).

---

## Куда идёт adv-bot (продуктовые цели)

1. **WB Sky как authority:** внешняя LLM формирует намерение / ChangeSet; **production writes только через WB Sky**; domain contract не зависит от transport; unknown state — fail closed; сначала contract + invariants, потом UI/API/MCP.
2. **Экономика CPO:** отдельный change **DRR_PERCENT → reference price → absolute Target/Max CPO** (режимы `FIXED_RUB` и `DRR_PERCENT`, V1 — shop-level DRR, без category/product overrides). Не ломать существующих пользователей и runtime с абсолютным CPO в рублях.
3. **PLAN vs FACT CPO:** параллельный workstream `separate-auto-search-cpo` (worktree `fix-search-cpc`) — Auto/Search CPO и attribution; **DRR-change не смешивать** с этим потоком.
4. **Данные и AI control plane:** исследовательский handoff → не «собрать всё за weekend», а **ChangeSetV1** между LLM и существующим runtime: preview, `expected_before`, conflict detection, отдельный контур от legacy Excel `setattr+commit`.
5. **Shop-wide read-side:** change `shop-wide-campaign-data-collection` — сбор рекламных данных по всем кампаниям магазина, в т.ч. не подключённым к управлению; временный архитектурный долг **TEMPORARY_DUAL_CAMPAIGN_COLLECTION** с путём к единому collector.
6. **Инфраструктурные соседи:** упоминаются worktree `clickhouse-migrations-control-plane`, `ai-package-v1-contract`; базовый repo `meta-repo/adv-bot`, **base branch `stage`**, разработка с **отдельными worktree на feature**, без смешивания dirty state.

Архитектурный вектор из чата: **много параллельных изолированных workstream → contract-first для AI → merge train / integration**, а не один бесконечный worktree на всё.

---

## Workstreams (как в чате)

| Поток | Смысл | Изоляция |
|---|---|---|
| **DRR-based CPO** | Новая экономическая модель CPO | Отдельный change/worktree; не лезть в `separate-auto-search-cpo` |
| **separate-auto-search-cpo** | Search/Auto CPO, PLAN/FACT | `fix-search-cpc` worktree |
| **shop-wide-campaign-data-collection** | Shop-wide read-only collection | Собственный worktree/branch; design review, planning repair через `/opsx-update` |
| **wt-ai-contracts-v1** (+ package, changeset, execution, telegram, history) | AI ChangeSet control plane | **Сначала blocking:** контракты + registry операций, потом до четырёх параллельных |
| **clickhouse-migrations-control-plane** | CH migrations (упомянут в collision map) | Отдельный worktree |
| **OPSX surface на adv-bot** | Preflight: `.opsx/`, commands, pipeline, `tools/scripts/` | Read-only discovery до старта change |

---

## Порядок работ (из чата)

1. **Collision map / registry worktree** — не трогать чужие dirty worktree; зафиксировать пересечения (например `wb_shop.py`, CH migrations между shop-wide и DRR).
2. **Read-only preflight** на `adv-bot` (inventory CPO, collectors, `ComplexAdv`) **до** production code и новых worktree.
3. **AI:** создать `wt-ai-contracts-v1` от актуального `stage`, зафиксировать V1-контракты и первые операции **до** параллельного кодинга пяти AI-worktree.
4. **Shop-wide:** OPSX Discovery & Pipeline Preflight (worktree preflight → OPSX inventory → pipeline recommendation → `READY_TO_START_OPSX` / `BLOCKED`); только потом одна конкретная slash-команда на старт change.
5. **DRR CPO:** отдельный стартовый промпт в **новый** чат проекта (явно отделён от `separate-auto-search-cpo`).
6. **Реализация фич:** OpenSpec change lifecycle (`/opsx-new` … `/opsx-apply` … verify) — в чате через промпты и `/opsx-update`, не ручной правкой planning artifacts без команды.
7. **Интеграция:** после параллельных веток — **merge train**, проверка вертикального сценария, не бесконечные долгоживущие worktree.

Упомянутый «weekend» план (26–27.09) для AI E2E — **исследовательский темп**, не обязательство store; полный handoff за два дня в чате признан нереалистичным.

---

## Связь со `stage`, scripts и OPSX-переносом

| Тема | Содержание чата |
|---|---|
| **`stage`** | Базовая ветка adv-bot; preflight и design review против доступного кода на `stage` |
| **`scripts/` / `tools/scripts/`** | Входит в OPSX inventory (registry, resolver, `/opsx-scripts` lane) — часть **локальной** OPSX-установки в worktree, не отдельный продуктовый goal |
| **Перенос game→adv-bot** | В share **не развёрнут** (нет manifest 16/23/61, `feature/opsx-full-command-transfer`) — это слой [adv-bot-transfer-holds.md](adv-bot-transfer-holds.md) / store, а не этот чат |
| **Tempo** | В извлечённом тексте **почти нет** — verification orchestration остаётся в store ([opsx-working-instruction.md](opsx-working-instruction.md) §2) |

Чат задаёт **что строить в продукте** и **как резать worktree**; store задаёт **как вести процесс OPSX/Tempo/перенос команд** на vkita-pc.

---

## Ограничения: команды, vkita-pc, Tempo vs OPSX

### Из чата

- Жёсткий **read-only / discovery** до создания OpenSpec change и до OPSX-команд на реализацию (shop-wide preflight).
- Planning repair — через **`/opsx-update <change>`**, не silent edits; architectural debt — **файл в репозитории**, не только чат.
- Модели в промпте: **Grok 4.7 High** + субагенты **Composer 2.5** для read-only исследований.
- Repo path: **`C:\Users\vkita\my_code\meta-repo\adv-bot`** и соседние worktrees под `meta-repo\`.

### Сверка с Project store (конфликты — только расхождения)

| Store ([opsx-working-instruction.md](opsx-working-instruction.md), [project-context.md](project-context.md)) | Чат `6abd1faa` | |
|---|---|---|
| Разработка **только через команды**; прямых правок нет (Owner 2026-09-30) | Много **готовых промптов** и `/opsx-update`, но ранние шаги — свободный discovery; правило «только команды» **не акцентировано** так же жёстко | **Частичное:** store строже; чат старше/шире по продукту |
| На **vkita-pc** субагенты **только composer-2.5** | Главный агент **Grok 4.7 High** в preflight-промпте | **Конфликт моделей** для локального исполнения |
| **Tempo** на участках verification; не путать с `/opsx-*` spine | Tempo **не обсуждается** | **Не конфликт** — другой слой |
| Перенос OPSX surface, merge **не авторизован** | Product merge trains для AI/фич | **Разные scope** (process transfer vs product integration) |
| Google Drive не использовать | Не упоминается | Согласовано по умолчанию |

---

## Надёжность capture

- `message_level_export_present: false` — порядок реплик Owner/assistant **не гарантирован**.
- Часть кириллицы в extract — mojibake; смысл ключевых блоков (workstream names, paths, OPSX preflight) читается по ASCII-якорям и дублирующим фрагментам.
- Для координатора: **store-инструкции по процессу приоритетнее** там, где чат молчит (Tempo, transfer holds, commands-only); **чат приоритетнее** по продуктовой карте workstreams и AI/CPO/shop-wide.

---

## Связанные документы store

- [opsx-working-instruction.md](opsx-working-instruction.md) — OPSX/Tempo, перенос, vkita-pc  
- [project-context.md](project-context.md) — потоки Project  
- [adv-bot-transfer-holds.md](adv-bot-transfer-holds.md) — перенос команд (не из этого чата)  
- [chatgpt-strategy-6abcdb39.md](chatgpt-strategy-6abcdb39.md) — Tiriel promocodes (не meta-strategy adv-bot)

**Internal evidence:** `internal/chatgpt-6abd1faa-messages.txt`, `internal/chatgpt-6abd1faa-parse-meta.json`
