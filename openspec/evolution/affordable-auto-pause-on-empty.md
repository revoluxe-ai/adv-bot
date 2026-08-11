# Доступная автокампания: пауза при пустых ключах + тариф 1000₽

```text
STAR_ID: affordable-auto-pause-on-empty
STATUS: ACTIVE
OWNER: Owner
CREATED_AT: 2026-08-07T19:11:00Z
UPDATED_AT: 2026-08-11T05:12:00Z
DEPENDS_ON: none
```

## North Star

Платный авто-бот честно останавливает неработающие ноги рекламы по разным
причинам: пустые ключи → пауза **Search**; исчерпанное тестирование ставок
полок без ставки под нужный план → пауза **Auto** с отложенным перетестом;
остаётся в режиме «подключил и забыл» без путающего ручного отключения бота
от рекламы, стоит 1000₽/мес за кампанию (в 5 раз дешевле прежних ~6000₽),
честно тарифицирует ноги Auto/Search (половина при одной на паузе, ноль если
обе на паузе — без обхода «пауза в момент списания»), и об этом ясно
рассказывают пользователям.

Контекст: продукту почти 4 года; низкая популярность связана со сложным
входом (настройка под ситуацию) и неочевидным выходом; статистика показывает,
что даже с ботом реклама часто не даёт результата (~80% кейсов лучше выключить).

## Capability Scope

- Aliases: pause-on-empty-keywords, last-key-off-pause, Search-only empty
  keywords, auto-shelf exhausted pause, shelf bid retest interval, тариф 1000,
  −80% цены, подключил-и-забыл, retire bot_active OFF, half-price one leg
  paused, fair pause billing, anti-gaming charge
- Domains: auto-updater v3 (keyword OFF / last key); Auto Shelf Bid Control
  (coverage / plan_distance / retest epoch); AutoAdvActiveControl /
  `ensure_campaigns_active`; billing `tariffs_for_auto_setting` / Pricer /
  daily charge; WB active_status Auto+Search legs; Telegram UX (pause reason +
  shelf retest setting); Owner channel communications
- Included outcomes:
  - автопауза **Search** после отключения последнего ключа ботом;
  - периодическое включение и перепроверка Search (корректно при окне статы
    ≤7 дней);
  - автопауза **Auto (полки)** когда эпоха тестирования ставок исчерпана и нет
    ставки, дающей нужный план при допустимом CPO;
  - отложенный перетест Auto: интервал задаёт пользователь + product default
    (7 дней); новая эпоха не должна мгновенно «закрывать» покрытие старой
    историей;
  - сообщение пользователю о причине паузы/перепроверки (отдельно для
    empty-keywords и shelf no-plan);
  - тариф авто 1000₽/мес за одну кампанию (базовая ставка);
  - тарификация по ногам: 1 активная нога → ~½; обе на паузе → 0 за эту пару;
    без обхода паузой «в момент списания»;
  - упрощение/снятие редкого ручного «отключить бота от РК»;
  - коммуникация изменений (TG и подходящие каналы).
- Excluded outcomes:
  - пауза **обеих** ног из-за empty-keywords (Forbidden без нового Owner GO);
  - перепись логики автокампании / shelf bid selection за пределами
    pause/recheck/UX hooks;
  - ship полной бесплатной/упрощённой версии как DoD pause/price Changes
    (готовится отдельно; в анонсе — статус «готовится» + поддержка);
  - отдача paid automation core бесплатно (см. config free/paid граница);
  - retire updater v2 (звезда `v3-only-retire-v2`).

## Evolution Path

Owner achievement route (2026-08-10, advisory — not DoD):
`INC-PAUSE-02` → `INC-AUTO-COST-SHELF-COEXIST-01` → `INC-BILL-LEG-PAUSE-01` →
`INC-AUTO-SHELF-PAUSE-01` → `INC-PRICE-01` → `INC-COMMS-01`.
Hypothesis order below matches that route (PAUSE-02 Search delivery may
continue in parallel; COEXIST is ENABLING_FOUNDATION before AUTO-SHELF).

### INC-PAUSE-01 — Автопауза при пустых ключах + перепроверка

```text
STATUS: DONE
LINKED_CHANGES: pause-auto-campaign-on-empty-keywords
```

Outcome: Если бот в автокампании выключает последний ключ, следующим действием
РК ставится на паузу; периодически снова включается и перепроверяется;
пользователь получает понятное сообщение; поведение доказано совместимым с
ограничением статистики за 7 дней. Остальная логика автокампании не меняется.

Contribution to North Star: Честный «подключил и забыл» вместо молчаливого
кручения мёртвой рекламы; основа для цены и коммуникации.

Scope boundary: только last-key-OFF → pause + recheck + UX + 7d proof; не тариф,
не снятие `bot_active` toggle, не канал-анонс. (Первая поставка била в Auto-ногу;
целевая нога уточнена в `INC-PAUSE-02`.)

Evidence / completion: OpenSpec change `pause-auto-campaign-on-empty-keywords`
verified GO (2026-08-08); archived
`openspec/changes/archive/2026-08-08-pause-auto-campaign-on-empty-keywords`;
main spec `openspec/specs/pause-on-empty-keywords/spec.md`; ADL
`openspec/decisions/empty-keywords-pause-write-path/decision.md` Accepted;
7d-window risk closed in design/tests.

### INC-PAUSE-02 — Empty-keywords pause/recheck только на Search

```text
STATUS: DONE
LINKED_CHANGES: retarget-empty-keywords-pause-to-search
```

Outcome (Owner 2026-08-08): Пауза и matching recheck/resume по причине
empty-keywords применяются только к ноге **Search**
(`pause_auction_campaign` / Search start). `pause_auto_campaign` для этой
причины Forbidden; отсутствие Search MUST NOT fallback на Auto pause. Reason
`empty_keywords`, intent latch, notify и 7d-invariants сохраняются. Остальная
логика автокампании не меняется.

Note (Owner 2026-08-10): Search delivery continues via linked change in
parallel; star **handoff** Active increment for next Change is
`INC-AUTO-COST-SHELF-COEXIST-01` (orthogonal Auto/shelf foundation).

Contribution to North Star: Честная остановка именно поисковой ноги при пустых
ключах; Auto/полки живут отдельным lifecycle (`INC-AUTO-SHELF-PAUSE-01`).

Scope boundary: retarget empty-keywords write-path Auto→Search + durable
leg/adapters в decision/spec + paired tests; не тариф; не Auto shelf exhausted
pause; не billing fair-pause; не канал-анонс; не BOTH-legs.

Evidence / completion: OpenSpec change `retarget-empty-keywords-pause-to-search`
verified GO (2026-08-11); Product Acceptance PASS; archived
`openspec/changes/archive/2026-08-11-retarget-empty-keywords-pause-to-search`;
main spec `openspec/specs/pause-on-empty-keywords/spec.md` synced (Search
leg); ADL `openspec/decisions/empty-keywords-pause-write-path/decision.md`
Accepted (TARGET_ENTITY_OR_LEG=SEARCH; forbid `pause_auto_campaign` for
empty-keywords).

### INC-BILL-LEG-PAUSE-01 — Честная оплата Auto/Search при паузе ног

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome (Owner 2026-08-08 / route 2026-08-09): Для пары ног одной авто-настройки
(вид РК Auto и вид РК Search); Owner: **второе** после `INC-PAUSE-02`, до
`INC-COMMS-01`:

1. Если используется только **одна** нога (started), а вторая на паузе — платишь
   **половину** базового тарифа за эту кампанию/комплект.
2. Если **обе** ноги на паузе — **не платишь** за них (0 за этот комплект
   в периоде тарифа).
3. **Anti-abuse:** нельзя обойти оплату, кратковременно ставя ногу(и) на паузу
   «под момент списания» (и сходные трюки). Нужен durable fair rule
   (например окно активности / доля времени в биллинг-периоде / latch —
   выбрать в design Change; не оставлять snapshot-only на instant WB status
   в секунду charge).

Contribution to North Star: Платишь за реально работающие / started ноги;
честный оффер рядом с empty-keywords / shelf pause и ценой 1000₽.

Scope boundary: Pricer / daily billing metering + anti-gaming; UX отображения
тарифа при паузе ног — в том же Change или тонкий follow-up. Не empty-keywords
runtime; не shelf exhausted pause; не смена базовой цифры 1000 (это
`INC-PRICE-01`); не retire v2; не канал-анонс.

Evidence / completion: none yet.

### INC-AUTO-COST-SHELF-COEXIST-01 — Pin legacy autobidder vs shelf coexistence

```text
STATUS: DONE
LINKED_CHANGES: pin-legacy-autobidder-vs-shelf-coexistence
```

Outcome (Owner 2026-08-10): Зафиксировать и доказать coexistence contract:
при включённом **«Управление ставкой в полках»** старый путь **«управление
ставкой для Авто»** не пишет ставку; reasons записи ставки vs cost-паузы
различимы. Characterization + paired regression; **без** terminal
shelf-exhausted pause/retest и **без** rewrite биддера / plan_distance.

Contribution to North Star: Безопасный фундамент перед честной паузой полок
(`INC-AUTO-SHELF-PAUSE-01`).

Scope boundary: pin/prove coexistence; не terminal Auto shelf pause; не
retest; не empty-keywords Search; не billing; не 1000₽; не comms.

Evidence / completion: archived
`openspec/changes/archive/2026-08-11-pin-legacy-autobidder-vs-shelf-coexistence`;
main spec `openspec/specs/auto-bid-module-coexistence/spec.md`; ADL
`openspec/decisions/auto-bid-module-coexistence-write-path/decision.md`.

### INC-AUTO-SHELF-PAUSE-01 — Пауза Auto/полок при исчерпании ставок без plan-fit + перетест

```text
STATUS: ACTIVE
LINKED_CHANGES: none
```

Outcome (Owner 2026-08-08 / return 2026-08-11 — **авто-отключение Авто-РК**):
Нога **Auto (полки)** ставится на паузу только когда одновременно
(после DONE `INC-AUTO-COST-SHELF-COEXIST-01`; BILL остаётся отдельным
hypothesis):

1. текущая эпоха тестирования ставок **исчерпана** (больше нечего тестировать
   в допустимом диапазоне / coverage epoch complete);
2. среди квалифицированно протестированных ставок **нет** ставки, дающей
   нужный план продаж при допустимом CPO (plan-fit / no plan-bid).

После паузы обязателен **отложенный перетест**:

- интервал задаёт пользователь в UI настроек полок;
- product default = **7 дней** (согласован с окном статы PLAN_DISTANCE);
- по наступлении интервала Auto снова стартует и начинается **новая эпоха**
  тестирования;
- окно покрытия для новой эпохи MUST NOT мгновенно закрывать все ставки из
  старой истории (использовать `date_from = max(now-7d, retest_epoch_started_at)`
  или эквивалент — зафиксировать в design Change).

Отдельный activity reason (не маскировать под empty-keywords / schedule /
budget / legacy `COST_RULE_FAILED` как terminal shelf-exhausted). Пользователь
получает сообщение: почему пауза Auto и когда следующий перетест. Управление
ставками полок (`auto_shelf_bid_control_enabled`) остаётся включённым; паузится
WB Auto-нога. Бюджет / расписание / баланс / emergency latch имеют приоритет
над retest-start.

Contribution to North Star: Честная остановка полок, когда тест завершён и
плана нет; периодический шанс снова найти рабочую ставку без ручного
«отключить бота».

Scope boundary: Auto shelf terminal pause + user/default retest interval +
reason/notify + durable write-path decision (Architecture Decision Missing до
proposed decision в Change); не empty-keywords Search path; не тариф 1000; не
fair-pause billing; не канал-анонс; не перепись plan_distance math сверх
terminal/retest hook.

Evidence / completion: none yet. Перед apply-ready Change MUST proposed
decision ownership: shelf manager (detect/intent/epoch) → activity-control
(WB pause/start) → Telegram setting (interval).

### INC-PRICE-01 — Тариф авто 1000₽/мес за кампанию

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome (route 2026-08-09): Новая стоимость авто — 1000 рублей в месяц за одну
кампанию (−80% / в 5 раз дешевле относительно прежнего entry ~6000₽) как
**базовая** ставка полного комплекта (обе ноги в работе по правилам тарифа).
Owner: **на потом**, обязательно до `INC-COMMS-01` / прессрелиза; не next
после `INC-PAUSE-02`.

Contribution to North Star: Доступный вход при честном отношении к неэффективной рекламе.

Scope boundary: billing/pricer table/copy для 1000₽; не fair-pause metering
(`INC-BILL-LEG-PAUSE-01`); не pause runtime empty-keywords / shelf exhausted;
не канал-анонс как substitute для смены цифры.

Evidence / completion: none yet. Runtime baseline: `tariffs_for_auto_setting[1]
= 6000`.

### INC-DISCONNECT-01 — Убрать путающее ручное отключение бота от РК

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Редко используемое ручное отключение бота от рекламы (`bot_active=False`)
упрощено: убран/скрыт UI; уже выключенные мигрируют во «включён»; биллингный
контракт `bot_active` для ACT не ломается. Default draft: UI-off + migrate OFF→ON.

Contribution to North Star: «Подключил и забыл» без неочевидного «как отключить».

Scope boundary: не pause WB-кампании; не смена цены; не упрощение всего онбординга.

Evidence / completion: none yet.

### INC-COMMS-01 — Коммуникация изменений

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Пакет для Telegram-канала (+ подходящие каналы) с полным перечнем
пунктов ниже. Не product-code DoD.

Обязательное содержание анонса (Owner 2026-08-07 / уточнение 2026-08-08):

1. Снижение цены на 80%; новая стоимость — 1000₽/мес за одну кампанию;
   посыл: бот сейчас в пять раз дешевле.
1a. Честная тарификация ног: одна на паузе → половина; обе на паузе → 0;
    без обхода паузой в момент списания (когда `INC-BILL-LEG-PAUSE-01` готов).
2. Новый функционал:
   - автопауза **Search**, если бот отключил последний ключ; периодическая
     повторная проверка / включение Search;
   - автопауза **Auto/полок**, если все ставки эпохи протестированы и нет
     ставки под нужный план; перетест через интервал (user + default 7 дней)
     — когда соответствующий increment готов.
3. Причина: по наблюдениям Owner ~80% случаев рекламу лучше выключить —
   не даёт результата; статистика это подтверждает («упрямая вещь»),
   в т.ч. личный кейс Owner даже с ботом.
4. Перечислить **весь** актуальный функционал продукта (полный список
   возможностей в анонсе, не только новинки).
5. Сообщить, что готовится **бесплатная**, более простая и понятная версия
   (в т.ч. для новичков) — Owner её готовил/готовит, к моменту анонса ещё
   не успел закончить.
6. Пока упрощённая/бесплатная версия не готова — компенсация: личная
   поддержка в чате («пишите в чат / Owner — отвечу максимально быстро»).
7. Раньше поддержка была медленной; сейчас Owner исправляется; уже есть
   опытная помощница, которая и Owner пнёт, и сама может помочь.

Contribution to North Star: Донести оффер, доверие и честный статус
«упрощение ещё в пути + поддержка сейчас».

Scope boundary: копирайт/канал; не реализация free-bot; не pause/billing code.
Не публиковать обещание ½/0 / 1000₽ / shelf-pause, пока соответствующие
increments не поставлены (Owner route 2026-08-09).

Evidence / completion: none yet.

### INC-ONBOARD-01 — Упростить подключение / бесплатная понятная версия (in progress)

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Owner готовит улучшенную версию — простую и понятную, подходящую
новичкам; в коммуникации она позиционируется также как **бесплатная** более
простая версия в целом. Снижает трение «надо настроить под конкретную
ситуацию». К моменту текущего анонса ещё не готова — не текущий DoD
pause/price increments.

Contribution to North Star: Закрывает «сложно подключить»; freemium-вход
согласован с vision free bot в `openspec/config.yaml` (не отдавать paid
automation core бесплатно — детали в отдельном free change).

Scope boundary: onboarding / free simpler product surface; не pause/price;
анонс о подготовке — в `INC-COMMS-01`.

Evidence / completion: none yet (Owner: in progress, not shipped).

## Forward Compatibility Constraints

- Empty-keywords: TARGET_ENTITY_OR_LEG=SEARCH; FORBIDDEN Auto pause adapter
  для этой причины; no Auto fallback if Search missing.
- Reason «нет активных ключей» отличим от budget/schedule и от shelf
  no-plan-bid reason (отдельные reason codes / UX).
- Не менять auto keyword selection / bid logic beyond last-key → pause hook.
- Recheck/resume Search MUST быть корректен при окне статистики ≤7 дней.
- Auto shelf terminal pause: detect/intent/epoch ownership и WB pause/start
  ownership MUST быть в accepted/proposed architecture decision до
  apply-ready (`Architecture Decision Missing` until Change proposes it).
- Retest epoch для Auto MUST NOT требовать статы старше 7 дней и MUST NOT
  считать эпоху «уже покрытой» только по истории до `retest_epoch_started_at`.
- Для shelf-enabled кампаний terminal shelf-exhausted MUST NOT маскироваться
  под ordinary `COST_RULE_FAILED` как единственный durable reason (legacy
  non-shelf cost pause остаётся ортогональным).
- Legacy bid-module coexistence (`INC-AUTO-COST-SHELF-COEXIST-01` DONE) MUST
  remain valid; terminal shelf pause MUST NOT break «полки ON → старый путь
  ставки игнорируется» и MUST NOT маскировать terminal reason под ordinary
  cost pause.
- `ensure_campaigns_active` / A/B Hold coexistence: freeze ≠ stop; activity-control
  остаётся ортогональным (см. card-ab-hold decisions).
- Тарифный count по `bot_active` остаётся согласованным при любых UI-изменениях
  disconnect.
- Fair leg-pause billing MUST NOT полагаться только на мгновенный WB status в
  момент daily charge (anti-gaming invariant).
- Future onboarding simplification не требует speculative framework сейчас.

## Non-Goals

- Переписать автокампанию «заодно».
- Пауза обеих ног из-за empty-keywords без отдельного Owner GO.
- Сделать linking обязательным для всех legacy changes.
- Включить free-bot / invite / unrelated freemium в DoD этой звезды.
- Трактовать EVOLUTION_PATH как обещанный backlog.

## Related North Stars

- V3-only: обесточить и выпилить updater v2 (`v3-only-retire-v2`) — соседняя
  линия (migrate/cutover/delete v2); не входит в DoD этой звезды.

## History

- 2026-08-11T05:12:00Z — Owner GO return: задача = **авто-отключение Авто-РК**
  → `INC-AUTO-SHELF-PAUSE-01` ACTIVE; `INC-AUTO-COST-SHELF-COEXIST-01` marked
  DONE (archive 2026-08-11); index Active → AUTO-SHELF; OWNER_INTENT product
  language preserved in handoff.
- 2026-08-10T09:02:00Z — Owner GO: next Change =
  `pin-legacy-autobidder-vs-shelf-coexistence` /
  `INC-AUTO-COST-SHELF-COEXIST-01` (ENABLING_FOUNDATION before
  `INC-AUTO-SHELF-PAUSE-01`); PAUSE-02 Search remains orthogonal/parallel;
  achievement route inserts COEXIST before BILL/AUTO-SHELF; forward-compat
  coexistence pin added.
- 2026-08-09T06:48:30Z — Owner GO + RECOMMENDED: close `INC-PAUSE-02` first;
  achievement route reorder PAUSE-02 → BILL-LEG → AUTO-SHELF → PRICE → COMMS;
  PRICE explicitly deferred until before press release; BILL is second before
  COMMS; STAR_ROUTE / EVOLUTION_PATH section order updated (hypotheses, not DoD).
- 2026-08-08T16:35:47Z — Owner GO: empty-keywords = Search-only; Auto/полки —
  отдельный `INC-AUTO-SHELF-PAUSE-01` (exhausted bids + no plan-fit + user/default
  7d retest); added ACTIVE `INC-PAUSE-02`; COMMS/forward-compat/non-goals updated.
- 2026-08-08T03:52:00Z — Owner: `INC-BILL-LEG-PAUSE-01` — half tariff if one
  Auto/Search leg paused, zero if both paused; anti-abuse vs pause-at-charge;
  North Star / COMMS / forward-compat updated; PRICE stays base 1000.
- 2026-08-08T03:41:00Z — Related: linked `v3-only-retire-v2` (Owner retire-v2
  nearest work; separate star so pause/price DoD stays narrow).
- 2026-08-07T19:11:00Z — card created from Owner evolution session: pause-on-empty,
  1000₽ (−80%), retire rare bot disconnect, channel comms; rationale — ~4y product,
  low popularity from hard connect/disconnect, Owner stats observation on ineffective ads.
- 2026-08-07T19:20:00Z — Owner `/opsx-explore` «это запиши»: expanded `INC-COMMS-01`
  (full feature list in announce; free simpler version in prep; chat support +
  faster replies + assistant); `INC-ONBOARD-01` marked in-progress / not shipped.
