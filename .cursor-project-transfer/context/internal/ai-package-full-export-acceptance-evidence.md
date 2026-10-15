---
cursor:
  subagentId: "bc-0a55fa12-200d-5dfa-b776-987fb4d86f8b"
---

# ai-package-full-export — acceptance evidence (raw, read-only)

## Baseline and worktree

| Field | Value |
|--------|--------|
| **BASELINE_SHA** | `23c0671f372f0435b13a3573ec8990b4303b3e4a` |
| **BASELINE_SUBJECT** | Merge pull request #448 from revoluxe-ai/cursor/cloud-project-bootstrap-8b4b |
| **BASELINE_CI** | 2026-10-05 16:38:29 +0000 |
| **HEAD** | `751e7bd2965a2d35941c5827a13cfab0ad6fc588` |
| **HEAD vs origin/stage** | Behind `origin/stage` (not checked out; inspection via `git show origin/stage:<path>` and local tree where `git diff HEAD origin/stage -- app/modules/ai_package_v1/` is empty) |
| **Worktree** | Clean at evidence end (`git status --short` empty) |
| **PRODUCT_CODE_CHANGED** | NO (no edits under `/agent/repos/adv-bot`) |

## Committed component paths (origin/stage)

| Role | Path | Lines (stage) |
|------|------|----------------|
| Export orchestrator | `app/modules/ai_package_v1/export/export_service.py` | `ExportService` L73–276, `export` / `export_with_scope` L109–167, `_export_with_scope` L169–276 |
| ZIP assembler | `app/modules/ai_package_v1/export/package_zip_assembler.py` | `PackageZipAssembler` L12–76 |
| Family gaps catalog | `app/modules/ai_package_v1/export/family_gaps.py` | `build_family_gap_catalog` L35–92, `PACKAGE_FAMILY_GAPS_LOGICAL` L21 |
| Manifest writer/schema | `app/modules/ai_package_v1/domain/manifest.py` | `MANIFEST_LOGICAL_NAME` = `manifest.json` L16; `ExportManifest` L56–91; per-file `sha256` L37–53 |
| DATA_MAP builder | `app/modules/ai_package_v1/keyword_performance/domain/data_map_builder.py` | `build_data_map` L38–179 |
| DATA_MAP cards | `app/modules/ai_package_v1/keyword_performance/export/dataset_cards.py` | `DATA_MAP_LOGICAL` = `DATA_MAP.json` |
| PACKAGE_SUMMARY | **Not present in repo** (grep `PACKAGE_SUMMARY` / `package_summary` on tree: zero matches). OpenSpec full-export spec names `PACKAGE_FAMILY_GAPS.json`, not PACKAGE_SUMMARY. |
| Validator | `app/modules/ai_package_v1/validator/package_validator.py` | `validate_zip_package` L83–94; `validate_domain_manifest` L31–80 |
| ZIP encode / hash | `app/modules/ai_package_v1/zip_transport/encode.py` | `encode_package` L17–33; `payload_sha256_map` L58–60 |
| Canonical JSON bytes | `app/modules/ai_package_v1/domain/serialization.py` | `canonical_json_bytes` L9–21 |
| Operator CLI | `scripts/ai_package_v1_export.py` | `main` / `_run_export` → `PackageZipAssembler()` L50–55 |
| Spec (archived capability) | `openspec/specs/ai-package-full-export/spec.md` | PackageZipAssembler + `PACKAGE_FAMILY_GAPS.json` requirements |

## Package generation

### Production CLI (`scripts/ai_package_v1_export.py`)

| Item | Observation |
|------|-------------|
| Command | `poetry run python scripts/ai_package_v1_export.py --shop-id <id> --period-start YYYY-MM-DD --period-end YYYY-MM-DD --output <path>` |
| Default wiring | `PackageZipAssembler()` → `ExportService()` with real `PgExportShopScopeReader`, CH readers, PG settings, `KeywordPerformanceAssembler()` (see `export_service.py` L80–107) |
| **Generation without prod PG/CH** | **NO** — would require live scope/stat/funnel/settings/keyword reads. Recorded as **acceptance GAP** for operator CLI on this VM (no Poetry py3.11 env; no DB). |

### Bounded non-production generation (fixture seam)

| Item | Value |
|------|--------|
| **Generation** | **YES** (twice) |
| **Why bounded** | Same seam as `tests/unit/ai_package_v1/test_package_zip_assembler.py`: `PackageZipAssembler.assemble_zip_with_scope` + injected `ExportService` with `_NoOpReader` CH fakes + `assembler_factory` / `FakeKeywordDeps` (no network). |
| **Entrypoint command** | `cd /agent/repos/adv-bot && set -a && . /tmp/ai-package-acceptance/minimal.env && set +a && PYTHONPATH=. python3 /tmp/ai-package-acceptance/generate_bounded_package.py --output <run>/package.zip --meta <run>/meta.json` |
| **Fixture identity** | `SHOP_ID="1"`, `PERIOD=2026-01-01..2026-01-07`, `GENERATED_AT="2026-10-05T12:00:00Z"` (from `test_package_zip_assembler.py` L32–34); `make_adv_setting(adv_id=111, search_adv_id=222)`; `FakeKeywordDeps` with `make_scope_row()`, overlap `{111,222}`, `make_daily_raw()` (`keyword_performance/conftest.py` L477–487 pattern). |
| **Output run A** | `/tmp/ai-package-acceptance/run-a/package.zip`, `meta.json` |
| **Output run B** | `/tmp/ai-package-acceptance/run-b/package.zip`, `meta.json` |
| **Post-build** | `validate_zip_package` called in generator (validator entry). |

## Package tree (run A)

```
DATA_MAP.json
PACKAGE_FAMILY_GAPS.json
coverage.json
datasets/campaign_full_stat.csv
datasets/campaign_settings_snapshot.json
datasets/complex_adv_funnel.csv
keyword_performance/keyword_changes.jsonl
keyword_performance/keyword_current_state.jsonl
keyword_performance/keyword_daily.jsonl
keyword_performance/keyword_decisions.jsonl          (0 bytes)
keyword_performance/keyword_position_current.jsonl   (0 bytes)
keyword_performance/keyword_position_windows.jsonl   (0 bytes)
keyword_performance/keyword_positions.jsonl          (0 bytes)
keyword_performance/keyword_windows.jsonl
manifest.json
```

15 ZIP entries; `manifest.json` is not listed in `manifest.files` (only payload descriptors — `manifest.py` L42–53).

## Family status (from generated package)

Statuses below combine **manifest dataset cards**, **payload presence**, and **`PACKAGE_FAMILY_GAPS.json`**.

| Family / dataset_id | Status in package | Evidence |
|---------------------|-------------------|----------|
| `campaign_full_stat` | **PARTIAL** (0 data rows; header-only CSV) | Card: `collection_outcome=PARTIAL`, `coverage=UNKNOWN`, `row_count=0`; CSV header only |
| `complex_adv_funnel` | **PARTIAL** (0 rows) | Card: `PARTIAL` / `UNKNOWN`; header-only CSV |
| `campaign_settings_snapshot` | **PARTIAL** (1 record) | Card: `coverage=PARTIAL`, `row_file=datasets/campaign_settings_snapshot.json` |
| `shop_product_orders_sales` | **GAP** (implicit card, no file) | Card: `row_file=null`, `row_count=0`, `primary_source=SOURCE_NOT_ASSIGNED`; also named in gaps file as `shop_product_orders_sales_feed` **GAP** |
| `keyword_daily` | **PARTIAL** | `row_count=1`, file present |
| `keyword_windows` | **PARTIAL** | `row_count=16` |
| `keyword_current_state` | **PARTIAL** | `row_count=1` |
| `keyword_changes` | **PARTIAL** | `row_count=180` |
| `keyword_positions` | **PARTIAL** (empty file) | `row_count=0`, 0-byte jsonl |
| `keyword_position_windows` | **PARTIAL** (empty) | 0-byte |
| `keyword_position_current` | **PARTIAL** (empty) | 0-byte |
| `keyword_decisions` | **PARTIAL** (empty) | 0-byte |
| `keyword_coverage` / `coverage.json` | **PARTIAL** | Card + root `coverage.json` |
| `DATA_MAP` | **COMPLETE** (metadata) | Card `coverage=FULL` |
| `package_family_gaps` | **COMPLETE** (catalog) | `PACKAGE_FAMILY_GAPS.json`, 6 entries all `status: GAP` |
| `campaign_settings_history` | **GAP** (explicit only in gaps file) | Not in manifest datasets; `family_id=campaign_settings_history` in gaps |
| `shop_inventory_discovery` | **GAP** | gaps catalog only |
| `store_drr` | **GAP** | gaps catalog only |
| `product_prices_stocks` | **GAP** | gaps catalog only |
| `finance_promo` | **GAP** | gaps catalog only |

**Implicit-only absence:** `campaign_settings_history` has no dataset card—only `PACKAGE_FAMILY_GAPS.json` names it (not silent).

## Determinism (run A vs run B)

| Check | Result |
|-------|--------|
| **Payload content SHA-256** (`payload_sha256_map` / manifest `files[].sha256`) | **Equal** across A and B (all 14 listed payloads identical) |
| **Per-entry CRC / uncompressed size** | **Equal** for every ZIP member |
| **Full ZIP SHA-256** | **Different** — run A `25a05816b8a28320a87d4b40ed9a4ac12578bf5fac734adb70ec137372a59922`; run B `1957b847cd753c19928645fc82aed69eb46956a88a474729786ad698ba43d710` |
| **ZIP `date_time` metadata** | Differs (+2s): e.g. `DATA_MAP.json` `(2026,10,5,17,1,8)` vs `(2026,10,5,17,1,10)`; **contract hashes file bytes, not ZIP envelope** (`manifest.py` L37–39, `encode.py` L26–32 uses stdlib `ZipFile.writestr` without fixed `ZipInfo.date_time`) |
| **Unit test (same process, back-to-back)** | `test_package_zip_deterministic_hash` asserts full ZIP SHA-256 equal (`test_package_zip_assembler.py` L80–101) — **PASS** when runs share wall-clock second |

**Contract hash algorithm:** SHA-256 hex lowercase over **raw payload file bytes** (`manifest.py` L37–39); manifest JSON via `canonical_json_bytes` (`serialization.py` L9–21). **PACKAGE_CONTRACT_GAP:** no documented normalization of ZIP entry timestamps; byte-identical ZIP across separate processes/seconds not guaranteed.

## Semantic field inventory (per family — package metadata vs code-only)

Legend: **P** = stated in package metadata (MANIFEST cards, DATA_MAP, coverage, gaps, CSV headers, jsonl keys); **G** = PACKAGE_CONTRACT_GAP (only in Python/tests).

| Family | grain | join keys | shop id | campaign id | adv_id / legs | nmid | date/TZ | units | source | authority | formulas | null/zero/missing | first/last date | coverage/limitations |
|--------|-------|-----------|---------|-------------|---------------|------|---------|-------|--------|-----------|----------|-------------------|-----------------|----------------------|
| `campaign_full_stat` | P: card `provenance.grain` `"adv_id + date"` | P: CSV `campaign_id`, `shop_id`, `date` | P: CSV | P: `campaign_id` | P: notes Auto/Search separate | — | P: `date`; TZ **G** | P: views/clicks counts | P: `CLICKHOUSE_FULL_ADV_WB_STAT` | **G** | **G** | **G** | P: `period` in manifest | P: card `coverage`, `reason_codes` |
| `complex_adv_funnel` | P: `"nmid + date (main_nmid only)"` | P: CSV `nmid`, `shop_id`, `date` | P | — | — | P | P: date | P: orders_sum etc. | P: `CLICKHOUSE_WB_COMMON_STAT` | **G** | **G** | **G** | P: manifest `period` | P: card; notes shop orders boundary |
| `campaign_settings_snapshot` | **G** (JSON `records[]` structure) | P: `inventory.adv_setting_id`, `adv_id`, `search_adv_id`, `nmids` | P: `shop_id` in JSON + manifest | P: `adv_id` / legs | P: `auto_leg` / `search_leg` `leg_role`, `wb_adv_id` | P: `nmids` | P: `snapshot_assembled_at` | **G** | P: card `postgresql.adv_setting_detailed_settings` | P: `field_provenance[].authority_class` | **G** | **G** | **G** | P: `completeness`, card `coverage=PARTIAL` |
| `shop_product_orders_sales` | P: card `grain=n/a` | **G** | **G** | — | — | **G** | **G** | **G** | P: `SOURCE_NOT_ASSIGNED` | **G** | **G** | **G** | **G** | P: `coverage=UNKNOWN`, gaps feed **GAP** |
| Keyword datasets | P: `DATA_MAP.json` `datasets.*.grain`, `primary_key` | P: DATA_MAP + jsonl keys (`adv_id`, `norm_query`, …) | P: `shop_id` in daily row | P: `adv_setting_id` | P: `adv_id`, `leg_role` | P: `nmid` | P: `package_calculation_timezone=UTC`, `source_calendar_timezone=UNKNOWN`, `keyword_history_bounds` | P: `rate_units`, position conventions | P: per-dataset `source` in DATA_MAP | P: `ownership_evidence_scope` | P: `comparable_window_formulas`, `export_field_matrix` | P: `finite_json_rule`, `coverage.json` `missing_vs_zero` | P: `keyword_history_bounds`, cutoff dates | P: `limitations[]`, coverage `reason_codes` |
| `package_family_gaps` | P: card `grain=family_catalog` | — | P: `shop_id` in JSON | — | — | — | P: `generated_at`, `export_period` | — | P: card notes | — | — | — | — | P: each `family_id` + `status` + `reason_codes` |

## Campaign settings three-way split (from package)

| Slice | Present? | Evidence |
|-------|----------|----------|
| **Current settings** | **YES** | `datasets/campaign_settings_snapshot.json` with `schema_version`, `records[]`, `snapshot_assembled_at`; manifest card `dataset_id=campaign_settings_snapshot` |
| **Settings history / snapshots over time** | **NO** | `PACKAGE_FAMILY_GAPS.json` entry `family_id=campaign_settings_history`, `status=GAP`, notes CH history not in v1 ZIP (`family_gaps.py` L57–63 matches gaps payload) |
| **Change events (settings)** | **NO** | No settings changelog dataset in ZIP; `keyword_changes` is keyword metric deltas (DATA_MAP `keyword_changes.grain`), not PG settings events |

Periodic snapshot in export is **point-in-time** `CampaignSettingsSnapshotV1`, not a history stream.

## Keyword performance (package + bounded fixture)

| Topic | Finding |
|-------|---------|
| Daily primary evidence | **YES** — `keyword_performance/keyword_daily.jsonl` 1 row; keys include `date`, `adv_id`, `leg_role`, `norm_query`, `views`, `spend_rub`, `query_spend_status` |
| Physical campaign IDs | **YES** — `adv_id` 111 in sample row; scope overlap maps 111/222 |
| Auto/Search distinction | **YES** — `leg_role` field in daily row; inventory `auto_leg` / `search_leg` in settings JSON |
| Normalized query | **YES** — `norm_query`; DATA_MAP `raw_query_semantics` |
| Rebound history | **G** in package for this fixture (no explicit rebound flag in daily line); scope reason codes in coverage |
| Spend semantics | **P** — sample `spend_rub=50.0`, `query_spend_status=FACTUAL`; DATA_MAP + `coverage.json` `missing_vs_zero` |
| Position semantics | **P** — DATA_MAP `position_direction`, `position_delta_convention`; position jsonl files empty in this package |
| Raw evidence | **P** — `raw_query`, `raw_query_status` on daily row |
| Fabricated spend | **Not observed in package** — factual spend present; implementation `spend_mapper.py` L1–22 documents no CPM×views fabrication (**code citation for audit trail**, not used to answer AI-readability questions) |

## Common sales / campaign advertising

| Topic | Finding |
|-------|---------|
| Shop-wide coverage metadata | **GAP** — `shop_product_orders_sales` card only (`row_count=0`, `SOURCE_NOT_ASSIGNED`); gaps `shop_product_orders_sales_feed` |
| Joinability | Funnel CSV keys `shop_id,nmid,date`; campaign stat `shop_id,campaign_id,date`; **no shop-wide sales feed file** |
| Period semantics | Manifest `period.start/end` = `2026-01-01` .. `2026-01-07` |
| Timezone | DATA_MAP `source_calendar_timezone=UNKNOWN`, `package_calculation_timezone=UTC` |
| Missing-day semantics | **G** for sales feed; keyword `coverage.json` states `missing_vs_zero` |
| Campaign inventory completeness | Settings snapshot `completeness` block + card `coverage=PARTIAL`; gaps `shop_inventory_discovery` **GAP** |

Store DRR: **not computed**; gaps file `store_drr` **GAP**.

## AI-readability raw answers (package only)

1. **Which campaigns exist?** — One inventory record: `adv_setting_id` 101, `adv_id` 111, `search_adv_id` 222, name `"Test Campaign"` (`campaign_settings_snapshot.json`).
2. **Which SKUs are covered?** — `nmids` `[111, 222]` in settings inventory; daily row `nmid` 500 (fixture).
3. **Which data periods are available?** — Export window manifest `2026-01-01`–`2026-01-07`; DATA_MAP `keyword_history_bounds` daily `2026-01-01`–`2026-01-05`; `last_closed_calendar_day` / cutoff fields in DATA_MAP.
4. **Which settings are current?** — Single snapshot in `campaign_settings_snapshot.json` (`snapshot_assembled_at` present).
5. **What is known about their history?** — **IMPOSSIBLE_FROM_PACKAGE** for settings history; gaps file states `campaign_settings_history` **GAP**. Keyword **metric** history via `keyword_changes` / windows files only.
6. **Which keyword performance data is available?** — Daily (1 row), windows (16 rows), current_state (1), changes (180 lines); positions/decisions empty files with PARTIAL/UNKNOWN cards.
7. **Where are GAP/PARTIAL?** — See family table; all six gaps-file families **GAP**; most datasets **PARTIAL** or **UNKNOWN** coverage on cards.
8. **What cannot be safely interpreted?** — Shop product orders/sales (**GAP**); settings history (**GAP**); WB calendar TZ (**UNKNOWN**); empty position/decision files despite cards; zero-row campaign/funnel CSVs (headers only).

## Validation gates

| Command | Result |
|---------|--------|
| `git diff --check` (repo root) | **PASS** (no output) |
| `PYTHONPATH=. pytest --confcutdir=tests/unit/ai_package_v1 tests/unit/ai_package_v1/test_package_zip_assembler.py -m unit -v` | **PASS** 3/3 |
| Same + `test_export_settings_integration.py`, `keyword_performance/test_export_integration.py`, `test_contract_keyword_export.py` | **PASS** 33/33 |
| Same + `keyword_performance/test_datamap.py` | **PASS** (9 total with zip tests) |
| `poetry run pyright-strict` (relevant modules) | **SKIP** — project requires Python `>=3.11,<3.12`; VM has 3.12.3 only; `poetry install` refused interpreter |
| Validator CLI | **No standalone CLI**; invoked via `validate_zip_package` in tests/generator |

**Test env note:** Unit tests run with `--confcutdir=tests/unit/ai_package_v1` and `/tmp/ai-package-acceptance/minimal.env` to avoid root `conftest` CH fixtures; selective `pip install --user` of runtime deps (not repo changes).

## git status at end

```
git status --short   # (empty)
git rev-parse HEAD   # 751e7bd2965a2d35941c5827a13cfab0ad6fc588
```

**PRODUCT_CODE_CHANGED:** NO
