## Why

Текущая feature-ветка должна безопасно попасть в target-ветку, созданную от
`stage`, а затем быть готовой к передаче владельцу для merge target-ветки в
`stage`. Migration safety gate падает, потому что переход данных и изменение
обязательности поля сейчас смешаны, а provenance и совместимость существующих
клиентов не доказаны.

Нужен fail-closed merge-readiness процесс: один base/candidate snapshot,
проверенная migration topology, подтверждённая семантика перехода данных и
понятный merge `GO`/`NO_GO`. Сборка образа, загрузка в Harbor, перезапуск
deployment и проверка запущенных pod остаются отдельным operational flow
владельца после merge.

## What Changes

- Зафиксировать observable-критерии готовности feature-ветки к merge в
  target-ветку, созданную от `stage`.
- Разрешить конфликт между migration safety policy и семантикой перехода
  данных до начала implementation.
- Зафиксировать одноразовый idempotent backfill: active paid records получают
  включённый флаг, остальные существующие и новые записи — выключенный.
- Запретить постоянную трактовку `None` как включённой automation и broad
  backfill без classifier.
- Привязать merge-readiness evidence к одному base/candidate snapshot.

## Capabilities

### New Capabilities

- `stage-landing-readiness`: проверяемая подготовка feature-ветки к merge в
  target-ветку от `stage` с migration safety и quality gates.

### Modified Capabilities

<!-- Existing main specifications have no matching landing-readiness capability. -->

## Scope

### In Scope

- текущий branch-to-base landing diff для target-ветки от `stage`;
- migration safety и семантика перехода данных/схемы, необходимая для landing;
- локальная проверка migration на тестовой базе;
- Alembic head/convergence checks;
- targeted, unit, static и OpenSpec verification gates;
- merge-readiness evidence и итоговый `GO`/`NO_GO`.

### Out of Scope

- изменение или расширение OPSX command contracts;
- исправление `.cursor/commands/**`, pipeline или process surfaces;
- unrelated dirty/untracked files;
- новые продуктовые возможности;
- автоматический commit, push, merge или PR;
- сборка image и загрузка image в Harbor;
- restart entrypoint deployment и запуск pod;
- stage/prod smoke и post-deploy verification;
- production DB actions вне approved migration/deployment path;
- постоянная runtime-нормализация legacy `NULL`.

## Current and Desired Behavior

Сейчас feature branch может обсуждаться для merge, хотя migration safety test
показывает конфликт между migration implementation и branch-to-base policy.
Backfill может незаметно изменить automation behavior, а dirty worktree может
исказить merge evidence.

После change feature branch считается готовой к merge в target-ветку только
после прохождения migration semantics, provenance, migration graph, safety,
targeted/static/OpenSpec gates на одном snapshot. Merge-readiness остаётся
отдельным `GO`/`NO_GO`; image rollout и дальнейшая проверка после попадания
target-ветки в `stage` не являются результатом этого change.

## Impact

- Изменение затрагивает OpenSpec planning, migration validation и branch
  landing gates.
- Возможны изменения migration implementation, rollout Job и связанных
  regression tests после утверждения design.
- Existing paid/free product behavior не должен измениться молча; намеренное
  изменение требует отдельного принятого решения, compatibility evidence и
  recovery plan.
- Owner-owned CI/CD после merge не смешивается с локальным merge-readiness
  verdict.

## Risks and Rollback

- Неверный classifier или backfill может изменить поведение существующих
  кампаний.
- Переписывание уже remote-published migration может нарушить forward-only
  policy.
- Слишком широкая проверка может захватить pre-existing dirty worktree и
  исказить verdict.

Rollback idea: остановить merge при любом `NO_GO`; вернуть target branch к
последнему проверенному snapshot до передачи владельцу. Production recovery
остаётся отдельной operational responsibility и не выполняется этим change.
