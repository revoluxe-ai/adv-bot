# Стратегический бриф: ChatGPT share `6abcdb39`

**Источник:** Playwright DOM capture  
**URL share:** https://chatgpt.com/share/6abcdb39-ab00-83eb-8c85-ea857511c6e9  
**Заголовок в capture:** «Промокоды — OPSX Continuation 02»  
**Файл на диске (фактический путь):** `C:\Users\vkita\Documents\Ссылка в markdown\_chatgpt_share_downloads\CHATGPT_SHARE_6abcdb39_20260930_playwright_dom_full.zip`  
*(В задании указана слитная папка `…markdown_chatgpt_share_downloads` — на vkita-pc архив лежит в `Ссылка в markdown\_chatgpt_share_downloads`.)*

**Извлечение:** `parsed/conversation.md`, `parsed/conversation.json` (6 сообщений в DOM-парсере), полный видимый текст — `page_text.txt` (включая промежуточные шаги агента до обрыва capture на `/opsx-apply-scaffold` для SLICE-004).

**Ограничение:** в бриф не включены вложения (continuation pack, raw archive), секреты, cookies и токены из HTML.

---

## Это тот чат, который нужен?

| Ожидание (OPSX Project / adv-bot / tiriel meta) | Факт в zip |
|---|---|
| Общая стратегия Cursor Project, перенос game→adv-bot, Tempo, PR #26 | **Нет** — в тексте share этого нет |
| Продуктовый OPSX-цикл Tiriel, промокоды | **Да** — change `promocodes-auth-server-redeem`, worktree `fix/promocodes-issuance-redemption-20260927`, срезы SLICE-001…004 |
| Правило «только команды» | **Да** — финальная реплика Owner (сообщение 6) |

**Вывод:** zip **корректен по id `6abcdb39`**, но это **узкий continuation-чат по промокодам Tiriel**, а не полная стратегия OPSX/adv-bot/tiriel-meta. Мета-стратегия уже зафиксирована в Project store: [opsx-working-instruction.md](opsx-working-instruction.md), [project-context.md](project-context.md).

В `conversation.json` ошибочно указан старый share `6aae77bb…` («Имплементация Tiriel») — артеfact парсера; authoritative URL — `README.md` / `capture_status.json` (`6abcdb39`).

---

## О чём чат решал

1. **Миграция контекста** из предыдущего чата «Tiriel / Промокоды» через continuation pack + raw archive; порядок авторитетности: текущие Project Instructions и repo → артефакты OPSX в чате → `RUNTIME_CONTINUATION_CONTEXT` → raw archive как provenance.
2. **Frontier на старте:** SLICE-001 `IMPLEMENTATION_ADOPTED`, GREEN блокировался mismatch backend test runner; подготовлен **четырёхфайловый process repair** с scoped-токеном `AUTHORIZE_COMMAND_FIX` (только после re-verify repo/worktree).
3. **Продолжение разработки** после миграции: снятие блокера runner, GREEN для SLICE-001/002, product-дефект `_DEFAULT_CHARACTER` в `promo_grant.py` (до команды Owner — см. конфликты ниже).
4. **Жёсткое огранching исполнения:** Owner: «Продолжай, используй **строго только команды**» — дальнейшее движение через `/opsx-apply-green`, `/opsx-apply-implement`, `/opsx-pipeline NAVIGATE`, `/opsx-apply-scaffold` и Composer 2.5, без ручных правок и «одноразовых скриптов».

---

## Что в процессе (состояние на момент capture)

| Срез | Стадия (по тексту чата) |
|---|---|
| SLICE-001 | `GREEN_PROVEN` (после repair test runner) |
| SLICE-002 | `GREEN_PROVEN` через `/opsx-apply-green`; pipeline → SLICE-003 |
| SLICE-003 | `GREEN_PROVEN`; router → **APPLY_SCAFFOLD / SLICE-004** |
| SLICE-004 | В worktree `game-promocodes-cloud` уже `GREEN_PROVEN` (capture устарел; к 2026-09-30 срезы 001…013 закрыты, frontier — verification) |

Параллельно в чате: dirty `stage` не трогать; изолированный promo-worktree; проблемы **CLI wrapper** (блокировка передачи slash в `--print`, буферизация stdout TUI) — обход только через интерактивный `cursor-agent`, не через ручное чтение receipts.

---

## Порядок работ (как следует из чата)

1. **Re-verify** локальный repo/worktree и OPSX receipts **до любой записи**.
2. Если scope совпадает — только тогда **scoped** process repair (`AUTHORIZE_COMMAND_FIX`, четыре файла команд/процесса).
3. **Slice-конveyor OPSX** (не full-cycle Tempo):  
   `apply-green` → `apply-implement` → … → **`/opsx-pipeline NAVIGATE`** (read-only router следующего hop) → `apply-scaffold` / следующий slice-команда по frontier.
4. После каждого hop — **receipts и NEXT_COMMAND/NEXT_ACTION из команды**, не ручная диагностика product-файлов.
5. Owner вмешивается только scoped-токенами и явными slash-командами.

---

## Ограничения: команды vs правки, Tempo vs OPSX

### Из чата

- После сообщения Owner — **никаких ручных правок продукта и обходов**; только штатные `/opsx-*` по контракту.
- **До** этого правила агент в чате **правил** `backend/app/promo_grant.py` вручную (implementation-owned дефект) — это **исторический** шаг, не образец для Project OPSX/adv-bot.

### Сверка с уже записанным в Project store (2026-09-30)

| Запись в store | Чат `6abcdb39` | Согласованность |
|---|---|---|
| Разработка **только через команды**; сломанную команду чинят отдельным процессом командами | Подтверждено финальной репликой Owner; ранние ручные правки в том же чате — **противоречат** текущему правилу | **Частично:** правило усилено после SLICE-002; store трактует PR #26 и прошлые правки как не-образец |
| **Tempo** покрывает **участки**, не весь цикл; шире всех `/tempo-verification` | В чате **не используется** Tempo; slice-прогон через **`/opsx-apply-*`** и **`/opsx-pipeline NAVIGATE`** | **Не конфликт:** другой слой (product slice conveyor vs meta verification operator) |
| Одной tempo-команды на весь цикл **нет** (цель на будущее) | Не обсуждается | **Согласовано** |
| **adv-bot** перенос, 16/23/61 manifest, vkita-pc worker | Не в share | Store — отдельный поток; чат не заменяет |
| **PR #26** (прямая правка `opsx-apply`, spine plan-verification) | Не в share | Store: не образец, не мержить как паттерн |
| **Tiriel meta:** 10 contract gaps, spine после apply | Не в share | Store: чинить **командами**, не как PR #26 |

**Tempo vs OPSX в этом чате:** промокоды идут по **OPSX slice-командам** (`apply-green`, `apply-implement`, `apply-scaffold`, pipeline NAVIGATE). **Tempo** в store относится к **замороженной verification** и оркестрации check-ledger на change — это **другой участок**, который в `6abcdb39` не стартовал.

---

## Рекомендуемое использование брифа

- Для **промокодов Tiriel:** продолжать с frontier **SLICE-004 scaffold** (или актуального router после re-verify), **только slash OPSX**, re-verify worktree перед записью.
- Для **OPSX Project / adv-bot / tiriel-meta:** опираться на [opsx-working-instruction.md](opsx-working-instruction.md) и [tiriel-opsx-gaps.md](tiriel-opsx-gaps.md); этот zip **не заменяет** meta-стратегию.
- При коллизии текста чата и store **приоритет у Owner-правил в store от 2026-09-30** (commands-only, Tempo scope, PR #26 не образец).

---

*Подготовлено read-only из zip `CHATGPT_SHARE_6abcdb39_20260930_playwright_dom_full.zip`; репозитории не изменялись.*
