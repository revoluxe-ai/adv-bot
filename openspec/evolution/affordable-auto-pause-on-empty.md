# Доступная автокампания: пауза при пустых ключах + тариф 1000₽

```text
STAR_ID: affordable-auto-pause-on-empty
STATUS: ACTIVE
OWNER: Owner
CREATED_AT: 2026-08-07T19:11:00Z
UPDATED_AT: 2026-08-08T04:38:00Z
DEPENDS_ON: none
```

## North Star

Платный авто-бот честно останавливает неработающую РК (все ключи OFF → пауза
кампании + периодическая перепроверка), остаётся в режиме «подключил и забыл»
без путающего ручного отключения бота от рекламы, стоит 1000₽/мес за кампанию
(в 5 раз дешевле прежних ~6000₽), честно тарифицирует ноги Auto/Search
(половина при одной на паузе, ноль если обе на паузе — без обхода «пауза в
момент списания»), и об этом ясно рассказывают пользователям.

Контекст: продукту почти 4 года; низкая популярность связана со сложным
входом (настройка под ситуацию) и неочевидным выходом; статистика показывает,
что даже с ботом реклама часто не даёт результата (~80% кейсов лучше выключить).

## Capability Scope

- Aliases: pause-on-empty-keywords, last-key-off-pause, тариф 1000, −80% цены,
  подключил-и-забыл, retire bot_active OFF, half-price one leg paused,
  fair pause billing, anti-gaming charge
- Domains: auto-updater v3 (keyword OFF / last key); AutoAdvActiveControl /
  `ensure_campaigns_active`; billing `tariffs_for_auto_setting` / Pricer /
  daily charge; WB active_status Auto+Search legs; Telegram UX;
  Owner channel communications
- Included outcomes:
  - автопауза РК после отключения последнего ключа ботом;
  - периодическое включение и перепроверка (корректно при окне статы 7 дней);
  - сообщение пользователю о причине паузы/перепроверки;
  - тариф авто 1000₽/мес за одну кампанию (базовая ставка);
  - тарификация по ногам: 1 активная нога → ~½; обе на паузе → 0 за эту пару;
    без обхода паузой «в момент списания»;
  - упрощение/снятие редкого ручного «отключить бота от РК»;
  - коммуникация изменений (TG и подходящие каналы).
- Excluded outcomes:
  - перепись логики автокампании за пределами pause/recheck/UX;
  - ship полной бесплатной/упрощённой версии как DoD pause/price Changes
    (готовится отдельно; в анонсе — статус «готовится» + поддержка);
  - отдача paid automation core бесплатно (см. config free/paid граница);
  - retire updater v2 (звезда `v3-only-retire-v2`).

## Evolution Path

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
не снятие `bot_active` toggle, не канал-анонс.

Evidence / completion: OpenSpec change `pause-auto-campaign-on-empty-keywords`
verified GO (2026-08-08); archived
`openspec/changes/archive/2026-08-08-pause-auto-campaign-on-empty-keywords`;
main spec `openspec/specs/pause-on-empty-keywords/spec.md`; ADL
`openspec/decisions/empty-keywords-pause-write-path/decision.md` Accepted;
7d-window risk closed in design/tests.

### INC-PRICE-01 — Тариф авто 1000₽/мес за кампанию

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Новая стоимость авто — 1000 рублей в месяц за одну кампанию
(−80% / в 5 раз дешевле относительно прежнего entry ~6000₽) как **базовая**
ставка полного комплекта (обе ноги в работе по правилам тарифа).

Contribution to North Star: Доступный вход при честном отношении к неэффективной рекламе.

Scope boundary: billing/pricer table/copy для 1000₽; не fair-pause metering
(`INC-BILL-LEG-PAUSE-01`); не pause runtime empty-keywords.

Evidence / completion: none yet.

### INC-BILL-LEG-PAUSE-01 — Честная оплата Auto/Search при паузе ног

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome (Owner 2026-08-08): Для пары ног одной авто-настройки (вид РК Auto и
вид РК Search):

1. Если используется только **одна** нога, а вторая на паузе — платишь
   **половину** базового тарифа за эту кампанию/комплект.
2. Если **обе** ноги на паузе — **не платишь** за них (0 за этот комплект
   в периоде тарифа).
3. **Anti-abuse:** нельзя обойти оплату, кратковременно ставя ногу(и) на паузу
   «под момент списания» (и сходные трюки). Нужен durable fair rule
   (например окно активности / доля времени в биллинг-периоде / latch —
   выбрать в design Change; не оставлять snapshot-only на instant WB status
   в секунду charge).

Contribution to North Star: Платишь за реально работающие ноги; честный оффер
рядом с empty-keywords pause и ценой 1000₽.

Scope boundary: Pricer / daily billing metering + anti-gaming; UX отображения
тарифа при паузе ног — в том же Change или тонкий follow-up. Не empty-keywords
runtime; не смена базовой цифры 1000 (это `INC-PRICE-01`); не retire v2.

Evidence / completion: none yet.

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

Обязательное содержание анонса (Owner 2026-08-07):

1. Снижение цены на 80%; новая стоимость — 1000₽/мес за одну кампанию;
   посыл: бот сейчас в пять раз дешевле.
1a. Честная тарификация ног: одна на паузе → половина; обе на паузе → 0;
    без обхода паузой в момент списания (когда `INC-BILL-LEG-PAUSE-01` готов).
2. Новый функционал: автопауза РК, если бот отключил последний ключ;
   периодическая повторная проверка / включение.
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
`INC-PAUSE-01` / цены.

Contribution to North Star: Закрывает «сложно подключить»; freemium-вход
согласован с vision free bot в `openspec/config.yaml` (не отдавать paid
automation core бесплатно — детали в отдельном free change).

Scope boundary: onboarding / free simpler product surface; не pause/price;
анонс о подготовке — в `INC-COMMS-01`.

Evidence / completion: none yet (Owner: in progress, not shipped).

## Forward Compatibility Constraints

- Reason паузы «все ключи OFF» отличим от budget/schedule pause (reason code / UX).
- Не менять auto keyword selection / bid logic beyond last-key → pause hook.
- Recheck/resume MUST быть корректен при окне статистики ≤7 дней (не предполагать
  более длинную историю).
- `ensure_campaigns_active` / A/B Hold coexistence: freeze ≠ stop; activity-control
  остаётся ортогональным (см. card-ab-hold decisions).
- Тарифный count по `bot_active` остаётся согласованным при любых UI-изменениях
  disconnect.
- Fair leg-pause billing MUST NOT полагаться только на мгновенный WB status в
  момент daily charge (anti-gaming invariant).
- Future onboarding simplification не требует speculative framework сейчас.

## Non-Goals

- Переписать автокампанию «заодно».
- Сделать linking обязательным для всех legacy changes.
- Включить free-bot / invite / unrelated freemium в DoD этой звезды.
- Трактовать EVOLUTION_PATH как обещанный backlog.

## Related North Stars

- V3-only: обесточить и выпилить updater v2 (`v3-only-retire-v2`) — соседняя
  линия (migrate/cutover/delete v2); не входит в DoD этой звезды.

## History

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
