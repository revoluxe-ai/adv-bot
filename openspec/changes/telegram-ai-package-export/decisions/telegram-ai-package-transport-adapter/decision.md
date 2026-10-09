# Decision: Telegram transport adapter для AI Package

## Status

Proposed

## Context

Accepted `openspec/decisions/ai-package-v1-exporter-ownership/decision.md`
держит ZIP ownership в `app/modules/ai_package_v1/` и запрещает второй
exporter. Исходный пункт про Telegram запрещал любой GUI entry. Owner
запросил кнопку меню, которая вызывает уже существующий
`PackageZipAssembler`, не перенося семантику пакета в бот.

Этот change сужает только transport-запрет. Остальные инварианты
`READ_ONLY_NO_MUTATION` остаются.

## Decision

Telegram-меню MAY вызывать `PackageZipAssembler.assemble_zip` как
human-facing transport. Handler MUST авторизовать текущего пользователя,
резолвить `WBCabinet.shop_id` read-only запросом и передать в assembler только
этот shop id и `ExportPeriod`. Handler MUST NOT собирать datasets, кодировать
ZIP или вызывать WB mutation API.

Пока change активен, то же сужение записано в accepted decision
`ai-package-v1-exporter-ownership` (пункт 5 и Forbidden/Allowed), чтобы
placement не противоречил registry на этой ветке. При archive отдельный
permanent decision не обязателен, если amendment accepted decision сохранён.

## Applies to

- Меню магазина и callback выгрузки AI-пакета
- Будущие GUI transport adapters того же ZIP

## Allowed

- `verify_user_owns_wb_user_cabinet` и read-only SELECT shop_id
- `PackageZipAssembler.assemble_zip`
- `BufferedInputFile` / `send_document`
- In-process lock на пару telegram user + WBUserCabinet

## Forbidden

- Второй exporter или дубль `ExportService` в handler
- Передача `wb_user_cabinet_id` / `wb_cabinet.id` в assembler
- WB write, PG settings write, CH write, Apply Authority
- Локальные туннели, shell и пути машины пользователя
- Секреты и сырые ZIP bytes в логах

## Examples

Хорошо: handler после ownership check вызывает
`assemble_shop_package(shop_id, period)` → `PackageZipAssembler.assemble_zip`.

Плохо: handler сам читает datasets ClickHouse или переиспользует callback
Excel.

## Related specs

- `openspec/changes/telegram-ai-package-export/specs/telegram-ai-package-export/spec.md`
- `openspec/specs/ai-package-v1-exporter/spec.md`

## Related changes

- `telegram-ai-package-export`

## Review checklist

- [x] Existing decisions were searched before proposing implementation.
- [x] Relevant decisions are cited by path.
- [x] Ownership and placement match this decision.
- [x] No forbidden layer performs this decision's responsibility.
- [x] Tests verify behavior without masking placement violations.
