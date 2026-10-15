---
cursor:
  subagentId: "bc-e18fc674-275a-5149-8c90-8edda896cdcb"
---

# Control-loop middle — architecture inventory (READ-ONLY)

**Authority:** `23c0671f372f0435b13a3573ec8990b4303b3e4a`  
**Subject:** `Merge pull request #448 from revoluxe-ai/cursor/cloud-project-bootstrap-8b4b`  
**Committed:** `2026-10-05 16:38:29 +0000`  
**Repo:** `/agent/repos/adv-bot` (`origin/stage`)

## Executive summary

| Area | Status | One-line |
|------|--------|----------|
| A ChangeSet / AI mutation contract | **GAP** | No `wb_sky_control_plane`, no ChangeSet schema in `app/`; principles in `AGENTS.md` only |
| B Deterministic validation pipeline | **PARTIAL** | Strong for **read/history/export** (`campaign_settings_contract`, `ai_package_v1` validator); **not** unified for production writes |
| C proposal → diff → dry-run → apply | **GAP** | No shared control-loop; Excel = direct apply; domain dry-run flags are feature-local |
| D Write authority | **PARTIAL** | ADRs define per-capability owners; many direct PG/WB writers (bot, shop-runner, excel, scripts) |
| E Idempotency / concurrency | **PARTIAL** | Per-feature (A/B Hold epoch, billing lock, auto-budget keys, migration control); no campaign-settings ChangeSet layer |

---

## A — ChangeSet / proposal contract

### Classification: **GAP** (aspirational + read-side contracts only)

**Evidence**

- `git grep -i changeset` on `origin/stage` under `app/`: **no matches**. Only `AGENTS.md:62` and archived OpenSpec text reference ChangeSet.
- `app/modules/wb_sky_control_plane/` — **does not exist** on this SHA.
- `tests/unit/ai_package_v1/a1_contract_stub.py` — documents isolated worktree **without** control plane; stub `CampaignResourceSnapshotV1Stub` for **negative** non-aliasing tests only.
- `openspec/specs/ai-package-campaign-settings-snapshot/spec.md` — export MUST use `CampaignSettingsSnapshotV1`, MUST NOT alias `CampaignResourceSnapshotV1` (control plane) or `AdvSettingsSnapshotDTO`.
- Archived decision text mentions `resolver.resolve_changeset_snapshots()` (`openspec/changes/archive/2026-10-05-ai-package-campaign-settings-snapshot/...`) — **no** `resolve_changeset` in `app/` on stage.

**What exists instead (transport-independent, versioned, but read/mutation-eligibility — not ChangeSet)**

| Artifact | Versioning | Role |
|----------|------------|------|
| `app/modules/campaign_settings_contract/canonical.py` — `SCHEMA_VERSION = 1`, `CanonicalSettingsSnapshot` | int schema_version in payload | History canonicalization + hash (`build_canonical_settings_snapshot`) |
| `app/modules/campaign_settings_contract/registry.py` — `FieldPolicy`, `validate_registry()` | Registry structure validated at import | Field/source policy; Excel/history projections |
| `app/modules/ai_package_v1/domain/campaign_settings_snapshot_v1.py` — `SCHEMA_VERSION = "CampaignSettingsSnapshotV1"` | Pydantic frozen models | **Export-only** snapshot; `is_mutation_eligible()` fail-closed for heuristics, not apply API |
| `app/modules/ai_package_v1/domain/manifest.py` — `PACKAGE_SCHEMA_VERSION` | ZIP manifest | Package integrity (`package_validator.validate_domain_manifest`) |
| `app/client_bot/.../adv_excel_roundtrip/schema.py` — `EXCEL_TEMPLATE_VERSION = 8` | Human template version | Excel column whitelist from registry; **not** machine ChangeSet |

**Versioned / transport-independent?**  
Read contracts: **yes** (Python registry + pydantic + canonical JSON).  
AI intent / ChangeSet apply contract: **no shipped module**.

---

## B — Deterministic validation pipeline

### Classification: **PARTIAL**

**Implemented pipeline slices (evidence)**

1. **Schema / shape (structural)**  
   - `campaign_settings_contract/registry.py:validate_registry`, `validate_registry_structure` — fail-closed registry completeness.  
   - `campaign_settings_contract/canonical.py:normalize_value`, `build_canonical_settings_snapshot` — typed normalization + enum allowlists (`FieldPolicy.allowed_values`).  
   - `ai_package_v1/validator/package_validator.py:validate_domain_manifest` — manifest version, sha256, pydantic payload checks.  
   - Excel: `schema.py` + `parse_edit_value` — column typing; template version gate in `import_apply.apply_adv_excel_rows`.

2. **Domain / inventory (ORM ↔ registry)**  
   - `campaign_settings_contract/inventory.py:validate_registry_against_inventory` — deterministic inventory vs registry (tests in `tests/unit/test_campaign_settings_contract_*`).

3. **Capability / business invariants (code, not prompt-only)**  
   - Examples: `import_apply` RO column reconciliation vs server state; `resolve_flag_after_max_cpo_decrease`; A/B Hold freeze gates in handlers (`keyword_settings.py`, `card_ab_hold/*`); `CampaignSettingsSnapshotV1.is_mutation_eligible()` for export gaps.  
   - ADRs encode invariants: `openspec/decisions/campaign-settings-contract-ownership/decision.md` (forbids invariants **only** in prompt/JSON Schema without tests); `card-ab-hold-write-path-ownership`, `mode-defaults-policy-ownership`, `auto-bid-module-coexistence-write-path`.

4. **Precondition / current-state**  
   - Excel: `is_active_adv`, RO identity fields must match PG (`import_apply.py`).  
   - A/B Hold: stats freshness, enable gates (`card-ab-hold-write-path-ownership` §2a–2c).  
   - **No** single ordered pipeline object for “external AI mutation”.

**Gaps vs target order**  
`schema → domain → capability → precondition` is **not** one orchestrator. Excel interleaves access, template version, RO checks, and field rules in one function. Shop-runner paths validate inside each service. **Capability validation** for campaign settings mutations is **distributed**, not behind one application service.

**Business invariants only in prompts?**  
Project rule rejects that for registry (`campaign-settings-contract-ownership`). Runtime write paths still rely on handler/service-local checks; no central ChangeSet validator.

---

## C — proposal → validated diff → dry-run → apply

### Classification: **GAP**

| Step | On stage? | Evidence |
|------|-----------|----------|
| Proposal / intent | **GAP** | No ChangeSet ingest API/MCP in `app/` |
| Validated diff | **GAP** | No canonical diff against current state for mutations; `deviation.py` is plan/fact metrics for Excel export, not mutation diff |
| Dry-run | **PARTIAL (local)** | `scripts/a1_controlled_ad_expansion_v1.py` — strict dry-run without `--execute`; `AUTO_SHELF_BID_CONTROL_DRY_RUN` / `auto_shelf_bid_setter.py`; `app/db/control_acquire.py` `CONTROL_DRY_RUN` (migration job only); OPSX export dry-run — **not** campaign settings control loop |
| Apply | **Many paths** | Excel `apply_adv_excel_rows` commits PG directly; bot handlers `session.commit()`; shop-runner WB writers |

**Dry-run shares code with apply?**  
- Excel: **no** separate dry-run; fail-fast apply only (`import_apply` module docstring).  
- A1 expansion script: preflight + allowlist shared; execute branch calls production adapters.  
- Shelf bid control: setter short-circuits on env dry-run inside same code path.

**Read-side “preview”**  
- `campaign_settings_history/collector.py` — change-only detection via `state_hash` vs CH (observation, not user proposal).  
- AI package export — read-only per `ai-package-v1-exporter-ownership` decision.

---

## D — Write authority

### Classification: **PARTIAL** (documented ownership; no single application service)

**Architecture intent** (`AGENTS.md:62`): WB Sky sole production-write authority; Excel not canonical control.

**Accepted decisions (campaign / settings mutations — skim)**

| Decision path | Relevance |
|---------------|-----------|
| `openspec/decisions/campaign-settings-contract-ownership/decision.md` | PG SoT; registry does **not** perform writes; Excel/CH are projections |
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | Export `READ_ONLY_NO_MUTATION`; no `WBShopDataManager` on export path |
| `openspec/decisions/mode-defaults-policy-ownership/decision.md` | Defaults in policy overlays, not transition helpers/handlers |
| `openspec/decisions/card-ab-hold-write-path-ownership/decision.md` | Dedicated A/B pipeline; Excel MUST NOT apply `card_ab_hold_mode` (MVP) |
| `openspec/decisions/auto-bid-module-coexistence-write-path/decision.md` | Mutual exclusion for Auto bid writers |
| `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` | Generation / epoch write ownership (related) |

**Actual write entrypoints (examples — not exhaustive)**

| Entry | Symbol / path | Notes |
|-------|---------------|-------|
| Telegram Excel | `import_apply.apply_adv_excel_rows` | Direct ORM `setattr` + commit |
| Telegram UI | `keyword_settings.py`, `adv_setting.py`, A/B `confirm_handlers.py` / `epoch_write.py` | Direct session commits |
| Shop-runner | `WBShopDataManager`, `card_ab_hold/pipelines.py`, `setup_apply.py`, coroutines | WB + PG |
| ARQ / workers | `auto_budget_manager/service.py`, increment managers | Redis lock + idempotency keys |
| Scripts | `scripts/a1_controlled_ad_expansion_v1.py` | Bounded ops executor, not settings ChangeSet |
| Mode defaults | `apply_*_defaults_settings_for_adv` in `client_bot/modules/default_settings/` | Policy overlays |

**Single application service for campaign settings mutations:** **not present**. Coexistence is ADR-gated per capability.

---

## E — Idempotency & concurrency

### Classification: **PARTIAL**

| Mechanism | Location | Scope |
|-----------|----------|-------|
| PG `SELECT ... FOR UPDATE` | `card_ab_hold/epoch_write.py` | A/B Hold epoch / intent |
| Redis single-flight | `card_ab_hold/pipelines.py` + `RedisLockManager` | Setup/hold ticks |
| Idempotency key columns | `AdvSetting.card_ab_hold_wb_sync_idempotency_key`, `wb_auto_budget_topup.idempotency_key` | Feature-specific |
| Redis NX lock | `auto_budget_manager/service.py`, `billing/redis_lock.py` | Budget / billing |
| Migration control | `scripts/clickhouse_migration_control_plane/*`, `app/db/control_acquire.py` | CH DDL lifecycle (`IDEMPOTENT_HIT`) |
| CH collector advisory lock | `campaign_settings_history/collector.py` docstring | History collect per cabinet |

**Shop-runner races:** coordinated per subsystem (locks, freeze filters, `filter_ab_hold_stale_mutation_candidates`); **no** optimistic version on `AdvSetting` for generic settings updates.

---

## Rules checklist (this slice)

| Rule | Assessment |
|------|------------|
| AI forms ChangeSet; WB Sky sole write authority | **Policy in AGENTS.md**; implementation **GAP** for ChangeSet path |
| External AI mutations → deterministic validation | **PARTIAL** (export/history); writes **GAP** |
| Unknown state fails closed | **YES** in `campaign_settings_contract`, export `is_mutation_eligible`, registry inventory tests |
| Transport-independent domain contract | **YES** for history + AI export; **not** for mutation ops |
| Excel not canonical control | **YES** (ADR + `EXCEL_TEMPLATE_VERSION`; registry-driven columns) |
| Invariants not only prompt/JSON Schema | **YES** for registry domain; writes use Python guards |
| REUSE > EXTEND > CREATE | Read path **reuses** `campaign_settings_contract` for Excel + history |

---

## Explicit answers A / B / C / D

**A — ChangeSet contract:** **GAP**. Read/versioned contracts exist (`campaign_settings_contract`, `CampaignSettingsSnapshotV1`, AI package manifest). No versioned machine-readable **mutation** ChangeSet; `CampaignResourceSnapshotV1` / control plane **absent** from tree (stub tests only).

**B — Validation pipeline:** **PARTIAL**. Deterministic stages exist for **canonical history** and **export integrity** and **Excel import** inline checks. No unified `schema → domain → capability → precondition` runner for AI/proposal mutations; capability rules live in scattered services/ADRs.

**C — proposal → diff → dry-run → apply:** **GAP** for the control loop. Closest analogues: Excel import (validate+apply, no dry-run); `a1_controlled_ad_expansion_v1` (ops dry-run); feature dry-run flags (shelf bidder). No shared validated-diff step.

**D — Write authority:** **PARTIAL**. PostgreSQL + per-capability ADR ownership; **many** legacy/direct writers. No central campaign-settings application service. Export explicitly forbidden to write (`ai-package-v1-exporter-ownership`).

---

## Closed changes (not reopened)

Per assignment: `ai-package-campaign-settings-snapshot`, `ai-package-keyword-performance-history`, `ai-package-full-export`, `campaign-settings-history`, `shop-wide-common-sales-collection`, `shop-wide-campaign-data-collection` — cited only via archived specs/decisions above; no change artifacts reopened.
