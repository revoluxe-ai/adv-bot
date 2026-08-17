## Why

Текущая feature-ветка должна пройти единый проверяемый путь от посадки на
копию `stage` до rollout обновлённого интерфейса и проверки в production.
Migration safety gate падает, потому что переход данных и изменение
обязательности поля сейчас смешаны, а фактическое применение migration и
совместимость существующих клиентов не доказаны.

Нужен release-процесс с раздельными gate для stage, production migration,
публикации интерфейса и post-deploy verification, чтобы не выдать зелёный
результат при незавершённом или несовместимом rollout.

## What Changes

- Зафиксировать observable-критерии готовности feature-ветки к посадке на
  копию `stage`.
- Разрешить конфликт между migration safety policy и семантикой перехода
  данных до начала implementation.
- Провести stage deployment с обновлённым интерфейсом и обязательными smoke и
  compatibility checks.
- Провести production migration и UI rollout только через утверждённый
  release path с отдельным receipt.
- Проверить после production rollout automation flags, billing, WB writes и
  campaign lifecycle существующих paid/free клиентов.
- Зафиксировать одноразовый idempotent backfill: active paid records получают
  включённый флаг, остальные существующие и новые записи — выключенный.
- Запретить постоянную трактовку `None` как включённой automation и broad
  backfill без classifier.
- Привязать все evidence к одному candidate snapshot и разделить readiness,
  deployment и database-application statuses.

## Capabilities

### New Capabilities

- `stage-landing-readiness`: проверяемая подготовка feature-ветки к посадке на копию `stage` с migration safety и quality gates.

### Modified Capabilities

<!-- Existing main specifications have no matching landing-readiness capability. -->

## Scope

### In Scope

- текущий branch-to-base landing diff;
- migration safety и семантика перехода данных/схемы, необходимая для landing;
- локальная проверка migration на тестовой базе;
- Alembic head/convergence checks;
- targeted, unit, static и OpenSpec verification gates;
- stage deployment и stage verification;
- production migration/UI rollout через approved release path;
- production migration receipt, smoke checks и compatibility verification;
- evidence, необходимая перед каждым переходом release state.

### Out of Scope

- изменение или расширение OPSX command contracts;
- исправление `.cursor/commands/**`, pipeline или process surfaces;
- unrelated dirty/untracked files;
- новые продуктовые возможности;
- автоматический commit, push, merge или PR;
- production DB actions вне approved migration/deployment path;
- постоянная runtime-нормализация legacy `NULL`.

## Current and Desired Behavior

Сейчас landing может перейти к публикационному обсуждению при наличии remote
feature branch, хотя migration safety test показывает конфликт между
migration implementation и stage-diff policy. Production rollout и
совместимость существующих клиентов остаются за пределами readiness package,
а backfill может незаметно изменить automation behavior.

После change release считается завершённым только после последовательного
прохождения stage и production gates: migration semantics утверждены,
compatibility baselines не показывают недопустимого drift, migration graph и
safety checks проходят, stage и production deployment имеют receipts, а
post-deploy verification подтверждает поведение существующих paid/free
клиентов. Каждый статус остаётся отдельным evidence, а неподтверждённый
переход даёт `NO_GO`.

## Impact

- Изменение затрагивает OpenSpec planning, migration validation, branch landing
  gates, release deployment и post-deploy verification.
- Возможны изменения migration implementation, rollout Job и связанных
  regression tests после утверждения design.
- Existing paid/free product behavior не должен измениться молча; намеренное
  изменение требует отдельного принятого решения, compatibility evidence и
  recovery plan.
- Production deployment и database application становятся частью release
  evidence, но не смешиваются с локальным readiness verdict.

## Risks and Rollback

- Неверный classifier или backfill может изменить поведение существующих
  кампаний.
- Переписывание уже remote-published migration может нарушить forward-only
  policy.
- Неполный migration receipt может создать иллюзию успешного production
  rollout.
- Слишком широкая проверка может захватить pre-existing dirty worktree и
  исказить verdict.
- Неполная compatibility verification может пропустить drift paid/free
  behavior.

Rollback idea: остановить следующий release gate при любом `NO_GO`; до
production применения вернуть feature branch к последнему проверенному
snapshot. После production применения использовать только approved forward
compensating action и recovery plan, без destructive downgrade.
