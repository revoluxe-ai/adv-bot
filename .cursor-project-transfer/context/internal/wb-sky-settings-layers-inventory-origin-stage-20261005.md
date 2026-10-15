---
cursor:
  subagentId: "bc-8fc90a03-b341-54ee-8dff-fb760d2727fe"
---

# WB Sky — settings layers inventory (read-only)

**Authority SHA:** `23c0671f372f0435b13a3573ec8990b4303b3e4a`  
**Ref:** `origin/stage` — Merge PR #448 (`cursor/cloud-project-bootstrap-8b4b`), `2026-10-05 16:38:29 +0000`  
**Scope:** CURRENT SETTINGS vs SETTINGS HISTORY vs CHANGE EVENTS (do not conflate)

## Three layers (definitions used here)

| Layer | Meaning on `origin/stage` |
|-------|---------------------------|
| **CURRENT SETTINGS** | PostgreSQL authority (`AdvSetting`, keyword/shelf/schedule sources per `campaign_settings_contract`); AI export reads via `PgCampaignSettingsReader` / `CampaignSettingsAssembler`. |
| **SETTINGS HISTORY** | Append-only CH snapshots (`default_db.campaign_settings_history`), change-only vs latest hash; ~5m polling collector — **not** per-write operations. |
| **CHANGE EVENTS** | Concrete operation record: old/requested/applied/observed + source/actor/reason + proposal/execution/WB ack/postcheck — **no first-class product type at this SHA**. |

---

## 1. Audit / change events

**Classification: GAP**

Evidence: `git grep` on `origin/stage` for `old_value`, `requested_value`, `applied_value`, `observed_post_value`, `execution_status`, `proposal_status`, `wb_ack` → **zero hits** in product code/specs.

Explicit non-goal (settings history change, archived):

- `openspec/changes/archive/2026-10-05-campaign-settings-history/design.md` — **Non-Goals:** “Event sourcing every individual settings write between polling ticks.”
- Same file §3: polling “is **not presented as per-write audit logging**.”

Spec overload (not operational audit):

- `openspec/specs/campaign-settings-history/spec.md` uses “latest **change event**” to mean **latest distinct canonical hash / snapshot**, not a structured change-event row.

**Field checklist vs required audit schema**

| Field | Status | Evidence |
|-------|--------|----------|
| `change_id` | GAP | No settings-write event entity; `change_id` in `ai_package_v1` keyword performance is **metric comparator id** (`7d_vs_prev_7d`), not settings ops — `app/modules/ai_package_v1/keyword_performance/domain/models.py:277` |
| `timestamp` | PARTIAL | History snapshots only: `HistorySnapshotRow.observed_at` — `app/modules/campaign_settings_history/domain.py:HistorySnapshotRow` |
| `target`, `field` | GAP | History stores full `payload_json`, not field-level operation targets |
| `old_value`, `requested_value`, `applied_value`, `observed_post_value` | GAP | Not modeled |
| `source`, `actor`, `reason/intent` | GAP | Collector is read-only PG→CH; no actor on append — `app/modules/campaign_settings_history/collector.py:collect_cabinet` |
| `proposal_status`, `execution_status` | GAP | — |
| `WB acknowledgement`, `postcheck result` | GAP | — |

**PARTIAL (adjacent, not change events):**

- AI snapshot **read** provenance (`FieldProvenanceV1`, `observed_at`) — `app/modules/ai_package_v1/export/campaign_settings_assembler.py:_prov` — describes **export-time** PG read, not a write operation audit.
- Telegram **card A/B hold** documents “post-write re-read” after PG write-gate — `app/modules/shop_runner/.../card_ab_hold/telegram/confirm_handlers.py` — local UI path, not persisted change events or WB post-check contract.

---

## 2. Deterministic post-check after write (WB observation ↔ change_event)

**Classification: GAP**

- No `change_event` (or equivalent) table/module to link to.
- Settings history **observation** is scheduled polling (`CampaignSettingsHistoryUpdater`, default interval from `CampaignSettingsHistoryConfig`) — `app/modules/campaign_settings_history/updater.py`, `config.py` — **not** triggered by or keyed to a specific WB/PG write attempt.
- CH repository is append-only snapshots only — `ClickHouseCampaignSettingsHistoryRepository.insert_snapshots` / `latest_hashes` — `app/modules/campaign_settings_history/clickhouse_repository.py`.

**PARTIAL:** Post-mutation PG re-read in card A/B hold handlers (see above). **AUTO_SHELF_BID** dry-run skips WB PATCH — `auto_shelf_bid_setter.py` — not a deterministic post-write WB observation linked to audit.

**Conclusion:** No `change_event → observed_post_value` chain exists at this SHA.

---

## 3. Settings history (`campaign-settings-history`)

**Classification: READY** (for **snapshot history**, not operations)

**What it stores (SETTINGS HISTORY layer):**

- CH table — `scripts/clickhouse_migrations/006_create_campaign_settings_history.sql`:
  - `observed_at`, `snapshot_id`, identity (`adv_setting_id`, `wb_cabinet_id`, `shop_id`, `adv_id`, `search_adv_id`), `schema_version`, `state_hash`, `payload_json`
- Domain — `app/modules/campaign_settings_history/domain.py`: `HistorySnapshotRow`, `HistoryTimelineItem`
- Write path — `collect_cabinet`: canonicalize via `build_canonical_settings_snapshot`, compare `history.latest_hashes`, append on hash change — `app/modules/campaign_settings_history/collector.py`
- Contract/registry — `app/modules/campaign_settings_contract/` (fail-closed field policies; PG authority)

**What it does NOT store (by design):**

- Per-field deltas, requested vs applied values, actor, intent, WB API response, write proposal/execution lifecycle
- Events between polls that revert before next observation — `design.md` trade-off
- WB facts / metrics / runtime state as history drivers — spec scenarios “WB facts … stay outside settings history” — `openspec/specs/campaign-settings-history/spec.md`

**Closed owner (cite only):** archived change `campaign-settings-history` → specs at `openspec/specs/campaign-settings-history/spec.md`; decisions `openspec/decisions/campaign-settings-contract-ownership/decision.md`, `openspec/decisions/clickhouse-migration-corpus-006/decision.md`.

---

## 4. Full AI Package composition

**Orchestration (closed owner `ai-package-full-export`):**

- `PackageZipAssembler.assemble_zip` → `ExportService.export` → `attach_family_gaps` → `encode_package` — `app/modules/ai_package_v1/export/package_zip_assembler.py`
- Spec: `openspec/specs/ai-package-full-export/spec.md` — single ZIP path + mandatory `PACKAGE_FAMILY_GAPS.json`

**Included today (`ExportService._export_with_scope`):**

| Layer | In ZIP? | Classification | Evidence |
|-------|---------|----------------|----------|
| **Current settings** | YES | READY | `CampaignSettingsAssembler.assemble` → payload `CAMPAIGN_SETTINGS_JSON_LOGICAL`, `dataset_id=campaign_settings_snapshot` — `app/modules/ai_package_v1/export/export_service.py`; contract `openspec/specs/ai-package-campaign-settings-snapshot/spec.md` |
| **Campaign stat / funnel** | YES | READY (out of scope for E/F/G) | CH readers in same `export_service.py` |
| **Keyword performance history** | YES | READY | `KeywordPerformanceAssembler.assemble` — `export_service.py`; owner `openspec/specs/ai-package-keyword-performance-history/spec.md` |
| **Settings history (CH timeline)** | NO | GAP (explicit) | `build_family_gap_catalog()` entry `family_id: campaign_settings_history` — `app/modules/ai_package_v1/export/family_gaps.py:57-63`; full export spec lists this family as GAP |
| **Change events** | NO | GAP | No exporter reader; no source table |

**Shop-wide collectors (closed owners, not AI Package payloads):**

- `shop-wide-campaign-data-collection`, `shop-wide-common-sales-collection` — shop_runner / CH ingestion; shop orders/sales card in export remains `SOURCE_NOT_ASSIGNED` gap — `family_gaps.py:shop_product_orders_sales_feed`

---

## E / F / G (explicit)

| ID | Question | Answer |
|----|----------|--------|
| **E** | Full change events? | **No — GAP.** No product schema or persistence for operational change events; history explicitly rejects event sourcing between polls. |
| **F** | Deterministic post-check after write linked to change_event? | **No — GAP.** Polling history may eventually reflect post-write PG state but is not deterministic post-check per write, not linked to `change_id`, no WB acknowledgement/postcheck fields. |
| **G** | Full AI Package includes current settings, settings history, change events? | **Partial:** **current settings YES**; **settings history NO** (named GAP in ZIP); **change events NO** (no data path). |

---

## Loop blockers (closed loop: Package → AI → ChangeSet → validate → dry-run → apply → event → post-check → history → Package)

At `origin/stage`, missing or weak links:

1. **Structured change events (E)** — blocks audit, replay, and AI feedback on *who changed what and whether it landed*.
2. **Post-write observation bound to an apply attempt (F)** — blocks deterministic “applied vs observed on WB/PG” without inferring from unrelated poll snapshots.
3. **Settings history in Full AI Package** — AI cannot see CH timeline inside ZIP; only current PG snapshot + gap catalog note.
4. **Settings history ≠ operations** — even with (3) fixed, history alone cannot supply requested/applied/actor without a new CHANGE EVENTS layer.
5. **Apply / ChangeSet / deterministic validation** — dry-run exists in isolated modules (e.g. shelf bid control env dry-run); no unified ChangeSet → WB Sky apply → event pipeline evidenced at this SHA.
6. **Semantic “change event” in keyword export** — must not be mistaken for settings write audit (`KEYWORD_CHANGES.change_id` is analytics comparator grain).

---

## Key file:symbol index

- Current settings export: `ExportService._export_with_scope`, `CampaignSettingsAssembler.assemble`
- History collector: `collect_cabinet`, `CampaignSettingsHistoryUpdater`
- History storage: `ClickHouseCampaignSettingsHistoryRepository`, `HistorySnapshotRow`
- Full ZIP gaps: `build_family_gap_catalog`, `PackageZipAssembler.assemble_zip`
- Design boundary: `campaign-settings-history/design.md` (Non-Goals: event sourcing)
