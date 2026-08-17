## Context

Feature-ветка должна пройти полный release-путь: посадка на копию `stage`,
stage deployment, production migration/UI rollout и post-deploy verification.
Статическая проверка migration safety строит цепочку относительно merge-base со
`stage`, включая staged и unstaged изменения, и запрещает в `upgrade()` вызовы
`op.execute()` и `op.alter_column()`.

Текущая feature migration смешивает schema transition, backfill существующих
строк и усиление обязательности поля. Это отражает нужную бизнес-семантику не
полностью и не проходит текущий safety-контракт. Backfill должен быть
одноразовым, классифицировать legacy records по `bot_active` и выполняться
через утверждённый migration Job, а не через runtime fallback. Отдельная
topology-only merge revision должна оставаться без schema/data operations.

Поэтому landing рассматривается как evidence-gated процесс с двумя
независимыми осями:

- корректность migration graph и единственная head;
- безопасность и подтверждённая семантика schema/data transition.

Remote branch reachability уже является evidence существования revision в
истории веток, но не является evidence её применения в базе.

## Goals / Non-Goals

**Goals:**

- Определить один воспроизводимый branch-to-base snapshot для всех проверок.
- Не ослаблять safety gate только для получения зелёного результата.
- Разделить topology-only merge migration и migration с data transition.
- Зафиксировать evidence-gated выбор между rewrite ещё не применённой feature
  revision и новой forward repair revision.
- Проверить graph, data transition, повторный запуск и отсутствие влияния на
  paid/free product behavior вне текущего diff.
- Доказать compatibility existing paid/free clients до выдачи readiness.
- Провести stage deployment с обновлённым интерфейсом и проверить его до
  production rollout.
- Провести production migration/UI rollout через approved release path и
  сохранить deployment/database receipts.
- Выполнить post-deploy compatibility verification для существующих paid/free
  клиентов.
- Подготовить проверяемый release evidence package без неутверждённых
  production DB actions.

**Non-Goals:**

- Изменение OPSX command contracts, `.cursor/commands/**` или pipeline
  process surfaces.
- Автоматический commit, push, merge или PR.
- Production DB actions вне approved migration/deployment path.
- Доказательство применения migration без database/deployment receipt.
- Изменение accepted архитектурного решения о forward-only convergence.
- Ослабление safety-теста посредством blanket allowlist для опасных операций.
- Новая продуктовая логика для free bot или paid automation core.

## Architecture Decision References

- `openspec/decisions/alembic-forward-only-head-convergence/decision.md`
  (Accepted): опубликованная Alembic history immutable; несколько head
  сходятся новой forward-only merge revision без schema/data operations.
- `openspec/specs/alembic-head-convergence/spec.md`: контракт единственной head
  и focused regression replay.
- `openspec/changes/land-free-bot-rebase-into-stage/decisions/forward-only-data-migration-rollout/decision.md`
  (Proposed; owner-confirmed for this change): schema/data transition
  выносится в отдельный forward-only rollout, а provenance классифицирует
  rewrite против repair. Promote to reusable Accepted status during archive.
- `openspec/changes/safe-prod-pg-migrations/decisions/DDL_JOB_ONLY.md`
  (Proposed; owner-confirmed for this change): production DDL/data write-path
  через migration Job и Expand–Contract. The source artifact remains Proposed
  until its separate reusable-decision acceptance/archive flow.
- `openspec/changes/safe-prod-pg-migrations/proposal.md`: related change с
  migration Job, CI gates, provenance и dual-baseline requirements.

Owner confirmation for this change (2026-08-17) accepts the classifier,
one-time idempotent Job backfill, schema-only Alembic upgrade, prohibited
runtime fallback, and receipt/baseline requirements. This does not promote
the local or related proposed decisions globally.

## Ownership & Placement

**Owner layer:**

- migration layer владеет schema/data transition и forward revision topology;
- migration safety test владеет статической проверкой опасных upgrade patterns;
- OpenSpec landing verification владеет branch scope, provenance evidence и
  итоговым readiness verdict.

**Allowed layers:**

- Alembic revisions для forward-only schema transition;
- отдельный approved migration Job/write-path для production data/DDL rollout;
- approved stage/production deployment path для последовательного rollout
  schema и обновлённого интерфейса;
- unit/integration tests для graph, safety и data invariants;
- OpenSpec artifacts и release evidence для решения scope, receipts,
  compatibility и rollback.

**Forbidden layers:**

- application startup, runtime handlers и updater logic для schema writes;
- topology-only merge revision для backfill или constraint transition;
- `.cursor/commands/**` для исправления migration semantics;
- production database из local landing verification;
- production schema/data writes из application runtime или developer shell;
- unrelated dirty worktree как часть branch landing verdict.

**Rationale:**

Такое размещение сохраняет границу между миграционной топологией и
изменением данных, отделяет readiness от deployment и соответствует accepted
forward-only decision. Production rollout остаётся `NO_GO`, пока migration
Job/write-path и его application/control baselines не приняты и не проверены.

## Decisions

### 1. Сначала фиксируется snapshot и provenance

Landing checks работают на одном зафиксированном merge-base, commit SHA и
снимке relevant worktree changes. Файлы вне branch-to-base diff не должны
менять verdict.

До выбора migration route собирается provenance matrix:

- revision reachable from remote branch;
- revision reachable from stage/master;
- evidence database application;
- evidence release/deployment receipt.

Недостаток database application evidence не интерпретируется как `APPLIED`.
Если provenance остаётся неизвестной, migration route получает `NO_GO`.

### 2. Safety gate не ослабляется ради текущей migration

Существующий stage-diff safety test остаётся fail-closed. Его запреты на
`op.execute()` и `op.alter_column()` не обходятся переименованием вызова,
динамическим SQL или изменением теста под единственный файл.

Если подтверждённая бизнес-семантика действительно требует data backfill и
последующего constraint transition, implementation должна разделить эти
операции между безопасным schema step и approved migration Job/write-path.
Постоянный `None → true` fallback в application runtime не заменяет
backfill и не считается migration contract.

### 3. Topology merge и feature migration проверяются раздельно

Для topology-only merge revision проверяется отсутствие schema/data operations и
сохранение всех родителей. Для feature migration отдельно проверяются:

- начальное состояние существующих строк;
- ожидаемый backfill;
- default для новых строк;
- переход к `NOT NULL`;
- повторный запуск и частичный сбой;
- отсутствие изменения опубликованной истории.

### 3a. Legacy data classifier и одноразовый backfill

Для существующих записей migration Job применяет один фиксированный classifier:

- `bot_active=True` получает `auto_update_minus_phrases=True`;
- `bot_active=False` получает `auto_update_minus_phrases=False`;
- новые записи получают `False` через declarative defaults.

Backfill запускается один раз как release operation, но обязан быть
идемпотентным для retry. Он начинается с preview affected records и
распределения значений, а после завершения проверяет отсутствие несовместимого
остатка. Ни application startup, ни handler, ни runner не выполняют этот
backfill.

### 4. Rewrite против forward repair выбирается по provenance

- Если применение feature revision доказано, revision не переписывается:
  создаётся новая forward repair/compatibility revision.
- Если применение не доказано и revision ещё не вошла в release/base history,
  допускается её исправление до landing с последующим повтором graph и safety
  checks.
- Если evidence противоречива, implementation и landing останавливаются до
  ручного разрешения конфликта provenance.

### 5. Data transition имеет preview и recovery evidence

До изменения данных на test DB формируется preview: число затронутых строк,
распределение `NULL`/non-`NULL`, ожидаемые значения после backfill и итоговое
число строк, нарушающих constraint. Explicit confirmation даёт владелец
миграционного rollout, а не пользователь бота.

Affected records определяются classifier-ом `bot_active` и текущим состоянием
нового флага; broad backfill без classifier запрещён. Точный фильтр фиксируется
в spec и regression test. Recovery не полагается на destructive downgrade:
используются backup/restore на test DB и forward compensating action для уже
применённого rollout.

### 6. Compatibility existing clients является отдельным gate

До и после test-DB rollout фиксируются baselines для representative paid/free
client cohorts: effective automation flags, billing state, WB write activity и
campaign lifecycle. Сравнение выполняется по тем же affected records и
migration snapshot, что и data-transition preview.

Текущий broad backfill `NULL → true` запрещён. Классифицированное изменение
`bot_active=True → auto_update_minus_phrases=True` является explicit rollout
semantics и должно иметь accepted owner confirmation, affected-client evidence
и recovery plan. `None` не является постоянным состоянием для runtime-контракта
и не должен трактоваться как включённая automation.

## Risks / Trade-offs

- [Risk] Backfill `true` может быть неверен для части существующих настроек
  → [Mitigation] использовать только `bot_active` classifier, preview и
  explicit owner confirmation; без этого оставить `NO_GO`.
- [Risk] Постоянный fallback `None → true` включит automation на неодинаковых
  read-paths
  → [Mitigation] завершить schema/data transition до UI rollout и оставить
  runtime-контракт типизированным `bool` без legacy fallback.
- [Risk] Backfill может молча включить automation или изменить billing/WB writes
  у действующих клиентов
  → [Mitigation] обязательный paid/free before/after compatibility baseline;
  любой недопустимый drift блокирует readiness.
- [Risk] Rewrite revision после скрытого применения нарушит immutable history
  → [Mitigation] требовать database/deployment receipt, а при доказанном
  применении использовать только forward repair.
- [Risk] Слишком широкий dirty worktree изменит stage-diff verdict
  → [Mitigation] frozen snapshot, path-scoped diff и повторная проверка SHA
  перед каждым итоговым gate.
- [Risk] Попытка разрешить `op.execute()` глобальным исключением скроет
  online-unsafe migration → [Mitigation] не менять общий safety policy; при
  необходимости добавить отдельный доказуемый rollout path.
- [Risk] Migration Job policy ещё Proposed globally → [Mitigation] owner
  confirmation authorizes this change only; production rollout still requires
  approved-path receipts and the global decision remains open.
- [Risk] Stage и production deployment receipts относятся к разным snapshot
  → [Mitigation] привязать каждый receipt, smoke result и compatibility
  baseline к candidate SHA и release identifier.

## Migration Plan

1. Зафиксировать base ref, merge-base, HEAD SHA и список разрешённого diff;
   отдельно сохранить pre-existing dirty files.
2. Получить provenance evidence по feature migration и определить
   `rewrite-before-landing`, `forward-repair` или `NO_GO`.
3. Подтвердить семантику backfill/default/nullable transition на test DB и
   оформить preview, affected-records и recovery evidence.
4. Снять compatibility baseline для paid/free cohorts и сравнить его после
   test-DB rollout; любой неподтверждённый behavior drift означает `NO_GO`.
5. Реализовать выбранный migration route так, чтобы topology-only merge
   оставался no-op, schema step проходил safety gate, а backfill выполнялся
   только через approved migration Job.
6. Запустить focused graph contract, migration safety, data-transition и
   client-compatibility regression, targeted tests, required unit/static checks
   и OpenSpec validation на том же snapshot.
7. Выполнить stage deployment: schema step, одноразовый backfill, UI rollout,
   smoke и compatibility checks; сохранить stage receipts.
8. Получить production deployment/write-path approval, затем выполнить
   production migration и UI rollout; сохранить database/deployment receipts.
9. Выполнить production smoke, paid/free compatibility verification,
   monitoring window и forward recovery check; любой необъяснённый drift даёт
   `NO_GO`.
10. Сформировать release evidence package с base/candidate SHA, scope,
    provenance matrix, preview, test DB/stage/prod results, receipts и
    rollback/recovery evidence.

Rollback до landing: удалить только подготовленные unlanded изменения или
вернуть feature branch к последнему проверенному snapshot. После применения в
базе rollback выполняется только forward compensating migration по отдельному
операционному плану; production downgrade этим change не предлагается.

## Resolved Owner Decisions

Owner confirmation for this change (2026-08-17) accepted:

- `bot_active=True → auto_update_minus_phrases=True`;
- `bot_active=False → auto_update_minus_phrases=False`;
- new records default to `False`;
- one-time idempotent backfill is owned by the approved migration Job;
- Alembic `upgrade()` contains no `op.execute()` or `op.alter_column()`;
- production rollout requires migration/deployment receipts and a compatibility
  baseline; persistent `None → True` fallback is forbidden.

## Open Questions

- Как будет промотировано owner-confirmed change-local решение в reusable
  accepted decision при archive?
- Какой конкретный database/deployment receipt будет считаться доказательством
  применения revision?
- Какой stage/prod deployment path владеет последовательностью schema step,
  backfill, UI rollout и monitoring window?
- Какие baseline и recovery evidence обязательны перед production GO?

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
- [x] owner-confirmed classifier and one-time Job placement are recorded
- [x] provenance route evidence is attached
- [x] existing client compatibility baseline model and final review are included
- [x] readiness/deployment/database receipt model is separate and fail-closed
- [ ] stage deployment receipt is attached
- [ ] production migration/UI receipts are attached
- [ ] production verification and recovery evidence are attached
