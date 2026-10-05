# Design — ai-package-full-export-contract-repair

## Architecture Decision References

- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` — read-only export under `app/modules/ai_package_v1/`.
- `openspec/decisions/shop-wide-common-sales-ownership/decision.md` — shop-wide collection ≠ AI Package shop feed export (feed stays GAP).

## Ownership & Placement

| Component | Placement |
|-----------|-----------|
| `PACKAGE_SUMMARY.json` builder | `export/package_summary.py` |
| Canonical status derivation | `export/family_status.py` |
| ZIP attach order | `export/package_zip_assembler.py` (gaps → summary → encode) |
| Keyword identity alignment | `keyword_performance/domain/data_map_builder.py`, `coverage_assembler.py`, `export/dataset_cards.py` |
| Validator | `validator/package_validator.py` |

No changes to `zip_transport/encode.py` timestamps. No production writes.

## ZIP determinism

Normative: per-file and manifest payload hashes stable for identical inputs (`PAYLOAD_HASH_ONLY`). Byte-identical ZIP archive sha256 may differ across runs due to ZIP entry metadata; follow-up defect, explicitly out of scope for this change.

## Checklist

- [x] Context-first decision lookup performed
- [x] Relevant decisions cited
- [x] Implementation layer matches exporter ownership ADR
