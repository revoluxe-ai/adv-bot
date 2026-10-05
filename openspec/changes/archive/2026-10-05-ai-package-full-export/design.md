# Design — ai-package-full-export

## Architecture Decision References

| Decision | Role |
|---|---|
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | Export в `ai_package_v1/`; READ_ONLY; script entry allowed |
| `openspec/decisions/shop-data-source-strategy/decision.md` | Явные GAP для неназначенных семейств |
| `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` | Supplier ORDERS ≠ shop product orders feed |

## Ownership & Placement

| Concern | Owner | Layer |
|---|---|---|
| Domain datasets | Existing `ExportService` | `export/export_service.py` |
| ZIP assembly | This change | `export/package_zip_assembler.py` |
| Family GAP catalog | This change | `export/family_gaps.py` |
| ZIP bytes | Existing `encode_package` | `zip_transport/encode.py` |
| Operator CLI | This change | `scripts/ai_package_v1_export.py` |

Checklist:

- [x] Context-first decision lookup performed.
- [x] Relevant decisions cited.
- [x] No second exporter; assembler only wraps `ExportService`.
- [x] Implementation layer matches decision.

## Goals / Non-Goals

**Goals:** один shop → один ZIP; explicit `PACKAGE_FAMILY_GAPS.json`; injectable
`ExportService` for tests.

**Non-Goals:** collectors, WB API, новые CH readers, campaign-settings-history
export.

## Semantic Write Target

```text
TARGET_ENTITY_OR_LEG: read-only AI Package v1 ZIP (domain manifest + payloads)
ALLOWED_ADAPTERS:
  - ExportService.export / export_with_scope
  - encode_package / decode_package
  - PackageZipAssembler (orchestration only)
FORBIDDEN_ADAPTERS:
  - Standalone keyword/settings exporters bypassing ExportService
  - WBShopDataManager, collectors, shop-runner updaters on ZIP path
```
