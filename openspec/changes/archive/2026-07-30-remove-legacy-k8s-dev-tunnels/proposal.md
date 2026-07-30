## Why

LEGACY Python-модуль kubectl port-forward (`app.dev_local.k8s_tunnels`) уже deprecated: канон локальной разработки — публичный IP/NodePort из `.env`, автозапуск туннелей из settings отключён, unit-тесты модуля сняты. Модуль остаётся в strict pyright allowlist и даёт typing FAIL, плюс держит мёртвый API и один debug-caller. Нужно аккуратно выпилить LEGACY-поверхность, не ломая production path и destructive-test safety.

## What Changes

### Intent

Удалить in-app LEGACY kubectl port-forward к PG/CH и связанные хвосты так, чтобы локальный доступ к БД опирался только на канон `.env` (публичный IP/NodePort), а destructive live-tests по-прежнему отказывали при tunnel-env.

### Current behavior

- `app.dev_local.k8s_tunnels` помечен LEGACY; при `DEV_TUNNELS_ENABLED=true` может поднимать kubectl port-forward.
- `app.dev_local` реэкспортирует monitor/wait API.
- Production settings **не** импортируют модуль; канон локали — IP из `.env` (документировано в rules / local-dev guides).
- Единственный Python-caller — debug-entrypoint rec_bid recommendations (опциональный вызов при флаге).
- Параллельно существует ручной `scripts/dev-tunnels.ps1`.
- Destructive PG/CH fixtures hard-fail при `DEV_TUNNELS_ENABLED` / родственных tunnel env.
- Unit-тесты на сам `k8s_tunnels` уже удалены.

### Desired behavior

- In-app Python API kubectl port-forward **отсутствует**; импорт `app.dev_local.k8s_tunnels` / re-export monitor API недоступен.
- Debug/local entrypoints **не** вызывают in-app tunnel bootstrap; локальная БД — через `.env` hosts.
- Strict typing allowlist **не** включает удалённый LEGACY-модуль (закрытие pyright FAIL от этого файла).
- Destructive fixtures **сохраняют** запрет tunnel-env (denylist), даже без живого tunnel-модуля.
- Документация/rules больше не направляют на Python `k8s_tunnels` как поддерживаемый путь.

### Scope in

- Удаление LEGACY Python port-forward модуля и package re-export.
- Очистка единственного debug-caller и связанных unit-тестов entrypoint.
- Удаление ручного `scripts/dev-tunnels.ps1` и устаревших `DEV_TUNNEL_*` инструкций из `env.sample` / local-dev docs (кроме denylist для destructive tests).
- Снятие путей из `pyrightconfig_strict.json` include.
- Обновление docstring/rules ссылок на Python tunnel API.

### Out of scope

- Смена канона локального PG/CH (публичный IP/NodePort) или k8s network topology.
- Production shop-runner / Telegram / WB write paths / A/B Hold / Emergency.
- Ослабление или удаление destructive-test hard-fail на tunnel-env без эквивалентной safety.
- Новые in-app tunnel / auto port-forward реализации.
- Deploy/infra изменения cluster Postgres/ClickHouse.

### Risk

- Кто-то всё ещё запускал `DEV_TUNNELS_ENABLED=true` + Python API или `dev-tunnels.ps1` — после удаления путь сломается; mitigation: канон `.env` уже задокументирован, breaking ожидаем и объявляем.
- Случайно выпилить denylist в destructive fixtures → риск live DB через туннель; mitigation: явно сохранить/зафиксировать forbidden env keys.

### Rollback idea

Восстановить удалённые файлы из git history ветки/коммита; вернуть pyright include; не требуется DB migration.

## Capabilities

### New Capabilities

- `local-dev-db-connectivity`: канонический локальный доступ к PG/CH через `.env` hosts; запрет in-app kubectl port-forward модуля; сохранение destructive-test отказа при tunnel-env.

### Modified Capabilities

- (none — в `openspec/specs/` нет принятого capability про k8s tunnels / local-dev port-forward)

## Impact

- Local-dev tooling и debug entrypoint (не production automation).
- Strict typing allowlist / static-check pyright noise от LEGACY-файла.
- Docs/rules/env.sample и destructive-test env contract.
- **BREAKING** для любых локальных workflow, которые ещё зависели от in-app `k8s_tunnels` или `scripts/dev-tunnels.ps1`.
