## Why

Текущий `/opsx-scripts` смешивает resolution с operational execution: полное
совпадение контракта может приводить к одноразовому collector, а отсутствие
capability — к неявному ожиданию нового кода. Нужен machine-controlled resolver,
единый registry SoT и branch-independent запуск, при котором operational RUN GO
только переиспользует или компонирует уже разрешённые collectors.

Классификация: **STANDALONE** (discovery OPSX-SCRIPTS-ARCH-DISCOVERY-001).

## What Changes

- Зафиксировать только четыре operational outcomes:
  **REUSE**, **COMPOSE**, **FORMAL_CHANGE_REQUIRED**, **BLOCKED**.
- Определить `EXTEND` и `CREATE` как типы formal change, а не как разрешение
  `/opsx-scripts RUN GO` на запись collector-файлов.
- Обязать `/opsx-scripts PLAN_RUN/RUN` вызывать
  `tools/scripts/resolver.py`; command-only reasoning не является допустимой
  реализацией.
- Сделать `scripts/REGISTRY.yaml` machine-readable source of truth, а
  `scripts/REGISTRY.md` — генерируемым human-readable представлением.
- Разрешать canonical worktree только через `git worktree list --porcelain`,
  exact branch `refs/heads/scripts` и проверку общего Git common directory.
  `SCRIPTS_CANONICAL_ROOT` оставить только explicit override без default path.
- Определить COMPOSE как ordered acyclic child plan: PLAN_RUN показывает child
  collectors/args/outputs, RUN выполняет child Jobs последовательно, каждый
  child проходит artifact/checksum gate, а верхний `COMPOSE_MANIFEST.json`
  становится primary artifact без скрытого semantic merge.
- Добавить caller/execution provenance и additive backward-compatible поля отчёта.
- Ограничить R1 reference migration четырьмя entrypoints:
  `a1_strict_read_only_contract_collect.py`,
  `a1_cabinet401_run_go_contract_collect.py`, его v2 и
  `multi_client_ad_preflight_collect.py`.
- Применять hardcoding gate только к новым/изменённым collectors с
  `resolution_enabled: true`; legacy rows с `resolution_enabled: false`
  не блокируют R1.

**Out of scope:** массовая регистрация 71 unregistered entrypoint; миграция
прочих collector families; product `app/**` behavior; master/stage workflows;
клиентская отчётность; новый collector service/repository; operational creation
или изменение кода.

## Capabilities

### New Capabilities

- `scripts-collector-resolution`: обязательный machine resolver с outcomes
  REUSE/COMPOSE/FORMAL_CHANGE_REQUIRED/BLOCKED и formal-change handoff.
- `scripts-registry-contract`: `scripts/REGISTRY.yaml` SoT, generated Markdown,
  minimal Registry v2 fields, legacy opt-out и hardcoding attestation.
- `scripts-branch-independent-invocation`: canonical worktree discovery,
  immutable execution SHA, child-run isolation и provenance.

### Modified Capabilities

- _(нет)_ — поведение `wb-api-read-only-preflight` не меняется; collectors
  продолжают использовать accepted stack
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md`.

## Impact

- Process surface: `.cursor/commands/opsx-scripts.md` и связанные run/report
  contracts.
- Machine registry: новый `scripts/REGISTRY.yaml`; `scripts/REGISTRY.md`
  становится generated output.
- Required tooling: `tools/scripts/resolver.py` и unit tests.
- Runtime contract: COMPOSE child Jobs, per-child artifact gates,
  `COMPOSE_MANIFEST.json`, additive SCRIPTS_REPORT provenance.
- Reference migration: только четыре перечисленных entrypoints; legacy
  `a1_cabinet401_*` остаются доступны при явном `script=`.
- Safety: сохраняются READ_ONLY default, Harbor SHA image, checksum gate,
  zero-write counters и immutable evidence.

## Intent

Один intent: сделать scripts lifecycle детерминированным и ветко-независимым
для вызова, не разрешая operational RUN GO создавать или изменять код.

## Current behavior

- `/opsx-scripts` описывает EXISTING/CREATED/BLOCKED, но не имеет обязательного
  machine resolver и не отделяет formal change от runtime execution.
- Registry machine SoT не отделён от Markdown ledger.
- Canonical worktree не определяется по porcelain topology; branch gate
  недостаточно описывает cross-worktree invocation.
- COMPOSE не имеет обязательного child execution и composite artifact contract.

## Desired behavior

- Resolver всегда вызывается из PLAN_RUN/RUN и возвращает только
  REUSE/COMPOSE/FORMAL_CHANGE_REQUIRED/BLOCKED.
- REUSE включает backward-compatible alias для старого EXISTING; старый
  CREATED больше не производится.
- Недостающая capability возвращает FORMAL_CHANGE_REQUIRED с полным
  pasteable `/opsx-ff` или `/opsx-update` запросом.
- COMPOSE последовательно выполняет ordered child plan и публикует manifest
  только после успешных gates всех обязательных children.
- Caller branch не меняется; canonical worktree валидируется через Git
  topology, а `SCRIPTS_CANONICAL_ROOT` не имеет implicit default.

## Risk

- Ошибка resolver matching — mitigated fixtures для REUSE/COMPOSE/formal change.
- Stale или dirty canonical worktree — fail-closed BLOCKED с path/evidence.
- Частичный COMPOSE — сохраняет partial artifacts, но запрещает external handoff.
- Legacy rows без backfill — явно `resolution_enabled: false`, не участвуют в
  automated resolution и не блокируют R1.

## Rollback idea

- Откат planning-defined command/registry/resolver contract до предыдущего
  read-only execution path; legacy entrypoints остаются доступны по явному
  `script=`. Никаких operational code writes для rollback.
