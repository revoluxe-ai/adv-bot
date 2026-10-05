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

**Accepted contract (this change):** `PAYLOAD_HASH_ONLY` — deterministic per-file content
hashes listed in `manifest.files`; consumers MUST NOT require byte-identical ZIP archives.

Manifest, `PACKAGE_SUMMARY.json`, `PACKAGE_FAMILY_GAPS.json`, and keyword coverage
metadata embed `generated_at`; ZIP container metadata may also vary.

**Follow-up (out of scope here):** optional byte-identical ZIP normalization — do NOT
implement timestamp/metadata normalization in this change.
