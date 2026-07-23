# Decision: A/B Hold Confirmed Epoch Parameters Source Of Truth

## Status

Proposed

## Context

Обновлённый продуктовый флоу требует, чтобы ключевой набор, целевые позиции (target place), участие Auto и ставка Auto подтверждались пользователем **явно и раздельно**, а не выводились автоматически из статы на момент ENTER. Прежняя модель (`card-ab-hold-write-path-ownership` §3 «ENTER criterion») фиксировала целевую позицию как «текущая фактическая позиция» синхронно с автоматической PASS/FAIL классификацией ключа — без отдельного WARM_UP, без отображения «факт vs предложение» и без явного подтверждения Auto. Это входит в противоречие с owner-approved требованиями: тихая авто-классификация ENTER и авто-фиксация TP без явных подтверждений keyword+TP+Auto — Forbidden.

Кроме того, отображение позиции ключа исторически было одним числовым полем. Новое требование обязывает различать **факт (текущая наблюдаемая позиция)** и **target place (подтверждённый параметр эпохи)** как отдельные семантические поля, даже если их числовые значения могут совпасть после округления/clamping. Без reusable decision для source-of-truth (SoT) подтверждённых epoch-параметров любая реализация рискует повторно слить факт и target в одно поле или позволить фоновому пересчёту молча подменить подтверждённый пользователем параметр.

## Decision

Подтверждённые epoch-параметры (confirmed keyword set, confirmed target places, confirmed Auto participation, confirmed Auto bid) — durable source of truth эпохи A/B Hold, отдельный от live/факт-состояния WB и отдельный от allowed-set/минус-механизма enforcement из `card-ab-hold-write-path-ownership` §8.

1. **Confirmed keyword set.** Подтверждённый пользователем после явного действия (не авто-классификация по стате) набор ключей эпохи — durable PG SoT. Существующий allowed-set snapshot mechanism (`card-ab-hold-write-path-ownership` §8) остаётся действующим **enforcement**-слоем (минус-фразы как derived-исключение не-разрешённых фраз); подтверждённый набор ключей этой эпохи — вход, который наполняет/заменяет содержимое allowed-set snapshot для этой эпохи, а не параллельная несогласованная копия. Пороги «≥100 показов/ключ» продолжают определять, какие ключи предлагаются пользователю как eligible-кандидаты для подтверждения (см. `ab-hold-epoch-lifecycle-and-generation-ownership` §3); финальный подтверждённый набор — это то, что явно выбрал пользователь из eligible-кандидатов, а не автоматический результат классификации.
2. **Факт-позиция и target place — раздельные семантические поля.** Факт (текущая наблюдаемая позиция ключа в WB) — read-model, обновляется при каждом отображении, не хранится как подтверждённый параметр эпохи. Target place (целевая позиция) — write-model / подтверждённый параметр эпохи, предлагается функцией `ab_hold_target_place_from_keyword(position)` от факт-позиции, наблюдаемой после окончания WARM_UP, и становится durable только после явного подтверждения пользователем. Экран и любое сообщение MUST отображать оба поля раздельно («ключ → факт-позиция → предложенное target place»); совпадение их числовых значений после округления/clamping допустимо, но MUST NOT становиться причиной слияния полей в одно значение или одно хранимое поле.
3. **Immutable target place внутри эпохи.** После подтверждения target place становится durable и immutable для текущей generation/эпохи. ENTER/setup-тик MUST NOT пересчитывать confirmed target place. Обычный дрейф факт-позиции после подтверждения MUST NOT переоткрывать подтверждение и MUST NOT инициировать пересчёт target place этой эпохи (см. `ab-hold-epoch-lifecycle-and-generation-ownership` §9). Изменение target place возможно только через новую эпоху (EXIT → новый ENTER → новый полный цикл подтверждений).
4. **Keyword bidder — только holder подтверждённых target places.** Биддер во время ACTIVE использует исключительно подтверждённые (confirmed, durable) target places этой эпохи как цель ставок; биддер MUST NOT самостоятельно добавлять или возвращать ключи и MUST NOT изменять target place — эти действия принадлежат исключительно write-path подтверждения новой эпохи.
5. **Auto participation confirm — отдельное подтверждение.** Участие типа кампании Auto в текущей эпохе A/B Hold MUST подтверждаться явным пользовательским действием, отдельным от подтверждения Search keyword set/TP. Подтверждение Auto participation MUST NOT подразумеваться автоматически из подтверждения ключевого набора Search.
6. **Auto bid confirm — отдельное явное подтверждение.** Значение/стратегия ставки Auto на эпоху MUST подтверждаться отдельным явным действием пользователя, независимым от Auto participation confirm и от Search TP confirm. Confirmed Auto bid — durable параметр эпохи, наравне с confirmed target places.
7. **Auto bid мутаторы заморожены в ACTIVE.** После перехода в ACTIVE ordinary auto-update мутаторы ставки Auto MUST NOT изменять подтверждённую ставку Auto этой эпохи. **В scope freeze явно входят:** `AutoResetBidService.ensure_auto_bids_minimum` (shop-runner `manager.py`) и прочие Auto CPM writers того же тика; manual Telegram `change_auto_bid` при ACTIVE — либо block+explain, либо только через EXIT+новую эпоху. Изменение confirmed Auto bid возможно только через EXIT и новую эпоху (новый полный цикл подтверждений) либо иным явным owned-путём, эквивалентным EXIT.
8. **Owner layer.** Хранение и владение подтверждёнными epoch-параметрами принадлежит A/B Hold confirmation write-path (Telegram confirm-хендлеры → durable PG запись, тот же owner, что epoch/generation lifecycle из `ab-hold-epoch-lifecycle-and-generation-ownership`). Ordinary Search/Auto auto-updaters и display/formatting-слой не владеют confirmation state: display-слой только читает факт и confirmed target place раздельно, а не решает, что подтверждено.

## Applies to

- Capability `card-ab-hold-mode`: подтверждение набора ключей, TP confirm, Auto participation confirm, Auto bid confirm.
- Отображение «ключ → факт-позиция → предложенное target place» на любом экране/сообщении A/B Hold.
- Keyword bidder path во время ACTIVE (holder confirmed target places).
- Ordinary Auto bid auto-update mutators при ACTIVE A/B Hold (включая `AutoResetBidService.ensure_auto_bids_minimum`).
- Существующий allowed-set snapshot mechanism (`card-ab-hold-write-path-ownership` §8) как enforcement-слой, наполняемый подтверждённым набором ключей эпохи.

## Allowed

- Показ факт-позиции и предложенного target place (`ab_hold_target_place_from_keyword(position)`) как двух отдельных полей на одном экране/сообщении.
- Подтверждение target place пользователем после окончания WARM_UP, до начала WB-синхронизации эпохи.
- Раздельные экраны/шаги подтверждения: keyword set → TP → Auto participation → Auto bid.
- Биддер, удерживающий ставки к подтверждённым target places без их изменения.
- Наполнение существующего allowed-set snapshot подтверждённым набором ключей эпохи.
- Новый цикл подтверждений (новая эпоха) как единственный путь изменить confirmed target place / confirmed Auto bid после ACTIVE.

## Forbidden

- Автоматическая (без явного подтверждения) фиксация target place по результату классификации ключа на ENTER.
- Слияние факт-позиции и target place в одно отображаемое или хранимое значение/поле.
- Пересчёт confirmed target place на ENTER, на retry WB-синхронизации или из-за обычного дрейфа факт-позиции.
- Подразумевание Auto participation confirm из Search keyword set confirm (или наоборот).
- Изменение confirmed Auto bid ordinary auto-update мутатором во время ACTIVE (в т.ч. `AutoResetBidService.ensure_auto_bids_minimum`).
- Добавление/возврат ключей биддером или изменение target place биддером напрямую.
- Хранение confirmed epoch-параметров только в display/formatting-слое или только в Redis без durable PG SoT.

## Examples

Good:

- Экран после WARM_UP показывает: `Ключ X → факт: 14 → предложено: 12`; пользователь подтверждает `12` как target place; значение становится durable и не меняется до новой эпохи.
- Пользователь отдельно подтверждает «Auto участвует в тесте» и отдельно подтверждает конкретную ставку Auto для эпохи.
- В ACTIVE факт-позиция ключа сместилась на 18, однако биддер продолжает целиться в подтверждённые 12 без переоткрытия подтверждения.

Bad:

- Показ единственного числа «Позиция: 12» без указания, что это факт или предложение.
- ENTER-тик молча пересчитывает и перезаписывает уже подтверждённый target place на новую фактическую позицию.
- Подтверждение keyword set автоматически трактуется как подтверждение участия Auto.
- Ordinary auto-update ставок меняет подтверждённую ставку Auto, пока кампания ACTIVE (пример: `AutoResetBidService.ensure_auto_bids_minimum` без ab_hold guard).

## Related specs

- `openspec/changes/card-ab-hold-mode/specs/card-ab-hold-mode/spec.md`

## Related changes

- `openspec/changes/card-ab-hold-mode/`

## Review checklist

- [x] existing decisions searched (`card-ab-hold-write-path-ownership`, `ab-hold-epoch-lifecycle-and-generation-ownership`, `mode-defaults-policy-ownership`)
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing for confirmed-epoch-parameters SoT and факт/target place separation
- [ ] implementation layer matches decision (не применяется в этом PLAN_ONLY обновлении; apply заблокирован до owner-авторизации, см. `tasks.md`)
