# AI package full export — reconciliation (2026-10-05)

Source: [Inventory AI package export](bc-2a38ad19-970d-503b-bd88-830bf2214002). Read-only. PRODUCTION_WRITES: NONE.

**Authority:** local `stage` `47a94d4ebd80fe8ea0313393c71422095568b53a` (not origin `4763b0a`).

**IMPLEMENTATION_GATE:** `WAIT_FOR_KEYWORD_MERGE`. Tip `c66f46e09` (`ai-package-keyword-performance-history`) is not an ancestor of stage. Branch `ai-package-full-export` was not created. No `openspec/changes/ai-package-full-export`.

## In committed stage

- `ai-package-campaign-settings-snapshot` — ancestor `e5e3a7126` (worktree tip already in stage history; archive move is dirty only)
- `shop-wide-common-sales-collection` — archived in stage
- `shop-wide-campaign-data-collection` — same SHA as stage HEAD
- `ai-package-v1-contract` — base archived; worktree `30d7473e6` is not an ancestor

## Not in committed stage

- `ai-package-keyword-performance-history` — worktree only @ `c66f46e09`
- `campaign-settings-history` — worktree only @ `dbafc99b0`

## Export map on stage HEAD

- ExportService: `app/modules/ai_package_v1/export/export_service.py`
- MANIFEST: `app/modules/ai_package_v1/domain/manifest.py`
- DATA_MAP: not on stage; only in keyword worktree `keyword_performance/domain/data_map_builder.py`
- PACKAGE_SUMMARY: no module; spec wording in `openspec/specs/ai-package-v1-exporter/spec.md`
- Validator: `app/modules/ai_package_v1/validator/package_validator.py`
- ZIP/hash: `app/modules/ai_package_v1/zip_transport/encode.py`
- Human CLI `scripts/ai_package_v1_export.py`: planned, file absent

Keyword worktree vs stage on AI package paths: 105 files, +13143/−39. Shared core: `export_service.py` +24/−3, `package_validator.py` +36. `manifest.py` and `encode.py` unchanged.
