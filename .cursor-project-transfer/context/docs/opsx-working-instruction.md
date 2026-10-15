# Рабочая инструкция OPSX (стоящая)

Документ для агентов Project OPSX: что делать, куда смотреть, чего не путать. Текст ChatGPT из старого веб-чата **не переносится автоматически** — если Owner не положил его в store или репозиторий, его здесь нет.

**Жёсткое правило Owner (2026-09-30):** разработку вести только через команды. Если команда не доводит шаг, правку не делают руками в файлах. Её выносят в отдельный процесс и тоже закрывают специальными командами. Прямых правок продукта, команд и контрактов нет.

См. также: [контекст проекта](project-context.md), [разрывы tiriel](tiriel-opsx-gaps.md), [удержания переноса adv-bot](adv-bot-transfer-holds.md).

---

## 0. Как устроен этот Project

Owner раньше проекты Cursor не вёл. Этот Project — наша зона: OPSX и доведение adv-bot в этой концепции. Координатор держит инструкцию и статус, параллельно ведёт несколько независимых разработок и доработку самого OPSX. Один и тот же файл или worktree двумя потоками сразу не правят: такие шаги идут по очереди. Решения Owner из этого чата дописываются сюда, а не остаются только в переписке.

## 1. Что такое OPSX в этом Project

**OPSX** — способ вести продуктовую разработку через именованные slash-команды (`.cursor/commands/opsx-*.md`), правила, материализованный граф навигации (`.cursor/pipeline/GRAPH.md`) и машиночитаемые артефакты (`.opsx/`, OpenSpec `openspec/changes/**`).

Два параллельных потока (решение Owner):

| Поток | Где | Смысл |
|--------|-----|--------|
| **Продукт WB Sky** | adv-bot на **vkita-pc** | Довести бота в той же концепции OPSX, что и игра |
| **Мета / технология OPSX** | прежде всего **tiriel-game** | Чинить контракты, пайплайн, перенос поверхности, Temporal |
| **Выравнивание tiriel** | `revoluxe-ai/tiriel-game` («Kirill Game») | Более зрелая база: больше команд, upstream, верификация; здесь видны расхождения GRAPH ↔ canonical body |

Работа, которая раньше жила в веб-ChatGPT, теперь в **этом Cursor Project** (store + репозитории). Источник процесса — файлы в git, не история чата.

---

## 2. Две «дорожки» исполнения: OPSX-продукт и Temporal-оператор

Это **разные** контракты. Путать их — главный источник ошибок.

### 2.1. Дорожка `/opsx-*` (жизненный цикл change)

- **Кто решает «что дальше»:** тело **активной** команды (`PRIMARY_COMMAND` на один user turn), плюс жёсткие gate’ы внутри неё. Правило: `.cursor/rules/opsx-single-active-command.mdc` — в одном сообщении исполняется только одна slash-команда; остальные `/opsx-*` в тексте не загружаются.
- **GRAPH.md:** инвентарь и **советующая** навигация (`NEXT_ACTION`, `PATH_*`), не принудительный маршрут и не замена контрактов команд. Явно **не** покрывает `tempo-*` (в meta: «tempo-* out of scope (not opsx-*.md)»).
- **Типичный post-implementation spine** (состояние `impl_done` в GRAPH):
  1. `/opsx-plan-verification` — заморозить план проверок (`FROZEN` ≠ PASS);
  2. `/opsx-next-check` — **единственный планировщик** CURRENT-проверки по ledger;
  3. bounded-исполнители (`/opsx-run-tests`, browser-check, security-review и т.д.) — только по назначению из `CHECK_ASSIGNMENT`;
  4. после `ALL_REQUIRED_CHECKS_PASS` — `/opsx-verify` (read-only audit, не автоматический archive);
  5. archive — отдельно `/opsx-archive`, с собственными GO.

`/opsx-apply` пишет код и tasks; **не** подменяет plan-verification и **не** является Temporal.

### 2.2. Дорожка `/tempo-*` (Temporal operator)

Отдельное семейство команд: `tempo-verification`, `tempo-bugbot`, `tempo-security`, `tempo-project-bug-hunt`. Общий kernel: `.cursor/commands/_shared/tempo-pipeline.md`. Машинная спека: `tools/temporal/pipelines.json`, вход: `python tools/temporal/tempo_operator.py run …`.

**Это не** `/opsx-pipeline` и не «ещё один OPSX hop».

| Роль | Обязанность |
|------|-------------|
| **Owner** | Только slash, например `/tempo-verification change=<id> low low`. Не гонять вручную worker, `start.py`, Temporal UI. |
| **Агент** | Парсит аргументы → один вызов `tempo_operator.py run` → поднимает/чинит **процесс** (Docker Temporal, один worker, singleton workflow) → ждёт терминала → отчёт Owner. |

**Что Temporal делает:** **последовательность** вложенных agent-hop’ов (review activity → repair/execute activity → снова review). **Не** выбирает проверки, **не** чинит продукт после FAIL, **не** регенерирует verification plan.

Для **verification** (`/tempo-verification`):

```text
ensure_verification_context
→ execute_next_check  (внутри: /opsx-next-check)
→ execute_assigned_check (исполнитель из CHECK_ASSIGNMENT)
→ execute_next_check (reconcile)
→ … до ALL_REQUIRED_CHECKS_PASS или стоп
```

Сохраняется разделение полномочий:

- `/opsx-next-check` — sole scheduler ledger;
- bounded executor — sole writer `BOUNDED_CHECK_RESULT` для назначенной проверки;
- Temporal — только sequencing.

**Терминалы (verification):** `ALL_REQUIRED_CHECKS_PASS`, `VERIFICATION_CHECK_FAILED`, `VERIFICATION_CHECK_BLOCKED`, `BLOCKED_SNAPSHOT_DRIFT`, `CONTRACT_ERROR`, `EXECUTOR_COMPLETION_UNCERTAIN`, недоступность Temporal. После успеха **не** автозапускать `/opsx-verify` archive из этого пайплайна.

**Аргументы verification:** обязателен `change=<id>`; два последних токена — tier’ы `low|medium|high` для next-check и executor; **нет** `base=`/`head=` (возобновление с durable plan/bindings/ledger).

**Отказы и границы записи (tempo kernel):** разрешено трогать `tools/temporal/**`, `.tmp/temporal/**`, сами `tempo-*.md`; **запрещено** править product `src/**`, коммит/push, тела OPSX-команд.

**После терминала verification:** post-completion `owner-done-signal` (страница «перехватываю управление» в Owner Chrome через user-chrome-devtools, без нового профиля).

**Cloud VM:** вложенный Temporal-agent **не** имеет `cursor-ide-browser`. На `smoke_acceptance` CURRENT — handoff родительскому агенту: `/opsx-browser-check`, bounded `check-results`, reconcile ledger, снова `/tempo-verification` для оставшихся checks. Протокол: `tools/temporal/CLOUD-BROWSER-HANDOFF.md`, `AGENTS.md`.

Остальные tempo-пайплайны (кратко):

- **bugbot** — diff ветки к `base`, цикл `/review-bugbot` ↔ `/opsx-orch-bug-fix`;
- **security** — scope `src/**` + `tests/**`, `/review-security` ↔ `/opsx-bug-team`;
- **project-bug-hunt** — нужен `change=`, охота ↔ orch по change.

### 2.3. Что запускать сейчас, и куда Tempo идёт потом

Решение Owner (2026-09-30), сверено по файлам tiriel-game.

Часть обработки уже на Tempo. Если для участка есть подходящая `/tempo-*`, брать её, а не ручной набор `/opsx-*` внутри этого участка.

Проверено по `.cursor/commands/tempo-*.md`: одной команды на весь цикл (explore → change → apply → verification → verify → archive) **нет**.

| Команда | Что охватывает |
|---|---|
| `/tempo-verification change=<id> <tier> <tier>` | Самый широкий участок: прогон уже замороженной верификации до `ALL_REQUIRED_CHECKS_PASS` |
| `/tempo-bugbot` | Только review→repair диффа ветки |
| `/tempo-security` | Только security-срез `src/**` и `tests/**` |
| `/tempo-project-bug-hunt` | Только охота и orch по change |

`/tempo-verification` не делает explore, apply, `/opsx-verify` и archive. На Cloud браузерный smoke она отдаёт родителю.

Пока единой команды нет, цикл собирается так: участки до и после верификации — `/opsx-*`; сам прогон проверок — `/tempo-verification`, когда план уже заморожен. Пачкой все четыре `/tempo-*` полный цикл не изображать.

Цель на перспективу: **одна** tempo-команда на весь цикл. К Owner она обращается только когда без него шаг не пройти.

---

## 3. Как команде «разрешено» работать

1. Owner (или Project coordinator) задаёт **одну** primary slash-команду или явное задание worker’у с ссылкой на контракт.
2. Агент читает **только** назначенные пути: тело primary, named dependencies из него (например preflight), cited schema/tools.
3. **Projectization:** если `.opsx/projectization.yaml` не `COMPLETE`, многие writer-команды fail-closed → `/opsx-projectize` (токены `NEXT_ACTION` vs `NEXT_COMMAND` в разных местах — известный разрыв, см. tiriel-opsx-gaps).
4. **TARGET OVERRIDE** в frontmatter game-команд перекрывает canonical body ниже `BEGIN CANONICAL SOURCE BODY` (там часто остатки WB/pyright — не исполнять вслепую).
5. **Коммит и push** — только по явной просьбе Owner. **Google Drive** — не использовать. Субагенты — **composer-2.5**. На **локали** (vkita-pc) — **только** composer-2.5 standard, без других моделей.

---

## 4. Tiriel vs adv-bot

| | **tiriel-game** | **adv-bot** |
|---|-----------------|-------------|
| Зрелость OPSX | Выше: полный набор `opsx-*`, upstream snapshot, verification ledger, **четыре `tempo-*` на диске** | Перенос поверхности в worktree; продукт — Poetry/WB |
| Разработка продукта (Owner) | Ветка по `AGENTS.md`: `fix-bug-with-save-capture-on-mobile` (не infer `master` для PR) | **vkita-pc**, `C:/Users/vkita/my_code/meta-repo/adv-bot` + worktrees; worker должен быть запущен |
| Temporal | `tools/temporal/` + команды в `.cursor/commands/tempo-*.md` | **Отстаёт:** в `.cursor/commands/` **нет** файлов `tempo-*.md` (проверено поиском); в transfer manifest четыре tempo помечены proven на TARGET worktree, но live parity с game — отдельный вопрос |
| Тесты (ориентир) | `node --test`, `npm run build` | `poetry run pytest`, pyright-strict (в canonical apply-теле — не путать с game override) |

Tiriel — **эталон поверхности** для переноса; adv-bot — **целевой продукт**, куда поверхность адаптируют, не копируя `app/**` и продуктовые `openspec/changes/**`.

---

## 5. Перенос «знаний» (agent surface)

**Переносится:** `.cursor/commands`, rules, `.cursor/pipeline`, `.opsx/` (registry, adapters, tools), Temporal tooling — **не** application code.

**Живой перенос game → adv-bot:**

- Ветка: `feature/opsx-full-command-transfer`
- Worktree: `adv-bot-full-command-transfer` (путь на PC Owner — см. [adv-bot-transfer-holds](adv-bot-transfer-holds.md))
- Счётчики manifest (актуальная ориентация Owner): **16** `FUNCTIONAL_PROVEN`, **23** `IMPLEMENTED_UNVERIFIED`, **61** `EXISTING_ADAPTATION_REQUIRED`
- **Merge не авторизован**; functional parity / production ready не заявлены
- Следующий **именованный** hold в рекомендациях manifest: **`opsx-doctor`** — считать **не начатым**, пока Owner не дал GO на live run

---

## 6. PR #26 и Temporal — совместимость

[PR #26](https://github.com/revoluxe-ai/tiriel-game/pull/26): узкая правка — TARGET OVERRIDE в `opsx-apply.md`, чтобы после implementation primary spine совпадал с GRAPH: **plan-verification → next-check → verify**, вместо устаревшего «сразу `/opsx-verify mode=impl` + pyright-цепочка».

**Вывод для исполнения (без изменения PR):**

- PR **остаётся уместным** и **не конфликтует** с Temporal как control path.
- Причина: `/tempo-verification` начинает **исполнение уже замороженного** плана (цикл next-check + executors). Ему **нужен** предшествующий `/opsx-plan-verification` (и нормальный выход из apply на этот spine). PR чинит **навигацию сразу после apply**; Temporal **не заменяет** plan-verification и **не отменяет** необходимость согласованного post-apply handoff.
- PR **не покрывает** cloud browser handoff, post-completion `owner-done-signal`, bugbot/security tempo — это отдельный слой.
- Статус merge PR в mainline **не проверялся** в этом документе — unknown.

**Порядок для полного verification на change (game):**

1. `/opsx-apply` … done → (после PR #26 / override) `/opsx-plan-verification`
2. `/opsx-plan-verification` → `FROZEN`
3. Либо вручную цикл `/opsx-next-check` + исполнители, либо **один операторский** `/tempo-verification change=<id> <tier> <tier>` для автоматической последовательности шагов 3
4. `ALL_REQUIRED_CHECKS_PASS` → отдельно `/opsx-verify` при необходимости archive-eligible audit

---

## 7. Чего не делать

- Не править репозиторий напрямую. Нет команды — нет правки. Сломанную команду чинят отдельным процессом, тоже через специальные команды.
- [PR #26](https://github.com/revoluxe-ai/tiriel-game/pull/26) сделан прямой правкой `opsx-apply.md`, до этого правила. Это не образец. Не мержить и не продолжать его как прямой патч.
- Не считать правку только `opsx-apply` / GRAPH достаточной «всей» картины пайплайна — **есть отдельный Temporal operator**.
- Не подменять весь цикл пачкой `/tempo-*`. На участке, который Tempo уже закрывает, не идти ручными `/opsx-*` вместо неё.
- Не просить Owner запускать `tempo_operator.py`, worker, Temporal UI — это зона агента.
- Не давать Temporal выбирать checks, чинить код после verification FAIL, или пушить/коммитить из tempo-run.
- Не использовать Google Drive; не пушить adv-bot/tiriel без явного запроса.
- Не убивать Owner Chrome; CDP — через существующую сессию user-chrome-devtools.
- Не тащить в adv-bot продуктовый код game и наоборот при «переносе знаний».
- Не трактовать `opsx-doctor` как уже начатый hold.

---

## 7.1. Продуктовая стратегия adv-bot (основной ChatGPT)

Share `6abd1faa` («Стратегия доработки») — главный вектор WB Sky: contract-first AI ChangeSet, DRR→CPO отдельно от `separate-auto-search-cpo`, shop-wide collection, AI control plane (`wt-ai-contracts-v1` первым), изолированные worktree и merge train. База `meta-repo/adv-bot`, ветка `stage`. Бриф: [chatgpt-strategy-adv-bot-6abd1faa.md](chatgpt-strategy-adv-bot-6abd1faa.md). На vkita-pc модель исполнения — composer-2.5, не Grok из промптов чата.

## 7.2. Живой продуктовый чат Tiriel (промокоды)

Share `6abcdb39` («Промокоды — OPSX Continuation 02») — не мета-стратегия Project, а change `promocodes-auth-server-redeem` в worktree `fix/promocodes-issuance-redemption-20260927`. Apply/split-apply завершён; verification ledger **в процессе** (известен блокер smoke). **Не спешить с `/opsx-archive`:** после `ledger_status=COMPLETE` — по Owner-порядку `/tempo-bugbot`, затем `/tempo-security` («tempo review»), **стоп на моделях** (composer-2.5 на vkita-pc), projectization gate, `/opsx-verify mode=archive`, и только потом `/opsx-archive`. Полная карта gate’ов: [promocodes-closeout-process.md](promocodes-closeout-process.md). Бриф чата: [chatgpt-strategy-6abcdb39.md](chatgpt-strategy-6abcdb39.md). Движение только командами.

## 8. Текущий разумный следующий шаг (ориентация)

1. **Tiriel:** довести согласованность контрактов (список в [tiriel-opsx-gaps](tiriel-opsx-gaps.md)) командами, не прямой правкой. PR #26 прямой правкой не продолжать. Участок `/tempo-verification` не запускать, пока Owner сам его не назвал.
2. **adv-bot на vkita-pc:** продолжать продукт в OPSX-стиле на основном checkout; перенос — worktree `feature/opsx-full-command-transfer`; закрывать 23 unverified live run’ами и 61 adaptation по manifest; **merge не делать** без Owner.
3. **Meta:** развивать OPSX в tiriel (в т.ч. Temporal, ledger, handoff); при переносе на adv-bot сверять tempo и verification authority.
4. **Опционально по manifest:** первый live run **`/opsx-doctor`** на transfer worktree — только после явного GO Owner.

---

## 9. Непроверенное / unknown

- Фактическое состояние ветки PR #26 и merge в `master` / `fix-bug-with-save-capture-on-mobile`.
- Работает ли Docker/Temporal на конкретной машине Owner в момент run.
- Полный live parity четырёх `tempo-*` на adv-bot worktree vs tiriel (manifest claims vs эта cloud-копия adv-bot без tempo-команд в `.cursor/commands/`).
- Содержимое `adv-bot-active-work.docx` / детали текущего WB-среза — не разбиралось в этом документе.

---

*Документ подготовлен по чтению tiriel-game: `tempo-*.md`, `_shared/tempo-pipeline.md`, `tools/temporal/pipelines.json`, фрагменты `GRAPH.md`, `opsx-next-check.md`, `opsx-plan-verification.md`, `opsx-apply.md`, `AGENTS.md`; adv-bot — только сравнение наличия tempo-команд.*
