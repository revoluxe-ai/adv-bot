# Decision: WB API Master map — только из локальных vN swagger

## Status

Accepted

<!-- Promoted to openspec/decisions/wb-api-master-local-swagger-map/ on archive -->

## Context

North Star `wb-safe-readonly-collect` / INC-RO-03 требует воспроизводимую
карту path × method × family как явный allowlist для последующего
map-driven collect. Accepted
`openspec/decisions/scripts-wb-api-ops-stack/decision.md` запрещает invent
URL и raw HTTP для Job-скриптов, которые вызывают WB, но **не** фиксирует
ownership offline-разбора swagger и domain invariant самой карты.

Без reusable правила легко:

- положить парсер в live `wb/api` managers / collect Job;
- «дополнить» карту руками URL, которых нет в swagger;
- скачать swagger или сгенерировать клиент под видом inventory.

Нужен decision до design/apply: где живёт map builder и из чего
допустимы записи карты.

## Decision

1. **Источник записей карты.** Каждая запись API Master map
   (path × method × family) MUST происходить из уже сохранённых локальных
   OpenAPI YAML под `app/core/mp/wb/api/generated/<family>/vN/swagger/`
   (или явно указанного того же класса локального vN swagger tree).
   Path и HTTP method MUST копироваться из `paths` спеки; MUST NOT
   invent / hardcode URL вне разбора YAML.

2. **Family.** `family` MUST соответствовать ключу/дереву источника
   (swagger target / каталог generated family, например `promotion`,
   `products`, `reports`), а не произвольной операторской метке без
   привязки к файлу спеки.

3. **Offline / no codegen.** Прогон map builder MUST NOT ходить в сеть
   (в т.ч. download swagger) и MUST NOT запускать генерацию клиента.
   Обновление swagger / `vN` — зона INC-RO-02 / `tools/generate_wb_api_client.py`,
   не этого decision's map path.

4. **Ownership / layering.** Парсер и CLI карты MUST жить в operator/tooling
   плоскости `tools/` (предпочтительно рядом с swagger/codegen tooling) и/или
   тонком `scripts/` entrypoint, который только оркестрирует offline parse.
   MUST NOT размещать построение карты внутри `app/core/mp/wb/api`
   managers/adapters как побочный эффект live WB вызовов, и MUST NOT
   требовать Owner-bot Job / cabinet access / token для построения карты.

5. **Семантика артефакта.** Inventory map — allowlist *возможностей API*
   по локальным спекам. Сам факт записи в карте **не** авторизует вызов WB
   и **не** заменяет `READ_ONLY_NO_MUTATION` / stack ownership для будущих
   collect increment.

## Applies to

- Capability `wb-api-master-map` и change `wb-api-master-swagger-map`
  (INC-RO-03)
- Любой последующий tooling, который строит или обновляет API Master
  inventory map из swagger
- Future map-driven collect (INC-RO-04+), когда выбирает endpoints из карты —
  обязан считать карту производной от локального swagger, не invent URL

## Allowed

- Offline CLI/скрипт: указать локальный root `generated/.../vN` (или
  эквивалент) → детерминированный map-артефакт
- Family = ключ каталога/swagger target источника YAML
- Честный gap / skip для неразбираемых или пустых спек без выдуманных path
- Переиспользование знаний о расположении swagger из
  `tools/generate_wb_api_client.py` (пути, ключи targets) **без** вызова
  download/codegen в том же прогоне map

## Forbidden

- Invent / hand-edit path или method в карту без присутствия в локальном
  swagger YAML
- Live download swagger или remote fingerprint check как часть map build
- Генерация / регенерация OpenAPI client в том же шаге, что map build
- Размещение map builder внутри live WB manager/adapter call path
- Требование Job runtime, `shop_id`, cabinet token для построения карты
- Объявление Web Stage B / CLEAN_DUMP / collect DoD из факта наличия карты

## Examples

Good:

- `tools/…` читает
  `app/core/mp/wb/api/generated/reports/v1/swagger/12-reports.yaml`,
  извлекает `GET /path`, пишет family=`reports` в map artifact
- Повторный прогон на тех же YAML даёт тот же inventory (modulo явной
  версии метаданных)

Bad:

- Добавить в карту «удобный» URL, которого нет в YAML
- `httpx.get(dev.wildberries.ru/.../swagger)` внутри map command
- Вызвать `openapi-python-client` / `generate_wb_api_client` как шаг map
- Считать карту из hardcoded list path в Python без чтения swagger

## Related specs

- Change delta (planned): `openspec/changes/wb-api-master-swagger-map/specs/wb-api-master-map/spec.md`
- Adjacent (не изменяется этим decision): `openspec/specs/wb-api-read-only-preflight/spec.md`
- Baseline stack: `openspec/decisions/scripts-wb-api-ops-stack/decision.md`

## Related changes

- Active: `wb-api-master-swagger-map` (INC-RO-03)
- Evolution card: `openspec/evolution/wb-safe-readonly-collect.md`

## Review checklist

- [x] existing decisions searched (`openspec/decisions/index.md` +
      `scripts-wb-api-ops-stack`, `orders-or-sales-reports-read-identity`)
- [x] relevant decisions cited (`scripts-wb-api-ops-stack` — invent URL /
      Job WB stack; не покрывает offline map ownership)
- [x] new decision proposed because accepted decision was missing for
      offline API Master map ownership + source invariant
- [x] implementation layer matches decision (verify at apply:
      `tools/wb_api_master_map.py` offline; no Job/WB/codegen)
