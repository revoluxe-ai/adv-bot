# Decision: Forward-only rollout переходов схемы и данных

## Status

Proposed

## Context

Landing feature-ветки может затрагивать migration, которая одновременно
подготавливает существующие данные и усиливает ограничение схемы. Контракт
`openspec/decisions/alembic-forward-only-head-convergence/decision.md`
разрешает операции схемы и данных только вне merge-ревизии, если её цель —
схождение Alembic topology. Он не определяет, как безопасно выбирать между
исправлением remote feature migration и новой forward-only repair migration,
когда доказательство применения в базе отсутствует.

В change `safe-prod-pg-migrations` уже предложена модель DDL через migration
Job и Expand–Contract, но она ещё не является accepted decision. До
implementation-ready нужен reusable invariant для branch landing и
миграционного слоя.

## Decision

Переходы, которые меняют и данные, и обязательность схемы, принадлежат
выделенному forward-only migration rollout, а не topology-only merge path.
Landing readiness MUST разделять:

1. доказательство того, что revision опубликована или применена;
2. выбор между исправлением ещё не применённой revision и добавлением новой
   forward repair/compatibility revision;
3. проверку backfill, nullable transition и повторного запуска.

Если применение revision вне текущей ветки доказано, существующая история
считается immutable и исправление выполняется новой forward revision. Если
применение не доказано, исправление remote feature revision допустимо только
до landing, после явной проверки provenance и повторной проверки Alembic graph.
Одна лишь достижимость из remote branch не считается доказательством применения
в базе.

Production schema/data writes MUST выполняться только через утверждённый
migration write-path. Этот change может включать release gate и фиксировать
результат approved production action, но local landing verification,
application runtime и developer shell не выполняют production DB actions.
Readiness не заменяет отдельное deployment/database evidence.

Legacy field backfills MUST use an explicit domain classifier rather than a
runtime fallback. For `auto_update_minus_phrases`, the classifier for this
rollout is `bot_active` and MUST apply **only to NULL** legacy rows: NULL +
active → `true`, NULL + inactive → `false`. Already non-NULL values (including
post-landing UI toggles) MUST NOT be rewritten. The Job MAY run whenever NULLs
remain (fill-on-NULL); with no NULLs the UPDATE is a no-op. After NULLs are
filled, the rollout sets DEFAULT `false` and NOT NULL. New records receive
`false` through declarative defaults. A persistent runtime `None → true`
interpretation is not a valid replacement for the data transition. Longer-term
preferred end-state: keep NOT NULL in prod and remove this backfill Job path
once NULL legacy is gone.

Migration rollout MUST preserve the effective behavior of existing paid and
free clients. A default or backfill that enables a previously disabled
automation flag, changes billing, changes WB writes, or changes campaign
lifecycle is non-neutral behavior and requires an explicit accepted product
decision plus rollout evidence; it MUST NOT be treated as a routine schema
default.

## Applies to

- migration с backfill существующих строк;
- переходы `nullable`/`NOT NULL` и иные поэтапные schema constraints;
- выбор rewrite-before-publication против forward repair;
- compatibility of existing paid/free client cohorts across migration rollout;
- branch landing gates, которые проверяют migration safety и provenance;
- дальнейшие изменения, где remote publication и database application могут
  быть подтверждены разными источниками.

## Allowed

- Делать idempotent или безопасно повторяемый backfill частью выделенной
  forward migration при наличии data-safety proof.
- Применять для legacy **NULL** records явный classifier, зафиксированный до
  rollout; для текущего поля это `NULL ∧ bot_active=True → true` и
  `NULL ∧ bot_active=False → false`; non-NULL не трогать при retry.
- Оставлять новые записи с declarative default `false` и завершать переход
  без постоянного nullable/runtime compatibility fallback.
- Собирать before/after baseline для существующих клиентских cohort и проверять,
  что effective automation, billing, WB writes и campaign lifecycle не drift-ят.
- Выполнять намеренное изменение поведения существующих клиентов только при
  отдельном принятом product decision, явной rollout semantics и recovery plan.
- Использовать Expand–Contract для постепенного усиления schema constraint.
- Добавлять новую repair migration после доказанного применения исходной
  revision.
- Исправлять ещё не применённую feature revision до landing при зафиксированной
  provenance evidence и сохранении единственного корректного head.
- Проверять topology-only merge отдельно от schema/data migration.

## Forbidden

- Переписывать revision после доказанного применения вне текущей ветки.
- Добавлять schema/data operations в merge revision, цель которой ограничена
  схождением head.
- Считать remote branch reachability доказательством database application.
- Молча включать новую automation для существующих клиентов через broad default
  или backfill.
- Использовать broad `NULL → true` без classifier и affected-record preview.
- Трактовать `None` как постоянно включённую automation в application runtime.
- Называть migration безопасной только потому, что graph и static tests зелёные,
  если client compatibility baseline отсутствует.
- Выполнять production migration из application runtime, локального developer
  shell или landing verification.
- Смешивать migration repair с изменением OPSX command contracts или
  unrelated branch cleanup.

## Examples

- Хорошо: provenance доказала применение исходной revision; добавляется
  отдельная forward repair migration, а исходная история не меняется.
- Хорошо: before/after baseline показывает отсутствие drift для paid/free
  клиентов; migration меняет только schema state, явно заявленный в decision.
- Плохо: backfill `NULL → true` молча включает новую automation у всех
  существующих клиентов без отдельного product decision и rollout evidence.
- Хорошо: одноразовый idempotent release backfill применяет
  `bot_active=True → true`, `bot_active=False → false`, после preview и
  compatibility baseline.
- Плохо: runtime property превращает `None` в `true`, чтобы обойти migration
  safety gate или отсутствие data-transition evidence.
- Хорошо: provenance не доказана; feature revision корректируется до landing,
  затем повторно проходят graph, safety и data-transition checks.
- Плохо: доступная в remote ветке revision переписывается после применения в
  базе без repair revision.
- Плохо: topology-only merge revision выполняет backfill или меняет constraint.

## Related specs

- `openspec/specs/alembic-head-convergence/spec.md`
- `openspec/changes/land-free-bot-rebase-into-stage/specs/stage-landing-readiness/spec.md`

## Related changes

- `openspec/changes/land-free-bot-rebase-into-stage`
- `openspec/changes/safe-prod-pg-migrations`

## Review checklist

- [x] existing decisions searched
- [x] relevant accepted decision cited
- [x] new decision proposed because accepted decision for data-transition
      rollout and provenance choice is missing
- [x] implementation layer matches this decision
- [x] provenance evidence is attached before choosing rewrite or repair
- [x] existing paid/free client compatibility baseline contract and final
      local review are attached; stage/prod representative receipt remains
      a later release gate
- [x] any intentional behavior change has change-local Owner confirmation
- [x] migration Job/write-path is Owner-confirmed for this change; reusable
      decision remains Proposed until its acceptance/archive flow
- [x] legacy classifier and one-time idempotent backfill are explicitly
      approved for this change

## Change-local Owner confirmation

On 2026-08-17 the Owner accepted for `land-free-bot-rebase-into-stage`:

- `bot_active=True → auto_update_minus_phrases=True`;
- `bot_active=False → auto_update_minus_phrases=False`;
- new records default to `False`;
- the approved migration Job owns the one-time idempotent backfill;
- Alembic `upgrade()` must not contain `op.execute()` or `op.alter_column()`;
- persistent `None → True` fallback is forbidden;
- production requires migration/deployment receipts and a compatibility
  baseline.

This confirmation authorizes the current change only; it does not silently
promote this Proposed artifact to a reusable Accepted architecture decision.
