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
- [x] Shop identity stays the authoritative PG string (`WBCabinet.shop_id`).

## Shop identity

Authoritative source is `WBCabinet.shop_id` (`Mapped[str]`). PG scope selects
with `WBCabinet.shop_id == shop_id`. ClickHouse campaign and funnel SQL select
by scoped `adv_id` / `nmid`; `shop_id` on those rows is a stamp of the same
string, not a numeric database key.

`manifest.shop_id`, dataset `shop_id` columns, keyword payloads, PACKAGE_SUMMARY,
and DATA_MAP `shop_id` units are `str`. No int coercion, no UUID→int, no
hash surrogate. A future alternate identity MUST be a separately named field.

## Campaign physical legs

Permitted ids for one ComplexAdv are `{auto_adv_id, search_adv_id}`.
`campaign_id` stays the physical WB adv_id. Auto and Search stay separate:
no synthetic logical campaign id and no cross-leg fallback.

Observed campaign rows may contain both ids, only Auto, only Search, or none.
`missing leg != zero leg != synthetic merge`.

`assert_no_synthetic_merge` / `assert_observed_ids_are_physical` reject only an
observed id outside the permitted physical set. They do not require both legs
to have ClickHouse rows. The card records `PARTIAL_COLLECTION` when the slice
observes a non-empty proper subset of expected physical ids, and does not mark
that card `FULL`. An empty slice stays fail-closed (`NO_DATA`, coverage not
`FULL`) and does not emit zero-valued rows for the absent legs.

The canonical both-ids fixture remains: if rows exist for both physical ids,
export preserves both.

## ZIP determinism

**Accepted contract (this change):** `PAYLOAD_HASH_ONLY` — deterministic per-file content
hashes listed in `manifest.files`; consumers MUST NOT require byte-identical ZIP archives.

Manifest, `PACKAGE_SUMMARY.json`, `PACKAGE_FAMILY_GAPS.json`, and keyword coverage
metadata embed `generated_at`; ZIP container metadata may also vary.

**Follow-up (out of scope here):** optional byte-identical ZIP normalization — do NOT
implement timestamp/metadata normalization in this change.
