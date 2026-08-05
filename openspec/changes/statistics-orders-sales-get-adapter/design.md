## Context

INC-RO-06 закрывает gap семьи `ORDERS_OR_SALES_REPORTS_READ` для operator
read-only preflight/collect. Бот Sky уже получает «заказы» как метрики через
analytics funnel / promotion fullstats / CH — это **другие** источники и не
закрывают COL-R03 alias ORDERS. В swagger inventory
(`app/core/mp/wb/api/swagger_inventory/2026-08-04/yaml/en/12-reports.yaml`)
есть `GET /api/v1/supplier/orders` и `GET /api/v1/supplier/sales` на
`statistics-api.wildberries.ru` (`x-readonly-method: true`). В runtime-стеке
нет Reports generated client и domain adapter на эти пути.

Канон генерации клиентов: `app/core/mp/wb/api/generated/doc.md` +
`tools/generate_wb_api_client.py` (сейчас только `promotion` / `products`).

## Evolution Context

- **Title (STAR_ID):** Безопасный постоянный сбор WB API-данных
  (`wb-safe-readonly-collect`)
- **INCREMENT_ID:** INC-RO-06
- **CURRENT_INCREMENT:** полный generate Reports-клиента + узкий adapter
  surface (orders/sales GET) + period attestation + wire ORDERS первым в
  `wb_api_readonly_ops`; unit tests без live prod
- **CONTRIBUTION_TO_NORTH_STAR:** без GET orders/sales family нельзя честно
  закрыть COL-R03 / map-driven collect alias #1
- **FORWARD_COMPATIBILITY:** только `wb/api` stack; no invent URL; POST-read ≠
  GET для будущего COL-R03; ORDERS ≠ funnel/FBS/search-report
- Design **не** реализует Future: COL-R03 packager, Stage B pagination,
  swagger auto-refresh (INC-RO-02), CLEAN_DUMP

## Goals / Non-Goals

**Goals:**

- Зарегистрировать `reports` в `SWAGGER_TARGETS` и сгенерировать полный
  versioned OpenAPI-клиент из **en** `12-reports.yaml`.
- Domain adapter/manager: только `GET supplier/orders` (+ `sales` при
  необходимости того же family).
- Wire `ORDERS_OR_SALES_REPORTS_READ` **первой** в preflight `wb_api_readonly_ops`.
- Period Stage A: `dateFrom=2026-07-04` (Moscow), одна first page,
  `next_page_followed=NO`; честная attestation модели периода.
- Unit tests без prod WB API.

**Non-Goals:**

- COL-R03-009 RETURN packager / Web PASS
- Stage B cursor follow / CLEAN_DUMP
- Проброс прочих методов Reports-клиента в readonly_ops
- Live Dilera / Cursor→prod
- Mass swagger regen всех секций

## Architecture Decision References

- Accepted:
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md`
  (scripts Job → access plane → `app/core/mp/wb/api`; no raw HTTP;
  `READ_ONLY_NO_MUTATION`; secret-strip)
- Proposed (this change):
  `openspec/changes/statistics-orders-sales-get-adapter/decisions/orders-or-sales-reports-read-identity/decision.md`
  (identity ORDERS family; anti-substitution; full generate + narrow surface)

## Ownership & Placement

| Concern | Owner layer | Placement |
|--------|-------------|-----------|
| OpenAPI generate + `vN` + lock | WB API tooling | `tools/generate_wb_api_client.py`, `generated/reports/vN/` |
| Domain adapter orders/sales | `app/core/mp/wb/api` | adapter + domain manager / hub wiring |
| Family order + period attestation + report | scripts ops | `scripts/wb_api_readonly_ops/` |
| Token/access | existing Owner-bot | `get_access_for_wb_cabinet` |
| Live API execution | Owner-bot Job | `/opsx-scripts` — не Cursor |

**Forbidden layers:** raw `httpx` к statistics-api в обход generated client;
подмена ORDERS через analytics/promotion/FBS; claim Web PASS; finance paths.

Rationale: совпадает с `scripts-wb-api-ops-stack` + proposed ORDERS identity.

## Decisions

1. **Full generate, narrow surface (Owner):** генерируем **весь** Reports
   client; в operator path пробрасываем только orders (+ sales). Альтернатива
   «тонкий raw GET» отклонена — нарушает stack decision и invent-risk.

2. **Источник YAML:** English `12-reports.yaml` из inventory
   `swagger_inventory/2026-08-04/yaml/en/12-reports.yaml` (и/или portal
   `https://dev.wildberries.ru/api/swagger/yaml/en/12-reports.yaml`).
   Транслитерация **выкл.** (как у promotion). Имя файла в портале —
   `12-reports` (не `02-products` legacy naming).

3. **Генерация (apply recipe)** — по `generated/doc.md`:

   a. Добавить в `SWAGGER_TARGETS`:

   ```text
   key: reports
   spec_url: …/yaml/en/12-reports.yaml
   spec_filename: 12-reports.yaml
   target_root: app/core/mp/wb/api/generated/reports
   package_name: <reports_client package name, e.g. reports_client>
   skip_transliteration: True
   ```

   b. Скопировать inventory YAML в `generated/reports/v1/swagger/12-reports.yaml`
      (или next `vN`) + затем:

   ```bash
   poetry run python tools/generate_wb_api_client.py \
     --spec-key reports \
     --force-version 1 \
     --use-cached-spec
   ```

   (если `v1` уже занят — следующий `vN`). Без сети при cached-spec.

   c. Проверить наличие `spec.lock.json` рядом с YAML.

   d. Обновить `generated/doc.md` таблицу ключей (`reports` row).

4. **Adapter:** по паттерну `promotion_client/fullstats` /
   `BaseSectionAdapter` + `with_raise_errors`; методы только
   `get_supplier_orders(date_from=…, flag=…)` и опционально
   `get_supplier_sales(…)`. Hub/WBDataManager (или отдельный manager) —
   тонкий фасад.

5. **Readonly ops:** новая `FamilyName` / contract alias
   `ORDERS_OR_SALES_REPORTS_READ`; `FAMILY_ORDER` начинается с ORDERS;
   preflight: smallest (одна страница); period из CLI/contract defaults
   `2026-07-04`… без yesterday→today для этой семьи; analytics family
   остаётся отдельно и **не** считается ORDERS.

6. **Period attestation:** в MAPPING/report фиксировать
   `period_parameter_model` как dateFrom/cursor (не лже-`EXACT_RANGE`);
   `next_page_followed=NO` в Stage A.

7. **Tests:** unit — generator mapping presence / adapter parses mock GET /
   orchestrator order ORDERS first / period dateFrom / anti-substitution
   (funnel mock не засчитывается как ORDERS). Без live statistics-api.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Полный Reports client содержит finance-adjacent ops | Узкий adapter; mutation_guard / не вызывать лишнее |
| Portal 498 / download fail | Inventory cached-spec path |
| Period end `2026-08-02` не в query API | Честная attestation; Stage B later |
| Путаница с funnel «orders» в боте | Decision identity + tests + MAPPING.md |
| Большой generated tree | Versioned `vN`; не трогать promotion/products |

## Migration Plan

1. Mapping `reports` + generate `vN` from inventory.
2. Adapter + hub wire.
3. Readonly ops family + MAPPING.md.
4. Unit tests green.
5. Rollback: убрать family runner / не вызывать adapter; generated `vN`
   можно оставить неиспользуемым.

## Open Questions

- Нужен ли сразу `sales` в Stage A preflight или достаточно `orders` для
  family PASS mapping (proposal: orders достаточно; sales — same adapter,
  optional second call only if required by mapping).
- Точное имя `package_name` после первого generate (зафиксировать в tasks
  после пробного generate).

## Validation Plan

- `poetry run pytest` targeted unit для adapter/orchestrator/period.
- `poetry run pyright-strict` на затронутых модулях.
- Ручная проверка: `vN/swagger/12-reports.yaml` + `spec.lock.json` существуют.
- Не вызывать prod statistics-api из Cursor.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited (`scripts-wb-api-ops-stack` + proposed ORDERS identity)
- [x] new decision proposed if missing (ORDERS identity — proposed in change)
- [x] implementation layer matches decision (generate+adapter in `wb/api`; ops in `scripts/`)
