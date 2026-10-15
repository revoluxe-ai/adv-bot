---
cursor:
  subagentId: "bc-6c731ba4-eb2f-5aff-bab5-c868d2695f38"
---

# WB Sky — read-only ChangeSet / control-plane inventory (origin/stage)

Inventory date: 2026-10-05. Checkout: `751e7bd2965a2d35941c5827a13cfab0ad6fc588` (behind `origin/stage` by 2 commits; delta is Cursor cloud bootstrap only).

## Gap report read basis

`docs/ai-control-loop-gap-report.md` — **absent** on `origin/stage` and on HEAD (`git ls-tree origin/stage docs/` has no such path; repo-wide grep for `ai-control-loop` / `control-loop-gap` — no matches). **EVIDENCE_GAP:** cannot summarize ChangeSet/validation/write-authority/events/post-check gaps or quote a recommended next change name from that document.

---

## BASELINE

| Item | Value |
|------|--------|
| Authority SHA | `23c0671f372f0435b13a3573ec8990b4303b3e4a` (`origin/stage`) |
| Last confirmed baseline | `23c0671f372f0435b13a3573ec8990b4303b3e4a` — **same** (not newer) |
| HEAD SHA | `751e7bd2965a2d35941c5827a13cfab0ad6fc588` |
| HEAD vs origin/stage | **behind 2**; `HEAD` ≠ `origin/stage` |
| Behind delta | `1e4a3202b` (Cursor env), `23c0671f3` (merge PR #448) — no app/modules delta |

Citations below use **committed files at HEAD** unless noted.

---

## EXISTING CHANGESET CONTRACT

**NO** — `git grep ChangeSet\|ChangeSetV1\|changeset origin/stage -- '*.py'` returns empty. No `wb_sky_control_plane` package on tree. OpenSpec archive references future `wb_sky_control_plane` / ChangeSet resolver; not landed in Python.

Evidence: `tests/unit/ai_package_v1/a1_contract_stub.py` documents isolated worktree without `wb_sky_control_plane`.

---

## CONTROL PLANE COMMITTED ABSTRACTIONS

**NONE** under `app/modules/wb_sky_control_plane/` (directory missing).

Peripheral (not WB Sky settings control plane):

- `.cursor/pipeline/control-plane-tests/` — git packaging contract tests for OPSX commands, not domain ChangeSet.
- `openspec/decisions/clickhouse-migration-lifecycle-ownership` — ClickHouse migration control plane only.

---

## OpenSpec overlap scan

- No change or spec named `campaign-settings-changeset-contract`.
- ChangeSet mentioned only as **out of scope** / future in archives, e.g.:
  - `openspec/changes/archive/2026-10-05-ai-package-campaign-settings-snapshot/proposal.md`
  - `openspec/changes/archive/2026-10-05-ai-package-campaign-settings-snapshot/decisions/ai-package-campaign-settings-snapshot-ownership/decision.md`
  - `openspec/changes/archive/2026-10-05-ai-package-keyword-performance-history/proposal.md`
- Related **archived** settings work: `openspec/changes/archive/2026-10-05-campaign-settings-history/**`
- Promoted spec: `openspec/specs/campaign-settings-history/spec.md`
- Promoted spec: `openspec/specs/ai-package-campaign-settings-snapshot/spec.md`

---

## FILE MAP (committed inventory)

| Path | Symbol(s) | Purpose | Reuse for ChangeSetV1? |
|------|-----------|---------|------------------------|
| `app/modules/campaign_settings_contract/registry.py` | `FieldPolicy`, `NormalizationPolicy`, `REGISTERED_SOURCES`, `validate_*` | Canonical field/source registry; semantic role, history, Excel, normalization | **YES** — authoritative field policy & fail-closed registry validation |
| `app/modules/campaign_settings_contract/canonical.py` | `build_canonical_settings_snapshot`, `normalize_value`, `CanonicalSettingsSnapshot` | Deterministic normalization + versioned payload + `state_hash` for history | **YES** — normalization/deterministic snapshot; not a mutation diff contract |
| `app/modules/campaign_settings_contract/inventory.py` | `validate_registry_against_inventory`, AST ORM inventory | CI gate: ORM fields vs registry | **YES** — drift detection |
| `app/modules/campaign_settings_contract/__init__.py` | re-exports | Public contract surface | **YES** |
| `app/modules/campaign_settings_history/pg_reader.py` | `PostgresCampaignSettingsReader` | PG SELECT batch → `CampaignSettingsSources` (current settings authority) | **YES** — read current state |
| `app/modules/campaign_settings_history/collector.py` | `collect_cabinet` | Change-only history via canonical hash compare | **PARTIAL** — diff vs CH history, not proposed-vs-current ChangeSet |
| `app/modules/campaign_settings_history/domain.py` | `CampaignSettingsRecord`, ports | History domain types | **PARTIAL** |
| `app/modules/ai_package_v1/domain/campaign_settings_snapshot_v1.py` | `CampaignSettingsSnapshotV1`, `is_mutation_eligible` | AI export detailed snapshot; leg blocks; fail-closed eligibility heuristic | **PARTIAL** — read/export DTO, not ChangeSetV1 |
| `app/modules/ai_package_v1/export/campaign_settings_assembler.py` | assembler | PG → `CampaignSettingsSnapshotV1` | **PARTIAL** — read path |
| `app/modules/ai_package_v1/domain/settings_enums.py` | `CampaignLegRole`, `AuthorityClass` | Leg + authority taxonomy for export | **YES** — identity/authority vocabulary |
| `app/modules/ai_package_v1/read/local_policy_projection.py` | `project_local_policy_fields` | Local policy projection for export (explicitly no `wb_sky_control_plane`) | **PARTIAL** |
| `app/client_bot/user_interface/services/adv_excel_roundtrip/schema.py` | `EXCEL_TEMPLATE_VERSION`, registry-driven whitelists | Excel column schema tied to registry | **YES** — human mutation surface policy |
| `app/client_bot/user_interface/services/adv_excel_roundtrip/import_apply.py` | import validators | Excel → PG apply (real writes) | **NO** for validate-only ChangeSet — different write path |
| `app/client_bot/modules/default_settings/adv_setting_policy/field_policy.py` | `FieldPolicy` (mode defaults) | Paid/free/common **mode default** overlays (distinct type) | **NO** — different `FieldPolicy`; naming collision risk only |
| `app/shared/domains/wb/utils/wb_campaign_meta.py` | placement/bid_type helpers | WB campaign type / normquery eligibility | **YES** — leg/type semantics |
| `app/modules/shop_runner/.../complex_adv/complex_adv.py` | `ComplexAdv` | Shop-runner DTO: auto + search `AdvSetting` pair | **YES** — runtime leg pairing |
| `app/snapshot_data_updater/dto.py` | `AdvSettingsSnapshotDTO` | Redis tick settings DTO (shop-runner warmup) | **NO** — separate seam per AI snapshot archive |
| `tests/unit/ai_package_v1/a1_contract_stub.py` | `CampaignResourceSnapshotV1Stub` | Negative test stub for non-aliasing vs A1 | **NO** — placeholder until real control plane lands |

---

## OVERLAP RISK (future local control-plane WIP)

Likely touch paths (committed anchors only):

- `app/modules/campaign_settings_contract/**`
- `app/modules/campaign_settings_history/**`
- `app/modules/ai_package_v1/domain/campaign_settings_snapshot_v1.py`
- `app/modules/ai_package_v1/export/campaign_settings_assembler.py`
- `app/modules/ai_package_v1/read/local_policy_projection.py`
- `app/client_bot/user_interface/services/adv_excel_roundtrip/**`
- `tests/unit/test_campaign_settings_*.py`
- `tests/unit/ai_package_v1/test_campaign_settings_*.py`
- `openspec/decisions/campaign-settings-contract-ownership/decision.md`
- New package (referenced in archive, not on tree): `app/modules/wb_sky_control_plane/**`

---

## GAPS vs target (ChangeSetV1 + deterministic validation + deterministic diff, NO apply)

| Target piece | Committed state |
|--------------|-----------------|
| Versioned `ChangeSetV1` type | **Missing** (no Python type) |
| Validate-only pipeline | Registry/canonical **validate normalization**; no changeset field-level validate API |
| Deterministic diff (proposed vs current) | History collector diffs **canonical hash vs CH**; no generic settings changeset diff |
| Write authority / apply | Excel import + shop-runner/TG write paths; **no** centralized control-plane apply module |
| Events / post-check | Not found for settings ChangeSet |
| `wb_sky_control_plane` | **Not committed** (OpenSpec archive only) |

---

## Architecture decisions (bounded, ≤5)

| Path | One-line |
|------|----------|
| `openspec/decisions/campaign-settings-contract-ownership/decision.md` | Registry owns field classification; PG is current-settings authority; CH/Excel are projections; fail-closed inventory. |
| `openspec/decisions/shop-data-source-strategy/decision.md` | Shop data accumulation vs campaign management; collectors must not change `bot_active` or ad writes. |
| `openspec/decisions/mode-defaults-policy-ownership/decision.md` | Mode-specific AdvSetting defaults live in declarative policy overlays, not transition helpers. |
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | AI Package export is read-only; forbidden WB API / shop-runner orchestration on export path. |
| `openspec/decisions/clickhouse-migration-lifecycle-ownership/decision.md` | ClickHouse migration **control plane** ownership (unrelated to WB settings ChangeSet but only “control plane” ADR on index). |
