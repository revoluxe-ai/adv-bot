---
cursor:
  subagentId: "bc-c8776ce0-1155-5744-805b-83f6cceab900"
---

# WB Sky — architecture inventory (AI mutation / control-plane surfaces)

**Authority:** `origin/stage` @ `23c0671f372f0435b13a3573ec8990b4303b3e4a`  
**Subject:** `Merge pull request #448 from revoluxe-ai/cursor/cloud-project-bootstrap-8b4b`  
**Committed:** `2026-10-05 16:38:29 +0000`  
**Mode:** READ-ONLY inventory; evidence from `git grep` / `git show` on that tree only.

## Executive summary

On `origin/stage`, **production campaign mutations** flow through **Telegram handlers** (direct PostgreSQL sessions + shop-runner/WB side effects) and **shop-runner** automation—not through a first-class HTTP or in-repo MCP control plane. **AI Package v1** is a **read-only** ZIP export (`scripts/ai_package_v1_export.py` → `app/modules/ai_package_v1/`) with **Pydantic domain contracts** inside the archive; it does **not** accept AI-proposed changesets or apply them.

The planned **`wb_sky_control_plane`** module (ChangeSet preview/apply, `CampaignResourceSnapshotV1`, `cmp_*` resources) is **not present** under `app/modules/` on this SHA; only **archived OpenSpec design** and a **unit-test stub** reference it. **`AGENTS.md`** states target principles (ChangeSet, shared JSON/API/MCP semantics), but those are **not backed by committed API/MCP servers** in this repo.

For **AI-generated campaign write authority** (deterministic validate → dry-run → apply): **Architecture Decision Missing** in `openspec/decisions/` (no indexed decision for control-plane / ChangeSet apply). Related accepted decisions cover **settings field registry**, **AI export read boundary**, and **Excel not canonical**—not an apply pipeline.

---

## Transport vs domain

| Layer | Present on `origin/stage`? | Evidence |
|--------|---------------------------|----------|
| **Domain contract (transport-independent)** | **Yes (partial)** | `app/modules/campaign_settings_contract/` — registry with semantic role, history policy, Excel policy (`registry.py` module docstring: “не transport/storage adapter”). AI export: `CampaignSettingsSnapshotV1` Pydantic (`app/modules/ai_package_v1/domain/campaign_settings_snapshot_v1.py`, `SCHEMA_VERSION = "CampaignSettingsSnapshotV1"`). |
| **Human transport (Excel)** | **Yes** | `app/client_bot/user_interface/services/adv_excel_roundtrip/` — whitelist from registry (`schema.py` imports `excel_editable_fields`, `excel_read_only_fields`). |
| **Human transport (Telegram)** | **Yes** | `app/client_bot/user_interface/handlers/*` — settings, bids, keywords, budgets, Excel callbacks (`adv_excel_roundtrip.py`). |
| **Machine transport (HTTP API for settings/mutations)** | **No** | No `FastAPI`/`APIRouter` under `app/` for campaign control; `git grep FastAPI` in `app/**/*.py` → empty. |
| **Machine transport (in-repo MCP for WB Sky)** | **No** | `git grep modelcontextprotocol\|mcp.server` in `*.py` → empty. “MCP” hits are Cursor skills, generated `nmCPM`, or future API/MCP notes in decisions. |
| **A1 control-plane snapshot / ChangeSet** | **Not shipped** | `app/modules/wb_sky_control_plane/` **absent** from `git ls-tree app/modules/`. Stub: `tests/unit/ai_package_v1/a1_contract_stub.py` (“worktree не включает wb_sky_control_plane”). |

**Conclusion:** Domain contracts exist for **history registry** and **AI export snapshots**; **writes** are not unified behind a single domain “operation” type shared by JSON/API/MCP. Excel and Telegram each implement apply logic separately (Excel: `import_apply.py`; Telegram: per-handler PG/WB paths).

---

## Architecture decisions (bounded read)

Cited from `openspec/decisions/index.md` and bodies on `origin/stage`:

| Path | Relevance |
|------|-----------|
| `openspec/decisions/campaign-settings-contract-ownership/decision.md` | Canonical field registry; PG = current settings authority; CH history & Excel = projections; **future API/MCP representations** explicitly out of scope until a separate change. |
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | Export under `app/modules/ai_package_v1/`; `READ_ONLY_NO_MUTATION`; CLI/Job only; no TG/GUI export entry. |
| `openspec/decisions/shop-data-source-strategy/decision.md` | Collection vs campaign management; preview/apply **explicitly excluded** from this ADR. |
| `openspec/decisions/scripts-wb-api-ops-stack/decision.md` | `scripts/` WB read jobs via `app/core/mp/wb/api`; default `READ_ONLY_NO_MUTATION`. |
| `openspec/decisions/shop-runner-shop-wide-collection/decision.md` | Shop-wide ad data collection executor = shop-runner (cite only; closed change `shop-wide-campaign-data-collection`). |
| `openspec/decisions/card-ab-hold-write-path-ownership/decision.md` | Excel write-path out of MVP for A/B Hold (Telegram-only). |

**Write-authority for AI ChangeSet / control-plane apply:** no matching entry in `openspec/decisions/index.md` → **Architecture Decision Missing** (do not infer from `AGENTS.md` alone).

---

## Closed changes (cite only)

Referenced for context; not reopened:

- `ai-package-campaign-settings-snapshot` — export snapshot vs `wb_sky_control_plane` A1 (design in archive; module not on tree).
- `ai-package-keyword-performance-history` — keyword performance datasets in ZIP.
- `ai-package-full-export` — `PackageZipAssembler` / `PACKAGE_FAMILY_GAPS.json` (`openspec/specs/ai-package-full-export/spec.md`).
- `campaign-settings-history` — registry + CH observer CLI.
- `shop-wide-common-sales-collection` / `shop-wide-campaign-data-collection` — collection scope (shop-runner).

---

## Surface inventory

Classification: **READY** = committed surface matches stated contract for its scope; **PARTIAL** = contract exists but gaps vs stated north-star; **GAP** = missing or not in tree; **UNKNOWN** = insufficient evidence on this SHA.

### 1. HTTP / REST API (campaign settings, bids, keywords, budgets, AI, proposals)

| Field | Value |
|-------|--------|
| **Status** | **GAP** |
| **Owner** | N/A (not implemented) |
| **Code path** | Only unrelated HTTP: `error_collector/main.py` — FastAPI webhook/digest for logging (`git show origin/stage:error_collector/main.py`). |
| **Contract** | None for campaign mutations. WB vendor OpenAPI → generated clients under `app/core/mp/wb/api/generated/` (outbound WB API, not inbound control API). |
| **Missing** | Inbound REST/OpenAPI for settings, proposals, dry-run, apply. |
| **Risk** | External AI integrations cannot use a stable HTTP contract; principles in `AGENTS.md` are aspirational. |
| **Next action** | OpenSpec change: transport + ADR for control-plane write authority before implementation. |

### 2. In-repo MCP server (WB Sky operations)

| Field | Value |
|-------|--------|
| **Status** | **GAP** |
| **Owner** | N/A |
| **Code path** | No Python MCP server implementation on tree. |
| **Contract** | N/A |
| **Missing** | Tool definitions, auth, shared operation IDs with JSON/API. |
| **Risk** | “JSON/API/MCP share semantics” (`AGENTS.md`) has no MCP counterpart in repo. |
| **Next action** | Either add MCP as transport in a dedicated change or narrow the principle to future work. |

### 3. `wb_sky_control_plane` — ChangeSet, proposal, dry_run, apply_change

| Field | Value |
|-------|--------|
| **Status** | **GAP** (not on `origin/stage`) |
| **Owner** | Planned: archive design `openspec/changes/archive/2026-10-05-ai-package-campaign-settings-snapshot/design.md` (`wb_sky_control_plane`, `CampaignResourceSnapshotV1`). |
| **Code path** | **Absent** under `app/modules/`. References: `app/modules/ai_package_v1/read/local_policy_projection.py` (must not import control plane); test stub `tests/unit/ai_package_v1/a1_contract_stub.py`. |
| **Contract** | A1 stub models only in tests; no production resolver/apply. |
| **Missing** | Entire module, registry mutation, preview/apply pipeline cited as out-of-scope in archived AI snapshot change. |
| **Risk** | Docs/archive imply a control plane that production code does not ship; AI export contract (`CampaignSettingsSnapshotV1`) is explicitly **not** A1 authoritative snapshot per archive design. |
| **Next action** | Dedicated change to land `wb_sky_control_plane` + ADR for apply ownership; until then treat as **Architecture Decision Missing**. |

### 4. AI Package v1 — read / export

| Field | Value |
|-------|--------|
| **Status** | **READY** (read scope) |
| **Owner** | `app/modules/ai_package_v1/` per `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` |
| **Code path** | `scripts/ai_package_v1_export.py` → `PackageZipAssembler` / `ExportService`; validator `app/modules/ai_package_v1/validator/package_validator.py`; `import_guard.py` forbids WB API / `WBShopDataManager` imports. |
| **Contract** | Pydantic + manifest: `package_schema_version`, dataset `schema_version` fields; specs `openspec/specs/ai-package-v1-exporter/spec.md`, `ai-package-full-export`, `ai-package-campaign-settings-snapshot`, `ai-package-keyword-performance-history`. No standalone JSON Schema files in repo (validation via Pydantic + unit tests). |
| **Missing** | Inbound “apply AI package” path; k8s Job manifest not found via `git grep ai_package` in `k8s/` on this SHA. |
| **Risk** | Operators must run CLI/Job manually; TG export forbidden by ADR. |
| **Next action** | Ops wiring (Job) if needed; keep export read-only. |

### 5. Campaign settings — domain registry & history

| Field | Value |
|-------|--------|
| **Status** | **READY** (registry + history observer); **PARTIAL** (vs unified apply API) |
| **Owner** | Registry: `app/modules/campaign_settings_contract/`; history: `app/modules/campaign_settings_history/` |
| **Code path** | History CLI: `python -m app.modules.campaign_settings_history` (`cli.py` — PG observe → CH append; gated by `CAMPAIGN_SETTINGS_HISTORY_ENABLED`). |
| **Contract** | Registry enums/policies; spec `openspec/specs/campaign-settings-history/spec.md`. |
| **Missing** | API/MCP projection; CH history not in v1 ZIP (`family_gaps.py` cites `campaign-settings-history`). |
| **Risk** | History and Excel must stay in parity with registry (contract tests); silent drift if registry not updated. |
| **Next action** | Any new transport must consume registry, per `campaign-settings-contract-ownership`. |

### 6. Excel import/export (shop campaign settings)

| Field | Value |
|-------|--------|
| **Status** | **PARTIAL** |
| **Owner** | `app/client_bot/user_interface/services/adv_excel_roundtrip/` + TG handlers `adv_excel_roundtrip.py` |
| **Code path** | Export: `export_build.py`; Import: `import_apply.py` (fail-fast, full-file reject); template `EXCEL_TEMPLATE_VERSION = 8` in `schema.py`. |
| **Contract** | Column whitelist from `campaign_settings_contract`; explicit non-goal: A/B Hold via Excel (`import_apply.py` header). |
| **Missing** | Not canonical control (`campaign-settings-contract-ownership`); no dry-run/preview separate from apply; no shared operation IDs with future API/MCP. |
| **Risk** | Human-scale bulk edits bypass any future ChangeSet validation unless Excel path is wired into control plane. |
| **Next action** | If AI mutations land, decide whether Excel remains parallel or subsumes under control plane (ADR). |

### 7. Telegram UI — settings, bids, keywords, budgets

| Field | Value |
|-------|--------|
| **Status** | **READY** (production UX write path) |
| **Owner** | `app/client_bot/user_interface/handlers/` (e.g. `adv_setting/adv_setting.py`, `change_cpm.py`, `change_auto_bid.py`, `cpm_builder.py`, phrase handlers, `campaign_activity.py`, shelf bid control menus) |
| **Code path** | Aiogram `@router.callback_query` / FSM; PG `sm(read_only=True/False)` pattern across handlers. |
| **Contract** | Implicit per-handler validation; not a single OpenAPI document. |
| **Missing** | Machine-readable operation catalog; deterministic cross-transport semantics. |
| **Risk** | Primary write surface today; external AI must not bypass without new control plane. |
| **Next action** | Document owner write paths per feature or route through future control plane. |

### 8. Shop-runner / WB automated mutation (non-AI)

| Field | Value |
|-------|--------|
| **Status** | **READY** (runtime automation, not AI ingress) |
| **Owner** | `app/modules/shop_runner/` (bidders, pauses, A/B hold `card_ab_hold/*`, shelf bid control with env dry-run `AUTO_SHELF_BID_CONTROL_DRY_RUN`) |
| **Code path** | e.g. `auto_shelf_bid_setter.py` (dry-run skips WB PATCH); activity-control pause paths per various write-path ADRs. |
| **Contract** | Domain specs under `openspec/specs/` (e.g. `card-ab-hold-mode`); not JSON API. |
| **Missing** | AI proposal intake. |
| **Risk** | Competing writers if AI apply added without mutual-exclusion ADRs (see `auto-bid-module-coexistence-write-path`, etc.). |
| **Next action** | Any AI apply change must cite coexistence / hold / empty-keywords ADRs. |

### 9. `scripts/wb_api_readonly_ops` (WB read collect)

| Field | Value |
|-------|--------|
| **Status** | **READY** (read-only ops) |
| **Owner** | `scripts/wb_api_readonly_ops/` per `scripts-wb-api-ops-stack` |
| **Code path** | `mutation_guard.py` — `READ_ONLY_NO_MUTATION`; collect subpackage. |
| **Contract** | `openspec/specs/wb-api-read-only-preflight` (archive-related). |
| **Missing** | Campaign settings mutation. |
| **Risk** | Low for AI write (guarded); not a control plane. |
| **Next action** | None for mutation scope. |

### 10. `scripts/clickhouse_migration_control_plane` (DDL control plane)

| Field | Value |
|-------|--------|
| **Status** | **READY** (CH migrations only) |
| **Owner** | `scripts/clickhouse_migration_control_plane/` |
| **Code path** | CLI: plan / apply / status / reconcile (`openspec/decisions/clickhouse-migration-lifecycle-ownership`). |
| **Contract** | Spec `clickhouse-migration-lifecycle`; operator dry-run via plan/status, not campaign dry-run. |
| **Missing** | Campaign semantics. |
| **Risk** | Name collision with “control plane” for AI; different domain. |
| **Next action** | Disambiguate naming in future AI control-plane docs. |

### 11. gRPC `predict_ctr_service`

| Field | Value |
|-------|--------|
| **Status** | **UNKNOWN** for campaign settings (orthogonal) |
| **Owner** | `app/modules/grpcs/predict_ctr_service/` |
| **Code path** | Client used from shop-runner path (k8s diagnostics docs). |
| **Contract** | Protobuf/gRPC generated stubs. |
| **Missing** | N/A for settings mutation inventory. |
| **Risk** | Low for this inventory. |
| **Next action** | None unless AI bid proposals target CTR service directly. |

### 12. OpenAPI / JSON Schema (product control operations)

| Field | Value |
|-------|--------|
| **Status** | **GAP** (product control plane) |
| **Owner** | N/A |
| **Code path** | `openapitools.json` (tooling); `.cursor/opsx-resolve-conflict/schemas/*.schema.json` (OPSX conflict tooling); `tests/unit/tools/fixtures/wb_api_master_map/minimal_openapi.yml` (WB map tests). |
| **Contract** | AI Package uses Pydantic + canonical JSON bytes (`domain/serialization.py`), not published JSON Schema artifacts in repo. |
| **Missing** | OpenAPI for proposals/apply; JSON Schema for ChangeSet. |
| **Risk** | Integrators cannot codegen against a stable mutation API. |
| **Next action** | Spec-first change with schema artifacts if HTTP/MCP added. |

---

## JSON vs API vs MCP — semantics alignment

| Channel | Campaign read | Campaign write / apply | Shared operation model |
|---------|---------------|------------------------|-------------------------|
| **AI Package ZIP (JSON inside)** | **Yes** — export-only datasets | **No** | Export Pydantic models only |
| **HTTP API** | **No** product API | **No** | **GAP** |
| **MCP (in-repo)** | **No** | **No** | **GAP** |
| **Excel** | Export/import | **Yes** — direct PG apply | Registry-driven columns; independent apply logic |
| **Telegram** | UI lists/stats | **Yes** — primary | Per-handler; no shared op enum |

**Verdict:** **Divergent** today. `AGENTS.md` north-star (shared semantics) is **not implemented** for API/MCP. Excel and Telegram **partially** align on settings fields via `campaign_settings_contract` only.

---

## Dry-run / apply patterns (what exists)

| Mechanism | Scope | On `origin/stage` |
|-----------|--------|-------------------|
| `AUTO_SHELF_BID_CONTROL_DRY_RUN` | Shelf bid WB PATCH | **Yes** — `auto_shelf_bid_setter.py` |
| `CONTROL_DRY_RUN` | DB control acquire baseline | **Yes** — `app/db/control_acquire.py` |
| Script `--dry-run` / `--execute` | Ad-hoc scripts | **Yes** — e.g. `scripts/a1_controlled_ad_expansion_v1.py`, billing scripts |
| ChangeSet preview / `apply_change` | AI campaign mutations | **GAP** — no module |
| CH migration `plan` | Schema DDL | **Yes** — migration control plane only |
| Excel import | Settings | **No** separate dry-run — fail-fast apply or reject file |

---

## Evidence commands (replay)

```bash
cd /agent/repos/adv-bot
git fetch origin
git rev-parse origin/stage
git log -1 --format='%H%n%s%n%ci' origin/stage
git ls-tree -d --name-only origin/stage app/modules/
git grep -n FastAPI origin/stage -- 'app/**/*.py'
git ls-tree -r --name-only origin/stage scripts/ai_package_v1_export.py
git show origin/stage:scripts/ai_package_v1_export.py | head -40
```

---

## PRs

None (read-only inventory).
