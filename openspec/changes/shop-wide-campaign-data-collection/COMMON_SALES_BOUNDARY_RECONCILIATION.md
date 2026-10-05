# Common-Sales Ownership Boundary Reconciliation

```text
RECONCILIATION_RECEIPT

TASK_ID: WB-SKY-CAMPAIGN-COLLECTION-TASK-AUTHORITY-RECONCILE-20261005-0415
CHANGE_ID: shop-wide-campaign-data-collection
MODE: documentation-only (planning authority reconcile)
STATUS: COMPLETE
DATE: 2026-10-05
CAMPAIGN_CHANGE_RECONCILED: YES
PRIOR_RECEIPT: WB-SKY-COMMON-SALES-RECONCILE-20261005-0100-R2

MIGRATION_RECONCILE_TASK_ID: WB-SKY-CAMPAIGN-COLLECTION-PLAN-RECONCILE-20261005-0405-R2
MIGRATION_SEQUENCE: 007 (was 006 in feature worktree)
MIGRATION_COLLISION: stage merge owns 006_create_campaign_settings_history.sql
CH_MIGRATION_CONTROL_PLANE: READY (ledger/target); PG advisory-lock coordinator only

IMPLEMENTATION_FRONTIER: VERIFY / merge-review
PROVEN_COMPLETE: §1–§9.3 (code + 82 targeted unit tests; scenario acceptance 2026-10-05)
OPEN_APPLY: none
```

## Owner boundary applied

| Owner | Responsibilities |
|-------|------------------|
| **`shop-wide-common-sales-collection`** | Shop-wide product/funnel expansion `(nmid, date)`; assortment universe; uncovered `(nmid, date)` routing; common collector; `wb_common_stat` writer; common-sales coverage; coordinator for legacy `CommonSaleStatUpdater` |
| **`shop-wide-campaign-data-collection`** | WB campaign discovery; `shop_campaign_inventory` / `shop_campaign_collection_availability`; campaign advertising universe; `full_adv_wb_stat` `(adv_id, date)`; managed-only `clusters_adv_stats` |

## Removed competing writer obligations

The following **removed** from campaign change normative docs:

- Unmanaged slice `get_sales_funnel_products_history` + `ClickHouseCommonStatManager.insert` (design §D.3, tasks §4.1).
- Resolver grain `wb_common_stat` `(nmid, date)` (tasks §3.1).
- Unmanaged funnel write acceptance in spec grains table and S13 scenario.
- `LEG_UNMANAGED` funnel adapters in design Semantic Write Target.
- UNMANAGED path `wb_common_stat` in architectural debt table.
- Scenario plan THIN_ENDS / S13 / S17 / S22 assuming campaign `ClickHouseCommonStatManager` writes.

## Remaining campaign responsibilities (unchanged)

- Temporary dual-path shop-runner orchestration (managed legacy RECORD + unmanaged read-only).
- `CampaignCollectionRouteResolver` for `full_adv_wb_stat` and managed-only `clusters_adv_stats`.
- WB discovery, inventory, availability, route epoch, non-atomic handoff.
- Proven-complete apply slice §1–§9.3: legacy baseline through shop-runner
  orchestration, handoff/reconcile, scenario acceptance S01–S22 (direct code +
  unit test evidence in `tasks.md` and `scenario-coverage/acceptance.receipt.json`).
- Implementation frontier: **VERIFY / merge-review** (no open apply tasks).
- Management invariants: no AdvSetting create, no `bot_active` mutation, no scripts/Job executor.
- Cluster stats gap on unmanaged path (debt §D.4) unchanged.

## Legacy handoff preserved

- Managed `CoroutinesManager.update_common_sale_stat` → `CommonSaleStatUpdater` for loader universe §B.1 **documented as existing route**, not a new campaign writer.
- Coordination of shop-wide `(nmid, date)` expansion explicitly deferred to **`shop-wide-common-sales-collection`**.

## Scenario plan evidence regeneration

| Field | Prior (invalidated) | Current |
|-------|---------------------|---------|
| `PLAN_EVIDENCE_ID` | `SCPV1-10e934c6b4b577d5` | `SCPV1-0e11e1d5c3a8b2bb` |
| `PLAN_CONTENT_HASH` | `eaf6949b0cf1a7c78062f7c2f7b6ca6a09835ae22c4e9582da6f8ba4b67be64c` | `9a82cf6b4b0286f0807e8bdef800eaf28c8f62fa1829c25232b4bbdd04ec02d4` |
| `design.md` hash | `ac877bdef4835f65e16ff3fd11eb7fb72374c53c11bd5b8bd4ab6da3be144cf3` | `ed14f3def581a336c19930fbecd2b14ed5c01bee24707ac8e9e34a8a20620c55` |
| `spec.md` hash | `f5eaeb6f7bc3558f048c0cc4143157f121fbb14bb7be9aaa0a492d757ff8ee76` | `1104371ec73e146256cbba8f42ae57f48f16415f3bdbbc844b4bd84392eb9679` |

Prior receipt `SCPV1-10e934c6b4b577d5` **MUST NOT** be treated as current after this reconciliation.

## ClickHouse migration sequence (2026-10-05 plan reconcile)

| Evidence | Resolution |
|----------|------------|
| Stage merge | `006_create_campaign_settings_history.sql` occupies sequence **006** |
| Feature worktree (prior) | `006_create_shop_campaign_inventory_and_availability.sql` — **collision** |
| Reconciled | Renamed to `007_create_shop_campaign_inventory_and_availability.sql`; semantic DDL unchanged |
| Control plane | ClickHouse migration ledger/target READY in stage; PostgreSQL **not** CH migration ledger — advisory-lock coordinator only |

Feature-local references updated: `tasks.md` §2.1, DDL unit test, upsert test docstring, `design.md` Migration Plan.

## Files changed (authority reconcile 2026-10-05)

1. `openspec/changes/shop-wide-campaign-data-collection/COMMON_SALES_BOUNDARY_RECONCILIATION.md` (this receipt)
2. `openspec/changes/shop-wide-campaign-data-collection/tasks.md` (frontier metadata + §2.3 gate narrative)

**Prior common-sales / migration reconcile (unchanged this task):**
`design.md`, `proposal.md`, `spec.md`, `decisions/`, `scenario-coverage/plan.md`,
`plan.receipt.json`, `TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md`, migration **007**, DDL tests.

**Not modified:** normative `design.md` / `spec.md` / `plan.md` hashes (scenario receipt
CURRENT); `owner-contract.md`; §3–§6 code/tests; guard (`opsx_update.baseline_chars`
100181 preserved).

## Implementation authority (2026-10-05 task reconcile)

Independent review found planning/task authority drift: historical handoff claimed
only §1–2 complete and implied apply blocked until resolver §3.1. **Disk evidence
outranks handoff:** local code under `app/modules/shop_runner/shop_wide_collection/`
and eight targeted unit suites prove §3.1–§6.3 implemented; 66 targeted tests passed
in bounded verify. Planning artifacts reconciled to that state — **no reset** of valid
§3–§6 implementation.

| Slice | Status | Evidence role |
|-------|--------|---------------|
| §1–§2 | Complete | Legacy baseline, write-gates, DDL **007**, inventory upsert, feature flag |
| §3 | Complete | `route_resolver.py`, `test_campaign_collection_route_resolver.py` |
| §4 | Complete | `unmanaged_orchestrator.py`, `test_unmanaged_campaign_collector.py` |
| §5 | Complete | `managed_record_contract.py`, `test_managed_path_preservation.py` |
| §6 | Complete | `test_partial_failure_availability_read_latest.py`, read-latest helpers |
| §7–§8 | Complete | Handoff S16–S19, S22 reconcile, shop-runner orchestration S01/S20 |
| §9 | Complete | Scenario acceptance S01–S22; pyright-strict; quality gates |

Feature flag fail-closed gate (task §2.3): resolver §3.1 **is implemented**; ON no
longer defers unmanaged collector for missing resolver — gate satisfied.

## Planning evidence debt

- **`shop-wide-common-sales-collection`** change artifacts not present in this worktree — downstream feature must materialize its own spec/design/tasks/scenario plan for `(nmid, date)` coverage.
- Campaign apply §1–§9.3 complete in this worktree; next step is VERIFY / merge-review.

## Validation (authority reconcile 2026-10-05)

| Check | Result |
|-------|--------|
| `openspec validate shop-wide-campaign-data-collection --strict` | PASS |
| Scenario receipt integrity (`PLAN_CONTENT_HASH`, INPUTS hashes) | CURRENT |
| `git diff --check` | PASS |
| Targeted pytest (10 shop_runner suites, 82 tests) | 82 passed |
| Scenario acceptance (`acceptance.receipt.json`) | S01–S22 certified |
| Guard `opsx_update.baseline_chars` | 100181 preserved (unchanged) |

Scenario receipt **not** regenerated — normative artifact hashes unchanged.
