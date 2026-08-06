## Context

Локальные versioned swagger уже лежат рядом с generated-клиентами
(`generated/<family>/vN/swagger/*.yaml` + `spec.lock.json`), а
`tools/generate_wb_api_client.py` знает ключи семей (`promotion`, `products`,
`reports`). Нет операторского offline-прогона, который из этих YAML строит
воспроизводимую карту path × method × family как явный allowlist. Без неё
следующий map-driven collect рискует invent URL.

## Evolution Context

- **Title (STAR_ID):** Безопасный постоянный сбор WB API-данных
  (`wb-safe-readonly-collect`)
- **INCREMENT_ID:** INC-RO-03
- **CURRENT_INCREMENT:** API Master map path×method×family from local vN
  swagger (no network, no client gen)
- **CONTRIBUTION_TO_NORTH_STAR:** Explicit allowlist of API capabilities for
  later map-driven collect
- **FORWARD_COMPATIBILITY:** no invent URL; no live download; no client gen
  in this increment
- Design **не** реализует Future: INC-RO-02 swagger sync, INC-RO-04
  map-driven permanent collect / Web Stage B / CLEAN_DUMP, INC-RO-05
  read-only token, новый collect Job DoD

## Goals / Non-Goals

**Goals:**

- Offline CLI/tooling: разобрать локальные `vN/swagger` YAML известных
  семей и записать детерминированный inventory map (path × method × family).
- Привязка family к ключу источника (swagger target / каталог family).
- Честный gap при отсутствии/неразбираемости спек — без выдуманных path.
- Unit-покрытие парсера на fixture YAML (без сети).

**Non-Goals:**

- Download / status / sync swagger (INC-RO-02)
- Генерация или регенерация OpenAPI client
- Вызовы WB API, Job collect, `shop_id`, cabinet token
- Map-driven permanent collect, Web CLEAN_DUMP / Stage B (INC-RO-04)
- Read-only token hardening (INC-RO-05)
- Finance / mutation endpoints как отдельный product surface

## Architecture Decision References

- Proposed (this change):
  `openspec/changes/wb-api-master-swagger-map/decisions/wb-api-master-local-swagger-map/decision.md`
  — источник карты = локальный vN swagger; offline; ownership в `tools/`
  (± тонкий scripts entrypoint); map ≠ авторизация WB
- Accepted (baseline, не расширяем Job-path в этом change):
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md`
  — запрет invent URL для scripts→WB; здесь усиливает forward-compat карты
- Accepted (не применяется напрямую к offline map):
  `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`
  — identity ORDERS family; map может *перечислить* statistics paths из
  Reports YAML, но не wire collect

## Ownership & Placement

| Concern | Owner layer | Placement |
|--------|-------------|-----------|
| Parse OpenAPI paths + emit map | tooling | `tools/` (модуль/CLI рядом с swagger tooling) |
| Optional thin operator wrapper | scripts (optional) | только оркестрация offline CLI, без Job/WB |
| Source YAML / `vN` trees | existing generated layout | `app/core/mp/wb/api/generated/<family>/vN/swagger/` |
| Family keys discovery | reuse knowledge | ключи/`target_root` из `SWAGGER_TARGETS` **без** вызова download/codegen |

**Forbidden layers:** live `wb/api` managers/adapters как место построения
карты; raw HTTP / download swagger в map path; codegen в том же шаге;
Owner-bot Job / access plane как dependency map build.

Rationale: совпадает с proposed `wb-api-master-local-swagger-map`.

## Decisions

1. **Default scan roots.** По умолчанию CLI обходит известные family roots
   из `SWAGGER_TARGETS` (или эквивалентный явный список тех же roots) и для
   каждой family берёт **latest** `vN` с наличием `swagger/*.yaml`, либо
   явную `--version` / path override. Альтернатива «только swagger_inventory
   snapshot» отклонена как primary: INC-RO-03 и decision фиксируют vN
   generated swagger; inventory snapshot может быть optional extra root позже,
   не owed.

2. **Map artifact format.** JSON (stable key order / sorted entries) с
   метаданными: schema/version, source family, source `vN`, source yaml
   basename, список `{path, method, family}`; опционально operationId/summary
   если есть в спеке — не обязательны для allowlist. Альтернатива «только
   markdown table» отклонена как единственный SoT — markdown MAY быть
   human view, JSON MUST быть machine artifact.

3. **Determinism.** Entries sorted by `(family, path, method)`; повторный
   прогон на тех же YAML → byte-stable JSON (modulo явного `generated_at`,
   если есть — вынести в отдельное поле и не мешать compare, либо omit в
   default).

4. **HTTP methods.** Включать все methods, объявленные под path в YAML
   (включая POST). Фильтрация read-only / mutation — **не** owed INC-RO-03;
   карта — inventory capabilities, не collect policy.

5. **Gaps.** Missing family root / missing yaml / parse error → запись в
   gap report / non-zero или structured failure mode без invent entries.
   Пустой map при полном провале источников — честный fail, не success с
   ручным allowlist.

6. **Network / codegen guard.** CLI MUST NOT импортировать/вызывать download
   ветку `generate_wb_api_client` и MUST NOT открывать remote URLs. Тест:
   unit на fixture; optional assert no network helper если уже есть в
   проекте — не блокирует MVP.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Нестабильный YAML parse / PyYAML vs ruamel | Фиксировать зависимость как в codegen path; fixture regression |
| «Latest vN» неоднозначен при нескольких версиях | Явное правило latest numeric `vN` + override |
| Карта включает mutation methods → путаница с collect | Spec/docs: inventory ≠ collect allow-policy; filter — Future |
| Scope drift в sync/codegen/Job | Evolution Non-Goals + decision Forbidden |
| Большие swagger → шумный артефакт | Sorted JSON; optional future filters — не сейчас |

## Migration Plan

- Добавить tooling + unit tests; прогнать на существующих local vN swagger.
- Артефакт писать в явно указанный output path (по умолчанию под `.tmp/` или
  docs/inventory path — выбрать в apply без commit secrets).
- Rollback: удалить CLI/модуль и артефакты; runtime collect не зависит от карты.

## Open Questions

- Нужен ли thin `scripts/` wrapper в этом change или достаточно `poetry run
  python tools/…` — default: tools CLI only, scripts wrapper optional если
  REGISTRY уже требует entrypoint pattern.
- Включать ли `swagger_inventory/` snapshot как secondary root — default:
  **нет** в INC-RO-03 (только generated vN).

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (`wb-api-master-local-swagger-map`)
- [x] implementation layer matches decision (verify at apply:
      `tools/wb_api_master_map.py`)
