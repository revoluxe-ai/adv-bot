## 1. Characterization / baseline

- [x] 1.1 Зафиксировать baseline: без `NEO4J_*` создание app config падает на ValidationError Neo4j (короткий воспроизводимый pytest или ручной snippet в apply-логе) — spec `app-config-without-neo4j`
- [x] 1.2 Перечислить grep-ом живые импорты `Neo4jConfig` / `infrastructure.neo4j` / `Neo4jContainer` в `app/` (ожидание: config + orphan container)

## 2. Production: убрать Neo4j из config/DI

- [x] 2.1 Удалить поле `neo4j` и импорт `Neo4jConfig` из `InfrastructureConfig` — decision `neo4j-not-in-runtime-config-di`, spec `app-config-without-neo4j`
- [x] 2.2 Удалить модуль `neo4j_config.py` (если больше не импортируется)
- [x] 2.3 Удалить orphan `neo4j_container.py`; убедиться, что `containers/__init__.py` не реэкспортирует Neo4j
- [x] 2.4 Повторный grep: в active `app/` нет обязательного Neo4j config/DI surface

## 3. Verification

- [x] 3.1 `poetry run pytest tests/app/modules/billing/test_billing_module_load.py::test_billing_module_load -q`
- [x] 3.2 `poetry run pytest tests/core/di/test_building_app_container.py::test_all_services_can_be_built -q`
- [x] 3.3 `poetry run pytest tests/modules/shop_menu/test_process_tokens.py tests/test_wb_shop_run_coroutines.py tests/unit/app/snapshot_data_updater/test_factory.py::test_build_snapshot_updater_live_stack -q` — не должно быть Neo4j ValidationError (прочие failures out of scope)
- [x] 3.4 Подтвердить: зелёный результат не опирается на новые `NEO4J_*` stubs в conftest как DoD (spec: test stubs are not the architecture)

## 4. Docs / decision hygiene (change-local)

- [x] 4.1 В apply-отчёте сослаться на decision path и отметить checklist item «implementation layer matches decision»

Deferred parks (не DoD этого change): см. `DOTO/WORKLOG.md` секцию
`Deferred from change drop-unused-neo4j-config` (`[deferred-from:drop-unused-neo4j-config]`).
Возврат в scope — только `/opsx-update` + `REENTER_CONFIRMED`.

## Telegram UI / Message Safety

Не применимо: change не меняет Telegram bot UI text, captions, keyboards, callbacks.
