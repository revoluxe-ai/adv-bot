# Owner Contract — ai-package-v1-contract

## Status

`REVIEWED` — independent `/opsx-owner-contract-review change=ai-package-v1-contract`
returned `REVIEW_STATE: PASS` (READ_ONLY; 2026-09-27; review command does not
mutate artifacts). Confirmed semantics below (`D-001`–`D-005`). Production apply
still requires separate Owner GO; no GO token is recorded here.

## Confirmed Owner decisions (review cycle)

- **D-001:** MVP = versioned ZIP from **already accumulated** PostgreSQL +
  ClickHouse only, with **truthful** per-dataset `coverage` / `reason_codes` (no
  silent full-history or full WB-cabinet-universe claims).
- **D-002:** **Detailed** advertising campaign **settings** snapshot (full
  field-level settings export) is **out of v1** — future change
  `ai-package-campaign-settings-snapshot`; not a v1 completion criterion.
- **D-003:** Minimal PG **campaign inventory / relations** (shop-scoped
  `AdvSetting` rows, ids, join to `WBCabinet.shop_id`, Auto/Search id linkage)
  MAY appear only with proven read-only PG seam and explicit `PARTIAL` /
  `UNKNOWN` when detailed settings are unavailable — MUST NOT silently promise
  detailed settings rows.
- **D-004:** Shop product orders/sales MUST remain explicitly
  `SOURCE_NOT_ASSIGNED` / `UNKNOWN`; funnel/ad/supplier feeds MUST NOT stand in.
- **D-005:** Export path MUST stay read-only: no WB API, no collectors, no
  `WBShopDataManager` / min-bids orchestration; Auto (shelf) and Search
  (keywords) campaign ids MUST remain separate original rows in scope and CH stat
  export.

## Owner direction (intent — aligned with D-001..D-005)

2026-09-27 Owner affirmed in planning hop (chat, this worktree); review PASS
confirms durable representation in this contract and downstream specs.

## Intent

Bounded production read-only AI Package v1: `shop_id` + период → versioned ZIP
с manifest и `sha256`, только накопленные PG/CH.

## In scope

- Доменный контракт пакета и ZIP transport.
- Dataset cards с provenance, grain, coverage dimensions.
- Campaign full stat из `default_db.full_adv_wb_stat` (campaign+date).
- Funnel/common из `default_db.wb_common_stat` только main `nmid` ComplexAdv.
- PG **inventory / relations** card (minimal read-only fields from `AdvSetting` +
  `WBCabinet.shop_id` join) — **not** detailed settings snapshot; card MUST
  state partial/unavailable semantics when discovery incomplete.
- Shop product orders/sales: явно `SOURCE_NOT_ASSIGNED` / `UNKNOWN`.
- Contract tests и validator (no WB, no shop-runner orchestrator on export path,
  fail-closed UNKNOWN).

## Out of scope

- Collectors, backfill, CSV, DDL, WB API из экспортёра.
- `shop-wide-campaign-data-collection`, `inc-ro-08-orders-sales-period-collect`.
- GUI/TG, AI JSON response, preview/apply, prod campaign writes.
- **Detailed** campaign/settings snapshot export (future change above).
- WB-discovered “all campaigns in cabinet” universe as v1 coverage claim.
- Other worktrees.

## Acceptance (planning)

- Specs покрывают MUST из Owner brief и Accepted `shop-data-source-strategy`.
- Design cites decisions, names placement from repo evidence (no invented DDL).
- Tasks: tests-first vertical slice; planning gates pending independent
  planning-review PASS and receipt INPUTS gate (tasks §0.1, §0.4).
- Scenario **plan** traceability: authoritative
  `scenario-coverage/plan.receipt.json` (`SCENARIO_COUNT`, `INPUTS` hashes
  checked at gate — see tasks §0.4); refresh official `mode=plan` after
  planning-input edits to `design.md` / this contract. **Audit/certify**
  (`mode=audit`) is post-apply and does not substitute for PA
  `SIDE_EFFECT_PROOF`.

## Owner constraints (normative)

- MUST NOT borrow funnel or ad orders for shop product orders/sales.
- MUST NOT silent success when source missing.
- MUST NOT fake coverage from timestamps or imply full history / full WB campaign
  universe from PG inventory alone.
- Auto (shelf) and Search (keywords) MUST remain separate original rows /
  `adv_id` values in export scope and CH stat rows.
- MUST NOT import or call `WBShopDataManager` orchestrator, `_get_min_bids`,
  `backfill_min_bids_for_adv`, or any WB HTTP API on export path.
