## Why

`ExportService` уже собирает доменный manifest и payloads (campaign stat, funnel,
settings snapshot, keyword performance, DATA_MAP, coverage), а `encode_package`
умеет упаковать их в ZIP. Оператору и contract tests не хватает одного
канонического read-only entrypoint «один магазин → один ZIP» с явным перечнем
семейств данных, которые стратегия источников ожидает, но v1 export ещё не
материализует.

## What Changes

- Добавляется `PackageZipAssembler` — тонкий assembler поверх существующего
  `ExportService` + `encode_package` (без второго exporter и без collectors).
- Root-файл `PACKAGE_FAMILY_GAPS.json` с явными GAP для отсутствующих семейств
  (campaign settings history, supplier orders/sales как shop feed, store DRR,
  prices/stocks, finance и т.д.).
- CLI `scripts/ai_package_v1_export.py` для одного `shop_id` и периода
  (stdout/path, read-only).
- Contract tests: детерминизм ZIP, validator, отсутствие WB API на пути.

## Capabilities

### New Capabilities

- `ai-package-full-export`: ZIP assembler, family gaps document, operator CLI.

### Modified Capabilities

- `ai-package-v1-exporter`: ADDED — full ZIP path через assembler; gaps file.
- `ai-package-v1-contract-tests`: ADDED — assembler/CLI seam tests.

## Impact

- `app/modules/ai_package_v1/export/`, `scripts/ai_package_v1_export.py`,
  `tests/unit/ai_package_v1/`.
- **Не затрагивает:** collectors, WB writes, второй exporter, campaign-settings-history
  archive, merge/push.

## Out of scope

- Новые collectors, WB API, production writes, multi-shop batch, Telegram UI.
