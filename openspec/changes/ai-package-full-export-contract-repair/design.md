# Design — ai-package-full-export-contract-repair

## Architecture Decision References

| Decision | Role |
|---|---|
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | ExportService + encode_package authority |
| `openspec/decisions/shop-data-source-strategy/decision.md` | Explicit GAP families |

## Ownership & Placement

| Concern | Owner | Layer |
|---|---|---|
| Summary index | This change | `export/package_summary.py` |
| FamilyStatus semantics | This change | `export/family_status.py` |
| ZIP orchestration | Existing | `export/package_zip_assembler.py` |
| Validation | Existing | `validator/package_validator.py` |

Checklist:

- [x] Context-first decision lookup performed.
- [x] No second exporter; assembler wraps ExportService only.
- [x] Settings history / change events remain GAP catalog entries.

## ZIP determinism

With fixed `generated_at`, existing tests require byte-identical ZIP (`BYTE_DETERMINISTIC`).
When `generated_at` varies, domain CSV payloads remain stable; manifest/summary/gaps
and keyword coverage metadata embed the timestamp (`PAYLOAD_DETERMINISTIC` subset).
