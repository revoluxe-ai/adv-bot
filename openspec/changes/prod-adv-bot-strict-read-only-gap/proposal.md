## Why

Нужен воспроизводимый generic-аудит одного NMID в заданном кабинете, который
даёт фактическую картину текущего контура и экономики за ограниченное окно без
опасного смешения идентичностей, источников атрибуции или физических расходов.
Сейчас такого строгого read-only контракта нет, поэтому gap особенно критичен
для первичной проверки `shop_id=5586b2ff-449c-4151-9518-60f46d32b7d9`,
кабинета `573`, NMID `186069402`, `size_id=305698863` в
`Europe/Moscow`.

## What Changes

- Вводится reusable generic capability bounded single-NMID strict read-only
  audit, не привязанная к ProKraft или иной конкретной кампании.
- Фиксируется identity-safe маршрутизация: точные `shop_id`, cabinet, NMID и
  `size_id` обязательны; A1 fallback, нерелевантная collector/package
  подмена и выводы по чужому контуру запрещены.
- Определяется покрытие текущего контура: NMID/OFFER, AdvSetting, Auto/Search,
  прочие IDs и WB-статусы, настройки бота, CPO и лимиты; неподтверждённые
  части явно получают `NONE` или gap.
- Определяется фактическое окно 14 календарных дней, включая текущий день:
  orders, units, GMV, physical spend и authoritative direct/associated
  attribution; totals, CPO и DRR рассчитываются без glue inference,
  физический spend не дублируется.
- Вводится различение `missing`, `null`, `unsupported` и недоопределённых
  denominators с явными `NULL`/`UNDEFINED`, а authoritative topology не
  заменяется догадкой об association.
- Определяется FBO/FBS/TOTAL stock либо явный GAP и единый machine-readable
  output с human summary и decision block.
- Фиксируется targeted test contract для identity, запрета A1 fallback,
  missing/null semantics, duplicate-spend prevention и валидации output.
- Все production/shared writes остаются запрещёнными: capability допускает
  только bounded read-only execution через утверждённый WB API Job-контур.

## Capabilities

### New Capabilities

- `strict-single-nmid-read-only-audit`: generic bounded audit одного NMID с
  identity-safe routing, фактической 14-дневной экономикой, честной
  семантикой gaps/denominators и machine/human output contract.

### Modified Capabilities

- Нет. Существующий `wb-api-read-only-preflight` не изменяется; новый аудит
  задаёт отдельный более узкий контракт, а не расширяет его требования.

## Impact

Аудит затрагивает operator Job/read-only WB API контур, источники текущего
advertising/product identity, orders/sales, attribution, spend, stock и
структурированный отчёт. Размещение и запреты должны соответствовать
`openspec/decisions/scripts-wb-api-ops-stack/decision.md` и
`openspec/decisions/orders-or-sales-reports-read-identity/decision.md`;
отдельная reusable decision потребуется для строгой identity/attribution и
evidence-семантики, если существующие решения её не покрывают.

Риск — ложное связывание данных или двойной учёт расходов; он снижается
fail-closed routing, явными gaps и проверяемым output contract. Откат —
не запускать новый capability и удалить только его change-артефакты до
реализации; существующий paid/product и shared state не изменяются.

Out of scope: ProKraft-specific one-off logic, A1 fallback, campaign/bot
mutation, production/shared infrastructure changes, WB/DB/Redis/Excel state,
live Job execution, Web PASS/CLEAN_DUMP claims и неограниченный multi-NMID
collect.
