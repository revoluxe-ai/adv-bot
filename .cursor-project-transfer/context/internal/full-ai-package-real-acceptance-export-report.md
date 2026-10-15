---
cursor:
  subagentId: "bc-1d990eb7-88a5-546a-964a-de6bee610348"
---

# Full AI Package — real acceptance export (READ-ONLY attempt)

PR #450 at commit `1b636542a41e1dbfd66585c64d5c93dfff0bed18`. No code changes, no merge, no ZIP produced.

## Verdict block (required fields)

```text
PR: #450
PR_HEAD: 1b636542a41e1dbfd66585c64d5c93dfff0bed18
ORIGIN_STAGE: d2166b2d805b27a6656f46c6ccb8e56066b4e888
SHOP_ID:
PERIOD_START: 2026-09-21
PERIOD_END: 2026-10-04
EXPORT: FAIL
ZIP_PATH:
ZIP_FILES:
MANIFEST: FAIL
PACKAGE_SUMMARY: FAIL
DATA_MAP: FAIL
VALIDATOR: NOT_AVAILABLE
LIVE_FAMILY_STATUS:
campaign_advertising:
complex_adv_funnel:
campaign_settings_current:
keyword_performance:
shop_common_sales:
campaign_settings_history:
campaign_change_events:
CAMPAIGN_ROWS:
FUNNEL_ROWS:
SETTINGS_ROWS:
KEYWORD_ROWS:
FRESHNESS:
JOINABILITY: FAIL
MISSING_ZERO_NULL: FAIL
READ_ONLY_PROOF: PASS
PG_WRITES: NONE
CH_WRITES: NONE
WB_WRITES: NONE
IMPLEMENTATION_CHANGED: NO
PR_CHANGED: NO
FINAL_STATUS: BLOCKED
```

## Preflight

| Step | Result | Evidence |
|------|--------|----------|
| `git fetch origin` | OK | Fetched; `origin/stage` moved to `d2166b2d805b27a6656f46c6ccb8e56066b4e888` (post PR #451 revert restore). Not merged or rebased onto. |
| HEAD == PR #450 | OK | `git rev-parse HEAD` and `origin/cursor/ai-package-full-export-contract-repair-6076` both `1b636542a41e1dbfd66585c64d5c93dfff0bed18`. |
| Worktree | Clean | `git status --short` empty; `git diff --check` clean. |
| Alembic / collectors / updaters | Not run | Per assignment. |

## READ_ONLY_PROOF (static audit — PASS)

**Entry:** `scripts/ai_package_v1_export.py` → `PackageZipAssembler.assemble_zip` → `ExportService.export` → `encode_package` (local ZIP bytes only). Docstring: read-only PG/CH, no WB API.

**Orchestrator:** `app/modules/ai_package_v1/export/export_service.py` docstring: read-only, no WB API. Uses:

- `PgExportShopScopeReader.load_scope` — `get_async_session_maker(read_only=True)`, SQLAlchemy `select` only (`scope/pg_export_shop_scope_reader.py`, `scope/queries.py`).
- `ChCampaignStatReader`, `ChFunnelReader`, `ChExportFreshnessReader` — ClickHouse client queries loaded from `app/modules/ai_package_v1/sql/*.sql` (all `SELECT`; no `INSERT`/`ALTER` in module SQL).
- `CampaignSettingsAssembler` → `PgCampaignSettingsReader.load_adv_settings` — read-only inventory SELECT.
- `KeywordPerformanceAssembler` — CH readers under `keyword_performance/readers/` (grep: no INSERT/UPDATE/DELETE/commit in readers); PG policy readers use ORM select/join; rebound scope uses `get_rebound_wb_adv_ids` → Redis `SMEMBERS` only (`rebind_wb_adv_ids_history.py` `get_ids`, not `append`).
- `import_guard.py` forbids importing `app.core.mp.wb` and `WBShopDataManager` anywhere under `ai_package_v1/`.

**Writes in export path:** Only `args.output.write_bytes(zip_bytes)` in the CLI (allowed local ZIP). No PostgreSQL `commit`, no ClickHouse mutation statements, no WB HTTP client imports on the traced path.

**Redis:** Keyword scope may read rebound sets; export does not call `append` / `SADD`.

Conclusion: **READ_ONLY_PROOF PASS** — safe to run export from a code perspective; runtime blocked by missing DB/env (below).

## Shop selection (PostgreSQL)

**Attempt:** `poetry run python` with `get_async_session_maker()` and `SELECT shop_id FROM wb_cabinet …`.

**Failure before PG connect:** Importing `app.utils.db.session_maker` loads `app.settings`, which raises `ValueError: TELEGRAM_WEB_PORT is not set` because there is **no** `.env` in `/agent/repos/adv-bot` and no `POSTGRES_*` / `CLICK_HOUSE_*` / `TELEGRAM_WEB_PORT` in the process environment.

**Infrastructure:** `docker ps` empty; no listeners on 5432 / 8123 / 6379. No pre-running local Postgres on this VM.

Per assignment: PostgreSQL not reachable → **stop**; do not start Docker or create schemas for this hop.

**SHOP_ID:** not resolved.

## Period (intended, not applied)

Today in environment: **2026-10-05**. Exporter validates inclusive calendar bounds only (`validate_export_period`); no “exclude today” rule in code. Operator window for 14 completed days: **2026-09-21** through **2026-10-04** (exclude incomplete 2026-10-05). Export was not executed.

## Export

**Command (not run to completion):**

```bash
poetry run python scripts/ai_package_v1_export.py \
  --shop-id <shop_id> \
  --period-start 2026-09-21 \
  --period-end 2026-10-04 \
  --output /tmp/WB_SKY_FULL_AI_PACKAGE_ACCEPTANCE.zip
```

**Result:** FAIL — blocked at settings bootstrap; no ZIP at `/tmp/WB_SKY_FULL_AI_PACKAGE_ACCEPTANCE.zip`.

## ZIP inspection / live families / validator

Not performed (no artifact). Post-#450 contract expects live fields in `PACKAGE_SUMMARY.json`, `PACKAGE_FAMILY_GAPS.json`, keyword `DATA_MAP`, etc.; those would be filled from ZIP evidence on a successful run.

**Validator:** Library API `validate_zip_package` in `app/modules/ai_package_v1/validator/package_validator.py` (used in unit tests). No dedicated `scripts/*validate*package*` CLI → **NOT_AVAILABLE** for this blocked run.

## Blocker summary

1. Missing application configuration (`.env` / env vars): at minimum `TELEGRAM_WEB_PORT` and PostgreSQL/ClickHouse/Redis connection settings required by `ExportService` and keyword scope.
2. No reachable PostgreSQL (or ClickHouse/Redis) from this cloud VM without Owner-provided credentials and network path (e.g. synced `.env` from k8s NodePort — not present here).

**Unblock for a future real export (Owner action, out of scope here):** provide read-only-capable `.env` (or secrets injection) and ensure PG/CH/Redis endpoints accept SELECT/read paths; then re-run this acceptance recipe unchanged.

## Internal cross-links

- Prior bounded acceptance (fixtures, not real PG/CH): `internal/full-ai-package-acceptance-report.md`
- Contract repair review at this SHA: `internal/ai-package-full-export-contract-review-1b636542.md`
