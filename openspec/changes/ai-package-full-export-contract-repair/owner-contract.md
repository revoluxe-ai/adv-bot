# Owner Contract — ai-package-full-export-contract-repair

## Что хотим получить

Full AI Package v1 ZIP self-describing для внешнего AI: root `PACKAGE_SUMMARY.json`,
единый `FamilyStatus` (COMPLETE|PARTIAL|GAP|UNSUPPORTED|FAILED), явная campaign/keyword
identity, missing≠zero semantics, GAP для history/change-events без новых collectors.

## Зачем

Acceptance `FULL_AI_PACKAGE_ACCEPTANCE_REPORT` на stage `23c0671f3` показал
PACKAGE_SUMMARY/JOINABILITY/AI_READABILITY gaps при рабочем ExportService.

## Shop identity

Канонический shop id пакета — authoritative `WBCabinet.shop_id` (`str`),
включая UUID. Числовой coercion, hash-surrogate и второй скрытый идентификатор
запрещены. Пустой shop id fail-closed.

## Non-goals

Новые collectors, второй exporter, settings-history persistence, production writes.

## Acceptance

Два прогона `tests/unit/ai_package_v1/test_full_package_acceptance.py`; validator
ловит расхождение family_status; targeted pytest + pyright-strict на touched modules.
