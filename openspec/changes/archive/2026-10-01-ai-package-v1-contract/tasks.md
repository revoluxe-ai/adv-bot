# Tasks — ai-package-v1-contract

Planning artifact. Implementation via `/opsx-apply` after owner-contract
`REVIEWED` + planning package coherent (verify at apply/archive boundary).
Tests-first; first
vertical slice before broad PG completeness claims.

```text
TASKS_STATUS: PLANNING_READY
TASKS_CHECKED: 27/29 (owe: §0.3 guard debt, §10.2)
PLANNING_READY: yes
APPLY_READY: no
PRODUCT_ACCEPTANCE_PENDING: yes (pre-apply — SIDE_EFFECT_PROOF / PA per design; not waived by planning PASS)
APPLY_PLANNING_GATE: PASS (independent `/opsx-planning-review change=ai-package-v1-contract` after
  `PLAN_EVIDENCE_ID` SCPV1-39d14fba55537e56; tasks ledger synced — not self-attested)
PLANNING_REVIEW_STATUS: PASS (independent 2026-09-27; receipt SCPV1-39d14fba55537e56)
PLANNING_REVIEW_PILLARS: PASS (P1–P4 per planning-review receipt; no blocking findings)
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
SCENARIO_REQUIREMENTS_CONSUMED: plan=yes; audit=yes (26/26 PASS; durable report
  `scenario-coverage/audit.report.md` + `audit.receipt.json` — authoritative hashes in receipt only)
SCENARIO_PLAN_RECEIPT: openspec/changes/ai-package-v1-contract/scenario-coverage/plan.receipt.json
SCENARIO_PLAN_RECEIPT_STATUS: INPUTS_CURRENT (PLAN_EVIDENCE_ID SCPV1-39d14fba55537e56; SCENARIO_COUNT=26;
  supersedes SCPV1-ce004c8dce3e693d — authoritative hashes in receipt only)
SCENARIO_AUDIT_RECEIPT: openspec/changes/ai-package-v1-contract/scenario-coverage/audit.receipt.json
SCENARIO_AUDIT_STATUS: PASS (independent `/opsx-spec-scenario-coverage mode=audit run=targeted`
  2026-09-29; `AUDIT_EVIDENCE_ID` SCAR-06a07a1142979015; 75 unit + 6 integration pytest green;
  local PG5433/CH8124; certify/provider receipts owed at §10.1 certify hop — not archive GO)
SOURCE_SPEC_SCENARIO_COUNT: 26
OWNER_CONTRACT_STATUS: REVIEWED (owner-contract-review PASS 2026-09-27; D-001..D-005)
OPSX_VERIFY_STATUS: IMPL_OK (independent /opsx-verify mode=impl 2026-09-27;
  workspace C:\Users\vkita\my_code\meta-repo\ai-package-v1-contract; archive GO not claimed)
IMPL_VERIFY_EVIDENCE: `poetry run pytest -m unit tests/unit/ai_package_v1/` → **44 passed**, exit **0**
  (2026-09-27); `ALLOW_DESTRUCTIVE_TEST_*=1` `poetry run pytest -m "integration and destructive_local"
  tests/integration/ai_package_v1/test_ch_pg_read_boundary.py` → **3 passed**, exit **0** (local PG
  `127.0.0.1:5433` + CH `127.0.0.1:8124`); `poetry run openspec validate ai-package-v1-contract
  --type change --strict` → **Change 'ai-package-v1-contract' is valid**; owed post-apply: §10.1–10.2
```

## LEGACY_BASELINE

- No AI Package v1 exporter in repo; strategy specs synced to `openspec/specs/`.
- Existing CH writers/readers: `full_wb_adv_stat`, `common_stat_manager` (not
  ZIP-aware).

## TARGET_REGRESSION

- Must not regress shop-runner write paths or invoke WB from new export module.
- Must not merge Auto/Search campaign stat rows in default export.
- Must not call `WBShopDataManager` or min-bids backfill from export path.

## FINAL_ACCEPTANCE

- Contract tests in `specs/ai-package-v1-contract-tests/spec.md` pass under
  `poetry run pytest -m unit` (and targeted integration where marked).
- `openspec validate ai-package-v1-contract --type change --strict` passes.
- `/opsx-planning-review change=ai-package-v1-contract` PASS (independent 2026-09-27;
  `PLAN_EVIDENCE_ID` SCPV1-39d14fba55537e56 — authoritative hashes in receipt only).
- `/opsx-verify change=ai-package-v1-contract` GO (pre-archive; run at apply
  boundary — not blocking task decomposition).
- `/opsx-spec-scenario-coverage change=ai-package-v1-contract mode=audit` PASS
  after official plan refresh (§0.4).
- Export produces ZIP with deterministic manifest sha256 on golden fixtures;
  shop orders/sales card shows `SOURCE_NOT_ASSIGNED`; no WB / shop-runner
  orchestrator spy calls.

---

## 0. Planning gates (this change)

- [x] 0.1 `/opsx-planning-review change=ai-package-v1-contract` — **PASS**
      (independent 2026-09-27; `PLAN_EVIDENCE_ID` SCPV1-39d14fba55537e56;
      `APPLY_PLANNING_GATE: PASS`; no blocking findings — not self-attested)
- [x] 0.2 `/opsx-verify change=ai-package-v1-contract` — **mode=impl IMPL_OK**
      (independent 2026-09-27; see header `IMPL_VERIFY_EVIDENCE`; **44** unit +
      **3** integration PASS + strict change validate PASS); archive **GO** still
      owed at apply/archive boundary (§10.2 — not blocking task decomposition)
- [ ] 0.3 Infra debt (separate chore, **not** apply slice): `opsx_ff` strict guard
      baseline `83874 > 80001` — Owner bumps
      `tools/openspec/openspec_guard.yaml` when ready; **never** waive mandatory
      gate or edit guard in exporter apply tasks. Working-tree modification of
      `tools/openspec/openspec_guard.yaml` predates this change (pre-apply chore
      debt — **not** created by exporter apply; do not revert/stage as slice work)
- [x] 0.4 Scenario coverage — **plan INPUTS current** (`mode=plan`,
      `PLAN_STATUS: ready`)
      - **26** scenario rows in authoritative plan
        (`scenario-coverage/plan.md` + `plan.receipt.json` `SCENARIO_COUNT`);
        source specs: `ai-package-v1-exporter/spec.md` 17,
        `ai-package-v1-contract-tests/spec.md` 9 (`#### Scenario:` headings)
      - `PLAN_EVIDENCE_ID`: `SCPV1-39d14fba55537e56` (supersedes
        `SCPV1-ce004c8dce3e693d`; tasks cite ID only; content hashes live in receipt
        `INPUTS` — **do not** embed in design/specs/owner-contract or edit receipt/
        plan manually)
      - Receipt `INPUTS` match current `design.md`, `owner-contract.md`, delta
        specs (official `/opsx-spec-scenario-coverage mode=plan`)
      - `SCENARIO_REQUIREMENTS_CONSUMED`: **plan=yes**; §2.2 scenario map **[x]**
        (design.md §Spec scenario test traceability); scenario **audit/certify** pytest
        evidence still **post-apply** (§10.1)
      - **Audit/certify** (`mode=audit` / certify) — **post-apply** (§10.1);
        no `/opsx-verify` GO or Product Acceptance proof claimed in tasks
- [x] 0.5 `/opsx-owner-contract-review change=ai-package-v1-contract` —
      `REVIEW_STATE: PASS`; `owner-contract.md` attested `REVIEWED` (D-001..D-005)

## 1. Discovery (scoped — stop if pretending runnable)

- [x] 1.1 PG scope evidence (shop_id, **no** snapshot-updater warmup filter):
      - Join: `AdvSetting` → `AdvSetting.wb_cabinet` → `WBCabinet.shop_id`
      - Models: `app/modules/common_slaves/wildberries/models/models.py`
        (`AdvSetting`: `adv_id`, `name`, `wb_cabinet_id`, `active_status`,
        `bot_active`, `nmids`, `_search_adv_id` / `search_adv_id` property,
        …) and `wb_cabinet.py` (`WBCabinet.shop_id`)
      - **Forbidden** as export scope template:
        `app/snapshot_data_updater/providers/postgres_provider.py` filter
        `AdvSetting.bot_active.is_(True)` + `active_status != done` (warmup-only)
      - **Reference** query shape (inventory, not bot_active-only):
        `WBShopDataManager.__get_advs(session, shop_id, only_bot_active=False)`
        — `active_status != 'done'`, optional `bot_active` only when
        `only_bot_active=True` (export MUST use `False`)
      - Distinguish in docs/card metadata:
        - **PG inventory** = rows returned by export scope query for `shop_id`
        - **WB all-campaign universe** = not discovered in v1; coverage MUST NOT
          imply FULL cabinet campaign list from inventory alone
        - **CH stat coverage** = separate dimension per dataset card
      - Detailed settings field allowlist → future change; v1 card
        `campaign_settings_snapshot` = minimal inventory or `UNKNOWN` + reason
- [x] 1.2 `PgExportShopScopeReader` seam (named, apply implements under
      `app/modules/ai_package_v1/scope/`):
      - Opens `get_async_session_maker(read_only=True)` (`session_maker.py`
        evidence); static SQLAlchemy select/join only
      - Builds in-process `ComplexAdv` / scope DTO **without** importing
        `WBShopDataManager`, `WBDataManager`, `WBManager`
      - If evidence cannot ground read-only session + query without shop-runner
        orchestrator → mark task **BLOCKED** in apply log; manifest card
        `UNKNOWN` — do not invent columns or orchestrator delegation

## 2. Tests first — contract suite (vertical slice 1)

- [x] 2.1 Create `tests/unit/ai_package_v1/` — contract suite (slice 1 vertical;
      §2.2 scenario map complete — see design.md traceability)
      - [x] 2.1a Static import guard: `ai_package_v1` has no forbidden WB API /
        `WBShopDataManager` imports (`test_import_guard.py`)
      - [x] 2.1b `SOURCE_NOT_ASSIGNED` shop orders/sales card
        (`test_shop_orders_card.py`; contract-tests: Orders sales unassigned)
      - [x] 2.1c Empty campaign stat ≠ FULL coverage claim
        (`test_coverage_rules.py`; contract-tests: Empty campaign stat)
      - [x] 2.1d Auto vs Search **original** `adv_id` rows preserved (no merge);
        shop isolation fixtures (`test_campaign_stat_grain.py`)
      - [x] 2.1e sha256 determinism (frozen clock) (`test_manifest_determinism.py`;
        contract-tests: Repeatable manifest / golden ZIP)
      - [x] 2.1f runtime spy: zero WB HTTP via
        `app.core/mp/wb/api` (or export boundary hook) on export path
        (`test_export_service.py`; contract-tests: Export spy shows no WB calls)
      - [x] 2.1g runtime spy: no instantiate/call
        `WBShopDataManager`, `backfill_min_bids_for_adv` from export path
        (`test_export_service.py`; import guard ≠ export-path spy)
      - [x] 2.1h funnel `orders` MUST NOT populate shop product
        orders/sales (`test_funnel_orders_boundary.py`; domain guard)
      - [x] 2.1i CH reader SQL spy: qualified `default_db.` in query text
        (`test_ch_campaign_stat_reader.py`, `test_ch_funnel_reader.py`, export path)
- [x] 2.2 Map **all 26** spec scenarios to tests or explicit audit rows after
      §0.4 plan regen (design traceability table — apply; see design.md §Spec
      scenario test traceability)
- [x] 2.3 Minimal golden fixtures (inline JSON/CSV bytes) before impl

## 3. Domain module skeleton

- [x] 3.1 Add `app/modules/ai_package_v1/domain/` — manifest schema, enums
      (`SOURCE_NOT_ASSIGNED`, coverage/reason codes per strategy semantics)
- [x] 3.2 Add `ExportService` orchestrator signature `export(shop_id, period) ->
      ExportResult` (domain manifest + payload map, no ZIP yet) — docstrings RU;
      inject `PgExportShopScopeReader` + CH readers only

## 4. Readers (read-only, qualified CH SQL)

- [x] 4.1 `ch_campaign_stat_reader` — SQL under `ai_package_v1/sql/` querying
      `default_db.full_adv_wb_stat` by scoped adv_ids + period (reuse patterns from
      `full_wb_adv_stat.py`)
- [x] 4.2 `ch_funnel_reader` — `default_db.wb_common_stat` filtered to
      `ComplexAdv.main_nmid` set only
- [x] 4.3 Wire `PgExportShopScopeReader` (§1.2) for shop-scoped adv ids + main
      nmids — **not** `wb_shop_data_manager.WBShopDataManager`

## 5. Shop orders/sales + coverage cards

- [x] 5.1 Emit `shop_product_orders_sales` dataset card metadata only
      (`SOURCE_NOT_ASSIGNED`, `UNKNOWN` fail-closed fields)
- [x] 5.2 Per-dataset `collection_outcome`, `coverage`, `reason_codes`,
      `freshness` — independent semantics (`export/dataset_cards.py` + freshness reader)
      - [x] 5.2a Domain rules: `collection_outcome` / `coverage` / `reason_codes`
        independent, fail-closed (`domain/coverage_rules.py`, `test_coverage_rules.py`)
      - [x] 5.2b `ChExportFreshnessReader` for per-dataset `freshness` only (not
        coverage substitute; `freshness_from_version_timestamp` never asserts FULL)

## 6. PG inventory card (conditional — not detailed settings snapshot)

- [x] 6.1 If §1.1–1.2 complete: minimal `pg_snapshot_reader` / inventory card
      (ids, relations, allowlisted columns only); else `campaign_settings_snapshot`
      card = `UNKNOWN` + reason — MUST NOT fake detailed settings rows
- [x] 6.2 Card metadata MUST state `PARTIAL` / inventory grain vs any WB-universe
      FULL claim

## 7. ZIP transport + validator

- [x] 7.1 `zip_transport` — encode manifest + payloads; per-file sha256
- [x] 7.2 Validator module used by contract scenarios S11/S12 (post §0.4 ids)
- [x] 7.3 `scripts/ai_package_v1_export.py` CLI (shop_id, period start/end,
      output path) — READ_ONLY, no TG

## 8. Integration tests (optional second slice)

- [x] 8.1 Integration test with `test_adv_bot_clickhouse` fixtures for
      `full_adv_wb_stat` + `wb_common_stat` row shapes (mark `@pytest.mark.integration`)
      — `tests/integration/ai_package_v1/test_ch_pg_read_boundary.py` (**3** tests,
      `@pytest.mark.integration` + `destructive_local`); **PASS** 2026-09-27 on local test
      PG `127.0.0.1:5433` + CH `127.0.0.1:8124` (`test_adv_bot_db` /
      `test_adv_bot_clickhouse`); pytest **3 passed**, exit **0** (`CACHE_MODE` OFF,
      destructive_local executed 3 / cached 0); command:
      `ALLOW_DESTRUCTIVE_TEST_DB=1` `ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1`
      `ALLOW_DESTRUCTIVE_TEST_SUBPROCESS=1` `poetry run pytest -m "integration and destructive_local"
      tests/integration/ai_package_v1/test_ch_pg_read_boundary.py -v`

## 9. Quality gates (apply)

- [x] 9.1 `poetry run pytest -m unit tests/unit/ai_package_v1/ -v`
- [x] 9.2 `poetry run pyright-strict` on new module paths
- [x] 9.3 `git diff --check`
- [x] 9.4 `openspec validate ai-package-v1-contract --type change --strict`

## 10. Post-apply OpenSpec

- [x] 10.1 `/opsx-spec-scenario-coverage` plan + audit PASS
      - Plan: `PLAN_EVIDENCE_ID` SCPV1-39d14fba55537e56 (`scenario-coverage/plan.receipt.json`)
      - Audit: `AUDIT_EVIDENCE_ID` SCAR-06a07a1142979015 (`scenario-coverage/audit.receipt.json`);
        `VERDICT=PASS` `PASS_SCOPE=FULL_CHANGE` 26/26; executed 2026-09-29 (`CACHE_MODE=OFF`,
        `poetry run pytest -m unit tests/unit/ai_package_v1/` → **75 passed**;
        `ALLOW_DESTRUCTIVE_TEST_*=1` `poetry run pytest -m "integration and destructive_local"
        tests/integration/ai_package_v1/` → **6 passed** on PG `127.0.0.1:5433` + CH `127.0.0.1:8124`)
      - Next gate: `/opsx-spec-scenario-coverage mode=certify change=ai-package-v1-contract`
        (fresh `PROVIDER_EXECUTION_RECEIPT` when required — not claimed by audit PASS alone)
- [ ] 10.2 `/opsx-verify` then archive decision promotion for
      `ai-package-v1-exporter-ownership` when Accepted

---

**Explicit non-tasks:** collectors, DDL, WB API collect, `inc-ro-08`, GUI/TG,
shop-wide funnel export, silent Auto+Search merge, detailed campaign settings
snapshot export, `openspec_guard.yaml` baseline bump inside exporter PR.
