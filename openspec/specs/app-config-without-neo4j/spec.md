## Purpose

Требования к runtime app config / DI: Neo4j не является обязательной
зависимостью bootstrap, пока не возвращён отдельным change с явным wiring.

## Requirements

### Requirement: App config bootstrap does not require Neo4j
Создание конфигурации приложения MUST NOT требовать наличия Neo4j-переменных окружения или обязательного Neo4j-блока в инфраструктурных настройках. Пути, которым граф не нужен, MUST успешно получать app config без Neo4j.

#### Scenario: Config creates without Neo4j env
- **GIVEN** в окружении отсутствуют обязательные переменные Neo4j
- **WHEN** система создаёт конфигурацию приложения для обычного bootstrap (в том числе для доступа к активным non-Neo4j зависимостям)
- **THEN** создание конфигурации завершается успешно без ошибки валидации Neo4j

#### Scenario: Unit or DI path does not fail solely due to missing Neo4j
- **GIVEN** тест или DI-проверка строит app config / контейнер без использования Neo4j
- **WHEN** Neo4j env не задан
- **THEN** провал MUST NOT объясняться отсутствием обязательных полей Neo4j

### Requirement: Runtime config surface excludes mandatory Neo4j
Поверхность runtime-конфигурации и application DI MUST NOT объявлять Neo4j обязательной зависимостью приложения, пока Neo4j не возвращён отдельным change с явным подключением.

#### Scenario: Settings expose no mandatory Neo4j dependency
- **WHEN** потребитель читает инфраструктурные настройки приложения после этого change
- **THEN** обязательного Neo4j-контракта в этих настройках нет

#### Scenario: Reintroducing Neo4j needs an explicit change
- **GIVEN** продукт снова захочет использовать Neo4j в runtime
- **WHEN** планируется возврат Neo4j в app config или DI
- **THEN** это MUST оформляться отдельным change с явным wiring, а не тихим возвратом обязательного блока «на всякий случай»

### Requirement: Test stubs are not the architecture
Временные test-only подстановки Neo4j env MUST NOT считаться выполнением требования «Neo4j не в runtime stack». Целевое поведение — отсутствие обязательного Neo4j в config, а не маскировка stub’ами.

#### Scenario: Passing only via Neo4j env stubs is insufficient
- **GIVEN** обязательный Neo4j-блок всё ещё присутствует в app config
- **WHEN** тесты зелёные только потому, что harness подставил Neo4j env
- **THEN** это MUST NOT считаться соответствием capability `app-config-without-neo4j`
