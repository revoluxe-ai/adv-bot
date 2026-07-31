## ADDED Requirements

### Requirement: Local database connectivity uses env hosts
Локальный доступ приложения к PostgreSQL и ClickHouse MUST использовать хосты и порты из конфигурации окружения (`.env` / env), соответствующие канону публичного IP / NodePort. Система MUST NOT поднимать in-app kubectl port-forward к этим базам как поддерживаемый путь локальной разработки.

#### Scenario: Local run uses configured hosts
- **WHEN** разработчик запускает локальный entrypoint без tunnel-bootstrap модуля
- **THEN** подключение к PG/CH идёт по host/port из env-конфигурации

#### Scenario: In-app tunnel module is unavailable
- **WHEN** код или entrypoint пытается использовать удалённый LEGACY in-app kubectl port-forward API
- **THEN** такой API недоступен (модуль/импорт отсутствует) и локальный путь не зависит от него

### Requirement: Destructive tests reject tunnel environment
Destructive live-тесты к PG/CH MUST отказывать, если в окружении включены tunnel-related флаги (в том числе `DEV_TUNNELS_ENABLED` и родственные ключи denylist), даже после удаления LEGACY tunnel-модуля.

#### Scenario: Destructive run blocked when tunnel flag set
- **GIVEN** destructive live fixture opt-in
- **WHEN** `DEV_TUNNELS_ENABLED` (или эквивалент denylist) установлен в truthy
- **THEN** fixture MUST отказать до подключения к БД с явной ошибкой про tunnels

#### Scenario: Destructive run allowed when tunnel flags unset
- **GIVEN** destructive live fixture opt-in и прочие safety условия выполнены
- **WHEN** tunnel denylist env не установлены / false
- **THEN** fixture MUST NOT отказывать только из-за отсутствия LEGACY tunnel-модуля
