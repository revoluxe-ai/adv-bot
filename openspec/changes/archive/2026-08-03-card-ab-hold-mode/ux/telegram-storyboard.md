# Telegram Storyboard — A/B Hold WARM_UP / Confirm / Epoch Flow

## 0. Status and how to read this

Scene-by-scene walkthrough of the screens/keyboards/transitions fixed in
`openspec/changes/card-ab-hold-mode/ux/telegram-ux-contract.md` (the **contract**). This document does not
redefine any invariant from the contract; it illustrates it with concrete (but non-binding — implementation
MAY adjust exact wording during a future `/opsx:apply` as long as the contract's invariants hold) example
copy, and explicitly calls out the contradiction each scene is written to avoid.

Planning-level only. Does not authorize implementation, does not reopen financial scope, does not touch
OD-05, does not introduce monitoring/emergency-stop. See contract §0/§2 for the full boundary restatement.

Mockup blocks below show: message text (illustrative RU copy) then keyboard rows exactly as fixed in
contract §5.

---

## S0 — Entry / instruction screen

**Fixes:** "S0 text and keyboard must match"; "no hard-cap / guaranteed overshoot bound promises".

### S0, mode `OFF`

```
Режим A/B тестирования карточки (A/B Hold)

Что произойдёт:
1. Вы подтвердите набор ключей для теста.
2. Кампания пройдёт прогрев не короче 24 часов без фиксации целей.
3. После прогрева вы увидите факт-позицию и предложенную цель по каждому
   ключу и подтвердите их.
4. Отдельно вы подтвердите участие Auto и ставку Auto.
5. Система один раз синхронизирует Wildberries и запустит активный hold —
   биддер продолжит работать к подтверждённым целям.

Суточный бюджет/лимит активности кампании работает как обычно: это порог
остановки, а не жёсткий потолок расходов. Возможен перерасход относительно
порога (задержка статистики, работа воркера, уже запущенные траты) без
гарантированной числовой границы; на следующие сутки счётчик и траты
сбрасываются заново. Это не финансовая защита A/B-теста — только
существующий контроллер активности кампании.

Статистика иногда временно недоступна или устаревает. Чтобы ровный тест
не ломался на таких сбоях, бот в эти моменты не меняет состав ключей и
ставки «наугад» (решения откладываются до свежих данных). Тест при этом
продолжается. Вы берёте на себя контроль хода теста.

До запуска: рекомендуется прогреть РК без зажатого max CPO и с запасом
плана продаж; рекомендуется выключить полки (если без них нет трафика —
на ваше усмотрение); не меняйте цену на период теста.

[ Включить A/B тест ]
[ ← Назад ]
```

*Contradiction fix, explicit:* no "перерасход будет небольшим", no "лимит × дни"
arithmetic, no promise of a bound. The keyboard offers exactly `Включить A/B тест` +
`← Назад` — the text does not mention any other action (no Disable, because there is
nothing to disable while `OFF`).

### S0, mode ≠ `OFF` (poll-driven; user reopens the menu mid-flow)

```
Режим A/B тестирования карточки (A/B Hold)

Текущий шаг: <phase label, e.g. "Прогрев (WARM_UP)", "Подтверждение целевых
позиций", "Синхронизация с Wildberries", "Активный hold">

[ Открыть текущий шаг ]
[ Выключить A/B тест ]
[ ← Назад ]
```

The keyboard here matches the text: it never claims "можно запускать A/B" unless the
current step actually is `ACTIVE` (H1) — see §H1 below and contract §13.

---

## S1 — Keyword-set confirm (before warm-up)

**Fixes:** "no auto add/return"; "safety exclusion allowed"; "Back saves draft"; "Cancel separate".

```
Подтверждение набора ключей для A/B теста (стр. 1/2)

Ниже — ключи, прошедшие проверку (pay_for_order ≤ план max CPO,
≥100 показов). Отметьте, какие ключи войдут в тест. Новые ключи не
добавляются автоматически, а исключённые вручную не возвращаются
автоматически, пока идёт этот шаг и последующий прогрев.

✅ ключевая фраза один [нажать, чтобы исключить]
✅ ключевая фраза два [нажать, чтобы исключить]
❌ ключевая фраза три (исключена вручную) [нажать, чтобы включить]
... (до 10 позиций на странице)

[ ◀ Стр. ]  [ Стр. ▶ ]
[ Подтвердить набор ]
[ ← Назад ]  [ Отмена ]
```

- Toggling a row (`keyword_toggle`) only edits the draft and redraws the same page —
  it never moves the phase.
- `◀ Стр. / Стр. ▶` (`page_prev`/`page_next`) never touches Back/Cancel state and never
  discards toggles made on other pages (contract §9).
- `Подтвердить набор` (`keyword_set_confirm`) commits the draft and enters WARM_UP
  duration configuration (**S2**); it does **not** set `warmup_started_at` / start the timer
  (contract §4/§6).
- `← Назад` preserves every toggle across every page and reopens exactly here later
  (contract §7).
- `Отмена` opens a distinct confirmation sub-dialog:

```
Отменить запуск A/B теста? Черновик набора ключей будет утрачен, режим
останется выключен.

[ Да, отменить ]  [ Нет, продолжить ]
```

Because this is the **first** confirm of a fresh epoch attempt, nothing durable exists
yet (contract §8 resolution rule): `Да, отменить` returns to S0/`OFF` and clears
nothing, because there is nothing to clear.

---

## S2 — Warm-up config (default 24h, min 24h, increase only)

**Fixes:** "cannot choose <24h"; "100 views/keyword and 1000 aggregate views are NOT duration".

```
Длительность прогрева (WARM_UP)

По умолчанию — 24 часа (минимум). Вы можете увеличить длительность, но не
можете уменьшить её ниже 24 часов.

Пороги «≥100 показов на ключ» и «≥1000 показов по кампании» — это условия
допуска ключа/кампании к тесту, а не длительность прогрева: они не
заменяют и не сокращают 24-часовой таймер.

Текущий выбор: 24 часа

[ 24ч (по умолчанию) ]
[ Увеличить: +24ч ]  [ Увеличить: +48ч ]
[ Подтвердить длительность ]
[ ← Назад ]  [ Отмена ]
```

Attempting to submit any value below 24h is not offered by the keyboard at all (no
free-text entry below the floor) — the system does not need to "reject" an input the
keyboard structurally cannot produce. `Отмена` behaves as in S1 (nothing durable yet
for this attempt → abort to `OFF`, nothing to clear).

---

## S3 — Warm-up progress

**Fixes:** "stale/missing stats = decision freeze not campaign stop"; "daily budget continues"; forbid «лимит × дни» and «перерасход будет небольшим».

```
Прогрев идёт: осталось ≈ 6 ч 40 мин (из 24 ч)

Во время прогрева: без автоматического добавления новых ключей и без
автоматического возврата исключённых; целевая позиция ещё не
фиксируется. Защитное исключение ключа при риске перерасхода
по-прежнему возможно.

[если применимо] Заморожено: статистика по ключу «ключевая фраза два»
устарела — решение о включении/ставке отложено до свежих данных.
Это не останавливает кампанию и не останавливает таймер прогрева.

Суточный бюджет кампании продолжает работать как обычно (порог
остановки, не жёсткий лимит; без гарантированной границы перерасхода;
сброс на следующие сутки).

[ Обновить статус ]
[ Изменить набор ключей ]
[ Выключить A/B тест ]
[ ← Назад ]
```

- `Изменить набор ключей` (`keyword_edit_open`) opens **S1b**, not S1: the header of S1b
  explicitly states that confirming an edit here ends the current timer and returns to
  duration configuration (**S2**); the new timer starts only after `warmup_duration_confirm`
  (contract §4/§6; decision `ab-hold-epoch-lifecycle-and-generation-ownership` §4).
  Cancelling out of S1b (contract §8, case "prior durable value exists") leaves the
  original confirmed keyword set and the running timer **untouched**.
- No Cancel button here — S3 has no draft; `Выключить A/B тест` (EXIT) is the only
  abort path, and it is visually/semantically distinct from Cancel (contract §8 table).
- The freeze banner is conditional and explicitly framed as "decision frozen", never as
  "campaign stopped" (contract §11).

---

## W3 — Propose TP (keyword → factual current position → proposed target place)

**Fixes:** position vs target place semantically separate; page size 10; explicit confirm; ENTER does not recalc; drift does not reopen.

```
Подтверждение целевых позиций (стр. 1/2)

По каждому ключу показаны два отдельных значения: факт (текущая
наблюдаемая позиция) и предложенная цель (рассчитана функцией
ab_hold_target_place_from_keyword по факт-позиции после прогрева).
Совпадение чисел после округления — не повод считать поля одним
значением.

ключевая фраза один
  факт: 14   →   предложенная цель: 12
ключевая фраза два
  факт: 9    →   предложенная цель: 9   (совпали после округления —
                  это два разных поля, оба показаны)
... (до 10 ключей на странице)

[ ◀ Стр. ]  [ Стр. ▶ ]
[ Подтвердить целевые позиции ]
[ ← Назад ]  [ Отмена ]
```

- `Подтвердить целевые позиции` (`tp_confirm_all`) commits **all** shown target places
  as durable, immutable-for-this-epoch parameters, then moves to A1.
- No per-keyword "recalculate" control exists on this screen, and none is added later:
  once confirmed, a subsequent setup tick, activation retry, or ordinary factual
  position drift never recalculates or reopens confirmation (spec "Target place
  requires explicit confirmation and becomes immutable for the epoch").
- `Отмена` here aborts the whole epoch attempt to `OFF` (nothing durable for *this*
  screen's item existed yet — TP was never committed before this point).

## W3 — Confirmed / read-only (after confirm)

**Fixes:** after W3 confirm, Back → read-only W3, not editable; no re-calc impression.

```
Целевые позиции зафиксированы для текущей эпохи (стр. 1/2)

ключевая фраза один
  факт: 14 (текущая, может дрейфовать)   →   цель: 12 (зафиксирована)
ключевая фраза два
  факт: 9                                 →   цель: 9 (зафиксирована)

Дрейф факт-позиции после фиксации не переоткрывает подтверждение и не
пересчитывает цель этой эпохи.

[ ◀ Стр. ]  [ Стр. ▶ ]
[ Выключить A/B тест ]
[ ← Назад ]
```

There is no edit/confirm control on this screen — it is display-only. Every `Back`
pressed from A1, A2, P1, P2, or H1 during this epoch resolves here, never to the
editable W3-propose screen (contract §7 last row, §12).

---

## Auto participation confirm

**Fixes:** separate confirm; recommendation metrics separated from user decision.

```
Участие Auto в тесте

Search-ключи и целевые позиции уже подтверждены отдельно — это не
подразумевает решение по Auto. Подтвердите отдельно: участвует ли
реклама типа Auto в этой эпохе теста.

[для справки, не как решение] Показатели Auto за последний период:
CTR X%, CPO Y ₽ — это информация, а не автоматическое решение;
выбор ниже принимаете вы.

[ Да, участвует ]
[ Нет, не участвует ]
[ ← Назад ]  [ Отмена ]
```

Pressing either participation button is the explicit confirm (`auto_participation_confirm`);
neither Search confirmation nor this Auto-participation confirmation implies the other
(spec "Auto participation requires a separate explicit confirmation").

## Auto bid confirm

**Fixes:** Auto bid explicit confirm; ACTIVE freezes Auto bid competing mutators.

```
Ставка Auto для этой эпохи

Отдельно от участия Auto подтвердите ставку. После перехода в активный
hold обычное автообновление ставки Auto не будет менять подтверждённое
здесь значение до новой эпохи (после отключения и повторного включения
теста, либо после изменения набора ключей во время прогрева).

Ставка Auto: <value> ₽

[ Подтвердить ставку Auto: <value> ₽ ]
[ Изменить значение ]
[ ← Назад ]  [ Отмена ]
```

`auto_bid_confirm` is the last confirmation. On success it immediately: assigns the
generation, writes the durable PENDING intent (all four confirmed groups + generation),
and moves to P1 — before any WB write occurs (contract §13).

---

## PENDING → WB sync → ACTIVE

**Fixes:** no WB mutation before durable PENDING intent; sync progress separate from ACTIVE; partial sync non-ACTIVE recoverable; same-generation retry; no new epoch; no recalc.

### P1 — Syncing

```
Синхронизация с Wildberries

Все подтверждения получены. Параметры этой эпохи сохранены. Выполняется
однократная синхронизация с Wildberries. Режим станет активным только
после полного успеха синхронизации.

[ Обновить статус ]
[ ← Назад ]
```

No Disable button while the *first* sync attempt of a brand-new generation is in
flight (there is nothing to "turn off" yet that has any WB side effect — the intent is
durable but nothing was written to WB before this screen existed, contract §13).

### P2 — Sync partial (recoverable)

```
Синхронизация выполнена частично

Часть подтверждённых параметров применена в Wildberries, часть — ещё нет.
Режим пока не активен. Повторная попытка использует те же параметры этой
же эпохи без пересчёта целевых позиций и ставки Auto и без создания
новой эпохи.

[ Обновить статус ]
[ Выключить A/B тест ]
[ ← Назад ]
```

No numeric retry-count or ETA promise is shown (no invented retry cadence — that
remains a shop-runner scheduling detail per decision §8, not a UI commitment).

### H1 — Active hold

```
A/B Hold активен

Можно запускать A/B-тест: набор ключей и целевые позиции зафиксированы,
биддер продолжает работать к подтверждённым целям. Auto-ставка и участие
зафиксированы на эту эпоху. Структурные изменения (whitelist, разгон,
пересчёт минус-фраз) заморожены на время hold.

Суточный бюджет кампании продолжает работать как обычно (порог
остановки, не жёсткий лимит; сброс на следующие сутки; без
гарантированной границы перерасхода).

[если degraded=true, заменяет строку "можно запускать A/B-тест" честным
статусом деградации — без изменений к существующему decision §8 honest
degradation поведению]

[ Подробности по ключам ]
[ Выключить A/B тест ]
[ ← Назад ]
```

`ACTIVE` (H1) is reached **only** through P1 → full success, never directly from any
earlier screen (contract §4/§13); "можно запускать A/B" is only ever shown here.

---

## Stale callback

**Fixes:** no state change; show current screen; diagnosable.

Example: user has S1 open on device A with keyword toggles drafted; on device B they
already confirmed the keyword set and WARM_UP has been running for an hour; device A's
stale `keyword_toggle` callback arrives after that.

```
[toast, non-alert] Экран обновился — показываю актуальный шаг.
```

The bot then redraws **S3** (the actual current phase) on device A, not the stale S1.
No toggle is applied, no phase changes because of this stale callback, and the event is
logged at WARNING with `adv_id`, action id, expected vs. received revision/generation,
and current phase (contract §10). This applies identically to a stale `tp_confirm_all`,
a stale `auto_bid_confirm` after a retry already reached `ACTIVE`, a stale `page_next`
after the list changed page count, and a stale `disable` on an already-`OFF` campaign
(redraws S0, still a no-op).

---

## Cancel

**Fixes:** confirm when draft loss possible; not Back; no clearing durable snapshot before it exists.

Every draft screen's `Отмена` opens the same shaped sub-dialog (S1 example shown above);
`cancel_confirm_yes` resolves per contract §8's rule (no prior durable value → abort
attempt to `OFF`, nothing to clear; prior durable value exists, i.e. S1b only → discard
only the edit, keep the existing confirmed value and running timer untouched).
`cancel_confirm_no` always just closes the sub-dialog and redraws the original screen
with the draft intact — identical in effect to not having pressed Cancel at all.

---

## Screens/transitions inventory (for CONTROL evidence)

| ID | Screen | Draft | Paginated | Backend mode |
|---|---|---|---|---|
| S0 | Entry/instruction | No | No | `OFF` |
| S1 | Keyword-set confirm | Yes | Yes | `PENDING_SETUP` |
| S1b | Keyword-set edit during WARM_UP | Yes | Yes | `PENDING_SETUP` |
| S2 | WARM_UP duration config | Yes | No | `PENDING_SETUP` |
| S3 | WARM_UP progress | No | No | `PENDING_SETUP` |
| W3-propose | Fact vs proposed TP | Yes | Yes | `PENDING_SETUP` |
| W3-confirmed | Confirmed TP (read-only) | No | Yes | `PENDING_SETUP` |
| A1 | Auto participation confirm | Yes | No | `PENDING_SETUP` |
| A2 | Auto bid confirm | Yes | No | `PENDING_SETUP` |
| P1 | PENDING intent recorded / syncing | No | No | `PENDING_SETUP` |
| P2 | Sync partial (recoverable) | No | No | `PENDING_SETUP` |
| H1 | Active hold (read-only) | No | Yes (optional detail) | `ACTIVE` |

Full transition table: `telegram-ux-contract.md` §4.

## Back / Cancel availability table (for CONTROL evidence)

| Screen | Back | Cancel | Cancel resolution |
|---|---|---|---|
| S0 | navigation only (no draft) | not offered | n/a |
| S1 | preserves keyword-toggle draft | offered | no prior durable value → abort to `OFF`, nothing cleared |
| S1b | preserves keyword-toggle draft | offered | prior durable value exists → discard edit only, keep confirmed set + timer |
| S2 | preserves duration draft | offered | no prior durable value → abort to `OFF` |
| S3 | navigation only (no draft) | **not offered** (EXIT only) | n/a |
| W3-propose | preserves per-keyword review draft | offered | no prior durable value → abort to `OFF` |
| W3-confirmed | navigation only (read-only, resolves here from later screens too) | not offered | n/a |
| A1 | preserves participation draft | offered | no prior durable value → abort to `OFF` |
| A2 | preserves bid draft | offered | no prior durable value → abort to `OFF` |
| P1 | navigation only | not offered (EXIT unavailable here too, first sync in flight) | n/a |
| P2 | navigation only | **not offered** (EXIT only) | n/a |
| H1 | navigation only | **not offered** (EXIT only) | n/a |

## Stale-callback protection summary (for CONTROL evidence)

- Every callback on every screen carries a `revision` (pre-generation) or `generation`
  (P1/P2/H1) token.
- Every handler reloads current durable/draft state fresh and compares before applying
  any effect (fail-closed: mismatch ⇒ no-op).
- On mismatch: reject, redraw the *actual current* screen (which may differ from the
  screen the stale callback was sent from), non-alarming toast, WARNING-level log with
  `adv_id` + action id + expected/received token + current phase, no internal
  identifiers leaked to the user.
- Uniformly applied to every action in contract §6, including EXIT/`disable` and page
  navigation.

## Applies to / Related

- `openspec/changes/card-ab-hold-mode/ux/telegram-ux-contract.md` (defines every
  invariant illustrated above)
- `openspec/changes/card-ab-hold-mode/specs/card-ab-hold-mode/spec.md`
- `openspec/changes/card-ab-hold-mode/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md`
- `openspec/changes/card-ab-hold-mode/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md`
- `openspec/changes/card-ab-hold-mode/tasks.md` §19–§25 (implementation, still blocked on
  owner authorization; this storyboard does not unblock it)
- `openspec/policies/telegram_bot_api_limits.md` (payload-limit tests are an
  implementation-time obligation for every screen above, not satisfied by this document)
