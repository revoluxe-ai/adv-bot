# Decision: A/B Hold Epoch Lifecycle And Generation Ownership

## Status

Proposed

## Context

Владельческое обновление продуктового флоу A/B Hold (owner-approved product requirements; **не** `REQ-AB-HOLD-BUDGET-SAFETY-001` и не параллельная финансовая safety-модель) вводит durable pre-epoch стадию WARM_UP и переносит фиксацию целевых позиций / Auto-параметров с момента ENTER на момент явных подтверждений пользователя после прогрева. Существующая `card-ab-hold-write-path-ownership/decision.md` описывает setup/hold write-path, allowed-set snapshot и stats freshness, но **не** отвечает: где живёт длительность и таймер WARM_UP, что такое «эпоха» подтверждённых epoch-параметров, какой счётчик (generation) идентифицирует конкретный подтверждённый набор параметров, кто владеет порядком «durable PENDING intent → WB sync → ACTIVE», как ведёт себя partial sync, и почему retry не должен пересчитывать TP/Auto bid или продвигать generation. Без reusable правила ownership для этого lifecycle любой ad hoc «if» в handler/runner снова смешает WARM_UP-таймер, подтверждение и WB-синхронизацию и повторит прежний класс проблем (ACTIVE без durable snapshot, TP, зафиксированный на «грязной» стате входа).

Существующая реализация `card-ab-hold-mode` (allowed-set freeze минус-фраз, Excel removal, V3-only gate, idempotent Enable, PENDING_SETUP liveness §14) остаётся в силе как уже применённый механизм enforcement/UI-гейтов; этот decision добавляет **новый слой** над ним — WARM_UP → confirm → durable PENDING → WB sync → ACTIVE, — не отменяя existing freshness/V3/shared-defaults/Excel-removal инвариантов.

## Decision

WARM_UP, эпоха (epoch) и generation — durable lifecycle-примитивы A/B Hold, принадлежащие выделенному A/B Hold epoch/setup write-path (тот же owner, что setup/hold entrypoints из `card-ab-hold-write-path-ownership`), а не ordinary V3 preamble, не Telegram-хендлеру напрямую и не shared defaults.

1. **WARM_UP — отдельная durable pre-epoch стадия.** Явное подтверждение набора ключей пользователем вводит кампанию в WARM_UP в состоянии **конфигурации длительности** (Telegram S2): durable keyword-set фиксируется, `warmup_started_at` MUST оставаться NULL, таймер MUST NOT стартовать. Таймер WARM_UP стартует только при подтверждении длительности (Telegram S2 → S3): write-path persist'ит duration (≥24ч) и выставляет `warmup_started_at`. Длительность WARM_UP — durable параметр эпохи: default = 24 часа, минимум = 24 часа. Пользователь MAY увеличить длительность на S2 до старта таймера; пользователь MUST NOT уменьшить её ниже 24 часов ни для текущей, ни для будущей эпохи той же кампании.
2. **Инварианты WARM_UP:** во время WARM_UP MUST NOT происходить автоматическое добавление ключей и автоматический возврат исключённых ключей; safety-исключение (защитное исключение по причинам, не связанным с экспериментом, например перерасход) Allowed. Целевая позиция (target place) MUST NOT быть зафиксирована во время WARM_UP — TP не существует как подтверждённый параметр до отдельного подтверждения после WARM_UP.
3. **Пороги показов — не длительность WARM_UP.** Существующие пороги «≥100 показов на ключ» (eligibility ключа) и «≥1000 суммарных показов кампании» (soft-gate объёма на enable) сохраняют текущую семантику из `card-ab-hold-write-path-ownership` (§2c, §3) как отдельные, независимые от длительности WARM_UP условия; они не заменяют и не изменяют 24-часовой таймер.
4. **Ручное изменение набора ключей во время WARM_UP завершает текущий WARM_UP-таймер и возвращает к конфигурации длительности.** Изменение состава подтверждённого набора ключей во время running WARM_UP MUST завершать текущий таймер (`warmup_started_at` cleared), MUST вернуть UI/phase к duration-configuration (S2) и MUST стартовать новый таймер только после повторного `warmup_duration_confirm` (новый отсчёт, снова ≥ выбранной длительности, не короче 24 часов). Остаток прежнего таймера MUST NOT переноситься. Такое изменение относится к той же попытке эпохи (epoch attempt) до момента, когда пользователь пройдёт полный цикл подтверждений TP + Auto заново для нового набора.
5. **Эпоха (epoch) и generation.** Одна эпоха — это один согласованный набор подтверждённых epoch-параметров (подтверждённый набор ключей + подтверждённые целевые позиции + подтверждённое участие Auto + подтверждённая ставка Auto), однажды доведённый до WB. `generation` — монотонный идентификатор конкретной подтверждённой эпохи, присваиваемый в момент завершения полного цикла подтверждений (после Auto bid confirm, перед записью durable PENDING intent). Generation принадлежит A/B Hold epoch write-path; UI/handler не присваивает и не инкрементирует generation напрямую — он читает его из durable записи, созданной write-path'ом.
6. **Durable PENDING intent MUST предшествовать любой WB-мутации.** После завершения всех подтверждений (keyword-set, TP, Auto participation, Auto bid) write-path MUST persist durable «PENDING intent» (сгенерированные параметры эпохи + generation) в PostgreSQL **до** первой попытки записи в WB для этой эпохи. WB MUST NOT мутироваться на основании эфемерного (Redis-only, in-memory, ещё не закоммиченного) намерения.
7. **Partial sync — recoverable, не ACTIVE.** Если WB-синхронизация для generation завершилась частично (часть ключей/бид синхронизированы, часть — нет, включая обрыв процесса/сети), кампания MUST оставаться в non-ACTIVE состоянии (например, PENDING) с сохранённым durable generation и confirmed-параметрами. ACTIVE MUST достигаться только после того, как WB-синхронизация для этой generation признана полностью успешной.
8. **Retry — тот же generation, те же параметры, без пересчёта, без новой эпохи.** Повторная попытка WB-синхронизации после partial/failed sync MUST переиспользовать тот же generation и те же confirmed-параметры (keyword-set, TP, Auto participation, Auto bid) без пересчёта. Retry MUST NOT пересчитывать целевые позиции, MUST NOT пересчитывать/переподтверждать Auto bid, и MUST NOT создавать новую эпоху или продвигать generation. Продвижение generation возможно только через новый полный цикл подтверждений (новая эпоха), например после EXIT → новый ENTER, либо после ручного изменения набора ключей, которое по правилу 4 явно начинает новую попытку эпохи с последующим повторным полным подтверждением.
9. **Дрейф позиции не переоткрывает подтверждение.** Естественное изменение фактической позиции ключа в WB после подтверждения TP MUST NOT само по себе аннулировать generation, MUST NOT запускать новый цикл подтверждений и MUST NOT приводить к автоматическому пересчёту целевой позиции этой generation (детали инварианта immutable TP — в `ab-hold-confirmed-epoch-parameters-sot`).
10. **Owner layer.** Таймер/состояние WARM_UP, generation-нумерация и порядок PENDING→WB→ACTIVE принадлежат A/B Hold epoch/setup write-path (shop-runner setup pipeline + durable PG epoch/generation поля), рядом с существующими setup/hold entrypoints `card-ab-hold-write-path-ownership`. Telegram-хендлеры только инициируют переходы (подтверждение/keyword-set change/EXIT) и читают durable статус; они не хранят generation и не пересчитывают WARM_UP-таймер локально.
11. **Legacy MVP-1 auto-ACTIVE MUST be gated.** Существующий путь `process_ab_setup` → `apply_ab_hold_setup_mutations` → `ACTIVE` (и TP-write на ENTER PASS в `setup_apply`) MUST NOT выполняться параллельно с owner WARM_UP/confirm/PENDING-intent флоу. До готовности epoch sync path setup-тик MUST NOT форсить ACTIVE и MUST NOT фиксировать TP; phase-gate — `tasks.md` §18.4. Planned PG columns — `tasks.md` §19.5 / §22.5 (`card_ab_hold_phase`, warmup timer fields, `card_ab_hold_generation`, `card_ab_hold_pending_intent_json`, `card_ab_hold_sync_status`, `card_ab_hold_wb_sync_idempotency_key`, confirmed-* columns).
12. **PostgreSQL idempotency, uniqueness, and row locking (AdvSetting SoT).** `AdvSetting` is 1:1 with `adv_id` (PK). Epoch lifecycle fields live on that single row; at most one non-terminal generation is stored per row; `card_ab_hold_mode=ACTIVE` is Allowed only when `card_ab_hold_sync_status=complete` and the stored generation is the sole active epoch for that row (transactional invariant: `mode=ACTIVE` implies sync complete for that generation only — no silent second ACTIVE).
    - **Idempotency key:** `card_ab_hold_wb_sync_idempotency_key` TEXT NOT NULL when durable PENDING intent exists; format `{adv_id}:{generation}` (example `12345:3`). Same generation + same confirmed params MUST reuse the same key on retry.
    - **Generation:** `card_ab_hold_generation` INT monotonic; new generation created atomically in one PG transaction together with intent JSON + idempotency key + `card_ab_hold_phase=PENDING_INTENT` (or equivalent phase). Duplicate intent submission MUST NOT create a new epoch (`ON CONFLICT` / transactional no-op when idempotency key already present for the same generation).
    - **Confirmed params immutable on retry:** retry reuses same generation, same idempotency key, same confirmed-parameter snapshot; no TP/Auto bid recalculation.
    - **Process restart:** shop-runner recovery reads the same generation and idempotency key from durable PG fields — no in-memory-only epoch state.
    - **Locking:** before generation bump, intent write, or `card_ab_hold_sync_status` transition, epoch write-path MUST `SELECT … FOR UPDATE` the `AdvSetting` row.
    - **Uniqueness conflict:** on idempotency/generation conflict, abort the transaction; leave prior generation intact; surface actionable status to UI; MUST NOT silently create a second ACTIVE or advance generation.
    - **Migration defaults:** new columns with NULL / 0 / `none` defaults MUST NOT activate the new lifecycle on existing rows (see §13 / `design.md` Migration Plan).
13. **Legacy / in-flight migration (no auto-conversion).** Existing MVP-1 campaigns (`card_ab_hold_phase` NULL, mode `PENDING_SETUP` or `ACTIVE`) MUST NOT auto-convert to epoch-managed generation on migration or restart. NULL `card_ab_hold_phase` means legacy-MVP-1 semantics until EXIT or controlled re-enter under fail-closed feature flag (§25). New epoch flow only via explicit owner entry. Already ACTIVE legacy continues legacy behavior until EXIT (prefer EXIT-only for MVP). Automatic backfill of confirmed parameters FORBIDDEN. Rollback migration MUST NOT destroy legacy mode / allowed-set snapshot / degraded fields. Concrete compatibility tests — `tasks.md` §18.5.

## Applies to

- Capability `card-ab-hold-mode`: WARM_UP-стадия, epoch/generation модель, durable PENDING→WB→ACTIVE порядок, retry-поведение.
- A/B Hold setup/ENTER write-path (тот же owner, что в `card-ab-hold-write-path-ownership`).
- Durable PG-поля эпохи/generation/WARM_UP-таймера кампании.
- WB-синхронизация confirmed-параметров эпохи и её retry-путь.
- Telegram-хендлеры, инициирующие keyword-set confirm, TP/Auto confirm, EXIT (только как triggers, не как SoT lifecycle).

## Allowed

- Durable WARM_UP-таймер per эпоха с default/min = 24 часа; пользовательское увеличение длительности.
- Safety-исключение ключей во время WARM_UP по причинам, не связанным с ростом/оптимизацией (например, защита от перерасхода).
- Сброс WARM_UP-таймера на новый отсчёт при ручном изменении набора ключей во время WARM_UP.
- Одна durable запись PENDING intent (parameters + generation) перед первой WB-мутацией эпохи.
- Non-ACTIVE (например, PENDING) состояние с сохранённым generation при partial/failed WB sync.
- Retry WB-синхронизации той же generation с тем же набором confirmed-параметров без пересчёта.
- Новая эпоха/generation только после нового полного цикла подтверждений (новый ENTER после EXIT, либо перезапуск подтверждений после изменения набора ключей).

## Forbidden

- Уменьшение длительности WARM_UP ниже 24 часов пользователем или системой.
- Автоматическое добавление новых ключей или автоматический возврат исключённых ключей во время WARM_UP.
- Фиксация целевой позиции (target place) как подтверждённого параметра во время WARM_UP, до отдельного TP confirm.
- Трактовать пороги «100 показов/ключ» и «1000 показов кампании» как длительность или замену WARM_UP-таймера.
- Любая WB-мутация confirmed-параметров эпохи до записи durable PENDING intent в PostgreSQL.
- Перевод кампании в ACTIVE при частично завершённой WB-синхронизации данной generation.
- Retry, который пересчитывает целевые позиции, пересчитывает/переподтверждает Auto bid, создаёт новую эпоху или продвигает generation.
- Автоматическое аннулирование generation или запуск нового цикла подтверждений из-за обычного дрейфа фактической позиции ключа.
- Присваивание/инкремент generation напрямую в Telegram-хендлере или в shared defaults transition-helper в обход A/B Hold epoch write-path.
- Legacy `process_ab_setup` auto-ACTIVE или ENTER TP-write, обходящие WARM_UP / confirms / durable PENDING intent.
- Duplicate PENDING intent creating a new generation or second ACTIVE for the same `adv_id`.
- WB sync or generation bump without `SELECT … FOR UPDATE` on the owning `AdvSetting` row.
- Migration defaults or process restart auto-converting legacy MVP-1 rows to epoch-managed generation.
- Automatic backfill of confirmed epoch parameters for legacy in-flight campaigns.

## Examples

Good:

- Пользователь подтверждает набор ключей → S2 (duration config, `warmup_started_at` NULL) → подтверждает длительность (default 24ч или увеличенную) → таймер стартует (S3) → по истечении показывается факт-позиция/proposed TP → пользователь подтверждает TP → подтверждает участие Auto → подтверждает ставку Auto → write-path пишет durable PENDING intent с новым generation → одна попытка WB sync → успех → ACTIVE.
- WB sync для generation N частично падает (сеть) → кампания остаётся PENDING с тем же generation N и тем же confirmed набором → следующий тик повторяет sync тех же параметров без пересчёта → успех → ACTIVE.
- Пользователь во время running WARM_UP убирает один ключ из набора → таймер завершается, UI возвращается на S2 → после повторного confirm длительности таймер начинается заново (снова ≥24ч); TP/Auto confirm ещё не пройдены для нового набора.

Bad:

- Keyword-set confirm сразу пишет `warmup_started_at=now` и пропускает S2, делая увеличение длительности недостижимым на happy path.
- WB-запись целевых позиций выполняется сразу после первого подтверждения ключевого набора, до окончания WARM_UP.
- Retry после partial sync пересчитывает target place по новой фактической позиции или запрашивает повторное подтверждение Auto bid.
- Кампания помечается ACTIVE, пока WB ещё не подтвердил применение всех confirmed ключей/TP/Auto bid для текущей generation.
- Пользователь уменьшает WARM_UP до 2 часов через Telegram-хендлер, и это принимается без блокировки.
- Естественный дрейф фактической позиции ключа в ACTIVE автоматически помечает generation как «требует нового подтверждения».

## Related specs

- `openspec/changes/card-ab-hold-mode/specs/card-ab-hold-mode/spec.md`

## Related changes

- `openspec/changes/card-ab-hold-mode/`

## Review checklist

- [x] existing decisions searched (`card-ab-hold-write-path-ownership`, `mode-defaults-policy-ownership`)
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing for WARM_UP/epoch/generation lifecycle ownership
- [ ] implementation layer matches decision (не применяется в этом PLAN_ONLY обновлении; apply заблокирован до owner-авторизации, см. `tasks.md`)
