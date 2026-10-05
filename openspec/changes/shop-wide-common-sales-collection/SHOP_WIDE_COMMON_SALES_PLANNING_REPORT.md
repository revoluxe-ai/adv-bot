# SHOP_WIDE_COMMON_SALES_PLANNING_REPORT

TASK_ID: WB-SKY-COMMON-SALES-PLAN-CLOSE-20261005-0130
Generated: 2026-10-05 (MSK planning close session)

## WORKTREE

`C:\Users\vkita\my_code\meta-repo\shop-wide-common-sales-collection`

## BRANCH

`shop-wide-common-sales-collection`

## BASE_HEAD

`62c8d48b15498997b84357e015b0e688f44fd37b` (actual committed local stage/worktree HEAD)

## PRIOR_INDEPENDENT_REVIEW

| Field | Value |
|-------|-------|
| Review task | `WB-SKY-COMMON-SALES-PLAN-REREVIEW-20261005-0120` |
| Reviewer status | Owner contract PASS; planning REPAIR_REQUIRED (P-001, P-002) |
| Coordinator disposition | **NO_GO** at planning gate — blockers repaired in this close session |
| Self-certification | **NOT PERFORMED** — awaits independent rereview |

## CAMPAIGN_CHANGE_RECONCILED

**YES**

Sibling receipt: `COMMON_SALES_BOUNDARY_RECONCILIATION.md`
(`TASK_ID: WB-SKY-COMMON-SALES-RECONCILE-20261005-0100-R2`, `CAMPAIGN_CHANGE_RECONCILED: YES`).

## PLANNING_REPAIR_BLOCKERS (R1–R9)

| ID | Status | Repair |
|----|--------|--------|
| R1 | PASS | Single coordinator inside existing `update_common_sale_stat`; frozen A/E/U |
| R2 | PASS | Every tick full E+U recollection; CH argMax never skip gate |
| R3 | **CLOSED (P-001)** | Exhaustive 25+1 TaskGroup registry in `design.md`; normative criterion; minimal `taskgroup_no_ad_supervisor` at WBShop task factory (18 members); coordinator exempt; S04b–S04e + AST guard |
| R4 | **CLOSED (P-002)** | Reject invalid/conflicting facts; STARTED before API; no false COMPLETE on CH failure; S07b–S07f, S11b–S11c |
| R5 | PASS | `\|E\|/\|U\|` SKU counter semantics |
| R6 | PASS | Transitions, pagination (S01c terminal boundary), null vs zero, mid-batch, argMax, forbidden writes |
| R7 | PASS | Sibling receipt; CAMPAIGN_CHANGE_RECONCILED=YES |
| R8 | PASS | BASE_HEAD 62c8d48…; scenario receipt regenerated (see below) |
| R9 | PASS | Task-owned CH proof via `validate_destructive_clickhouse_endpoint` + `test_adv_bot_clickhouse`; destructive tests not run at planning close |

## P-001 CLOSE SUMMARY

- Inspected **all 26** TaskGroup registrations (`wb_shop.py` L58–89).
- **18** call `get_complex_advs` or `get_pre_complex_advs` without local NotFound handling → **supervisor required**.
- **1** exempt: `update_common_sale_stat` (coordinator `_resolve_legacy_assigned_nmids` seam).
- **6** no loader path (including `refresh_stats_freshness_cache` canonical risk sibling — **supervisor required** among the 18).
- Minimal placement: `taskgroup_no_ad_supervisor` at WBShop `create_task` factory (not per-body edits); global `while_coroutine_decorator` unchanged.

## P-002 CLOSE SUMMARY

- Normative requirement: reject unexpected nmid, out-of-window dates, conflicting duplicates, non-finite metrics.
- Identical duplicates dedup deterministically; never invented-zero or cross-shop rows.
- Partial success per nmID; per-source request identity/window validation.
- `attempt_status=STARTED` before first funnel API await.
- Repaired S06 (split full 500/120/380 from U-only 25 remainder S06c).
- S01c terminal pagination (5 full pages + empty page 6).
- S12 task-owned CH endpoint proof (not port-only).

## ALL_SHOP_NMID_SOURCE

**ProductsManager.get_cards_list** (Content API pagination; trash excluded; fail-explicit null/partial).

## EXISTING_COVERED_SOURCE

This tick's API returned pairs + assortment proof + Redis last-attempt (`attempt_status` lifecycle). CH argMax read-latest only.

## COMMON_COLLECTOR_REUSE

**YES** — shared funnel adapter, batch 20, DTO, `ClickHouseCommonStatManager.insert`.

## NEW_CODE_REQUIRED

| Unit | Purpose |
|------|---------|
| `ShopAssortmentReader` | Paginate A |
| `_resolve_legacy_assigned_nmids` | Coordinator NotFound → E=∅ |
| Coordinator body | A/E/U partition, validation, Redis evidence |
| `taskgroup_no_ad_supervisor` | WBShop.run task factory wrapper (18 registry members) |
| Returned-fact validator | Reject invalid/conflicting API facts before CH insert |

## WB_COMMON_STAT_OWNERSHIP

Single coordinator (`update_common_sale_stat`); disjoint E/U routes; no second coroutine.

## RUNTIME_FLOW

```
WBShop TaskGroup
  update_common_sale_stat  [SINGLE COORDINATOR — local E=∅ seam]
    → A/E/U → validate facts → STARTED → collect E+U → Redis terminal evidence → CH insert

  other registered coroutines (18 loader-path)
    → taskgroup_no_ad_supervisor(create_task wrapper)
```

## HISTORY_BACKFILL

**DEFERRED**

## NUMERATOR_STATUS

**BLOCKED_BY_CAMPAIGN_COVERAGE**

## TEST_PLAN

| ID | Scope |
|----|-------|
| S01–S01c | Assortment pagination + terminal boundary |
| S03–S06c | Partition + batch 20 (full matrix vs U-25 remainder split) |
| S04–S04e | No-ad TaskGroup survival + registry AST + negative auth/other-stop |
| S07–S07f | Missing/null + invalid/conflicting rejection |
| S11–S11c | Last-attempt STARTED/COMPLETE honesty |
| S12 | Task-owned CH integration (authored; not run at planning close) |
| S13–S15 | Boundaries |

## PLANNING_REVIEW

**READY_FOR_REVIEW** — independent rereview required; no self-certification.

```text
/opsx-planning-review change=shop-wide-common-sales-collection
```

## IMPLEMENTATION_READY

**YES** — independent rereview PASS (`WB-SKY-COMMON-SALES-PLAN-FINAL-REVIEW-20261005-0135`).

## BLOCKERS

| ID | Severity | Description |
|----|----------|-------------|
| B1 | **CLOSED** | Independent rereview PASS — receipt `WB-SKY-COMMON-SALES-PLAN-FINAL-REVIEW-20261005-0135/result.json` |
| B3 | Evidence | Live production CH DDL introspection blocked — explicit non-production limitation |

**Resolved:** B2 sibling campaign; P-001 R3 registry; P-002 R4 invalid/conflicting facts.

## SCENARIO RECEIPT (CURRENT)

| Artifact | SHA256 |
|----------|--------|
| design.md | `07ea6d4d241eae80785b53ee3b7ae2d36f750b8ed3def29e5eeb4dd03c4929c9` |
| spec.md | `5e24eabdaa2f6bf4daaa494ea6bbca5da73dd443e0540d7568acbca78b508253` |
| owner-contract.md | `1ef750fb242b6092aa375c815de39557b9a1d78c36f3a9486a1ffd35c95817af` |
| plan.md | `c7e5882345385f9f1c39dc2e252b58c0b10a2c9319efab9a1ad16cb1f834d4a0` |
| PLAN_EVIDENCE_ID | `SCPV1-shop-wide-common-sales-20261005-close` |
| Supersedes | `SCPV1-shop-wide-common-sales-20261005-repair` |
| SCENARIO_COUNT | 33 |

Hash mechanism: SHA256 of LF-normalized UTF-8 file bytes per
`.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md`.

## VALIDATION RECEIPTS

```text
git rev-parse HEAD → 62c8d48b15498997b84357e015b0e688f44fd37b
git diff --check → exit 0
openspec validate shop-wide-common-sales-collection --type change --strict --json → valid: true, issues: []
python openspec/tools/check_config_contract.py → passed
```

## PLANNING_REPAIR_RECEIPT

```text
TASK_ID: WB-SKY-COMMON-SALES-PLAN-CLOSE-20261005-0130
STATUS: COMPLETE
MODE: write (documentation only)
PRIOR_REVIEW: WB-SKY-COMMON-SALES-PLAN-REREVIEW-20261005-0120 (P-001/P-002 blockers)
BASE_HEAD: 62c8d48b15498997b84357e015b0e688f44fd37b
CAMPAIGN_CHANGE_RECONCILED: YES
READY_FOR_REVIEW: YES
IMPLEMENTATION_READY: NO (await independent rereview)
INDEPENDENT_PASS_CLAIMED: NO
```
