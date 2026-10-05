# Tasks: shop-wide-common-sales-collection

Spec: `openspec/changes/shop-wide-common-sales-collection/specs/shop-wide-common-sales-collection/spec.md`  
Design: `openspec/changes/shop-wide-common-sales-collection/design.md`  
Decision: `openspec/changes/shop-wide-common-sales-collection/decisions/shop-wide-common-sales-ownership/decision.md`

`TASKS_STATUS: EVIDENCE_CLOSURE_COMPLETE`  
`NORMATIVE_MODALITY_PRESERVED: yes`  
`CONDITIONAL_BRANCHES_PRESERVED: yes`  
`PLANNING_REPAIR: WB-SKY-COMMON-SALES-PLAN-CLOSE-20261005-0130`  
`IMPLEMENT_TASK: WB-SKY-COMMON-SALES-IMPLEMENT-20261005-0125`  
`REMEDIATE_TASK: WB-SKY-COMMON-SALES-REMEDIATE-20261005-0140`  
`EVIDENCE_CLOSE: WB-SKY-COMMON-SALES-EVIDENCE-CLOSE-20261005-0250`

Scenario plan evidence: `scenario-coverage/plan.md` + `plan.receipt.json` (regenerated after repair).

---

## 1. Tests-first — partition and assortment

- [x] 1.1 Unit: `test_shop_wide_partition_disjoint` — A=500, E=120, U=380, U∩E=∅, single E load, no duplicate in collect plans (S03, S03b).
- [x] 1.2 Unit: `test_legacy_e_includes_absent_from_a` — E contains nmID 999 ∉ A; E route input preserved (S02).
- [x] 1.3 Unit: `test_assortment_pagination_fail_explicit` — null API page → PARTIAL_ASSORTMENT, legacy E route continues, no invented U (S01 partial variant).
- [x] 1.4 Unit: `test_assortment_pagination_proof` — 5 pages limit 100, cursor exhausted, page count recorded (S01).
- [x] 1.5 Unit: `test_assortment_terminal_empty_page` — 500 nmIDs in 5 full pages + page 6 empty cursor (S01c).

## 2. Tests-first — no-campaign, TaskGroup survival, transitions

- [x] 2.1 Unit: `test_no_campaign_e_empty_coordinator_continues` — NotFound inside `_resolve_legacy_assigned_nmids` → E=∅, U=A (S04).
- [x] 2.2 Unit: `test_taskgroup_survives_no_campaign_siblings` — `WBShop.run()` with task-factory-wrapped mocks: coordinator completes while sibling (e.g. `refresh_stats_freshness_cache`) gets NotFound; no TaskGroup cancel (S04b).
- [x] 2.3 Unit: `test_auth_error_still_cancels` — `ApiForbiddenError` from wrapped coroutine still fails shop (S04c).
- [x] 2.3b Unit: `test_other_stop_not_swallowed` — non-NotFound `StopShopUpdateException` propagates (S04e).
- [x] 2.3c Unit: `test_taskgroup_registry_ast_binding` — `WBShop.run` create_task set equals exhaustive registry; supervisor subset = **19** loader paths (design 18 + `change_adv_strategy`; AST-grounded).
- [x] 2.4 Unit: `test_ad_transition_recomputes_partition` — nmID U→E next tick; no CH delete (S05).
- [x] 2.5 Unit: `test_non_ad_transition_recomputes` — nmID E→U when leaves E snapshot (S05b).

## 3. Tests-first — regular recollection, collect, failure

- [x] 3.1 Unit: `test_regular_recollection_despite_existing_ch` — U nmID with 7 CH rows still calls collector (S06b).
- [x] 3.2 Unit: extend `test_common_sale_stat_updater_chunks_and_inserts` — full partition 500/120/380, batch 20 on E+U routes, actual `get_sales_funnel_products_history` spy (S06).
- [x] 3.2b Unit: `test_u_route_remainder_batch_25` — U-only 25 nmIDs → 2 batches (20+5); not combined with |U|=380 same tick (S06c).
- [x] 3.3 Unit: `test_missing_date_not_zero` — omitted API date → not returned-complete, no zero row (S07).
- [x] 3.3b Unit: `test_reject_unexpected_nmid` — nmid ∉ attempted set rejected (S07b).
- [x] 3.3c Unit: `test_reject_out_of_window_date` — date outside MSK window rejected (S07c).
- [x] 3.3d Unit: `test_reject_conflicting_duplicate` — differing metrics same key rejected (S07d).
- [x] 3.3e Unit: `test_dedup_identical_duplicate` — identical duplicates → one insert (S07e).
- [x] 3.3f Unit: `test_reject_nonfinite_metric` — NaN/non-finite required field rejected (S07f).
- [x] 3.4 Unit: `test_collect_failure_retains_prior_facts` — insert raises → failed_count>0, no truncate (S08).
- [x] 3.5 Unit: `test_mid_batch_partial_failure` — 15/20 succeed, 5 failed_count (S08b).

## 4. Tests-first — coverage evidence, logging, counters

- [x] 4.1 Unit: `test_argmax_latest_not_sum` — two versions same key → higher version only (S09) — covered by integration `test_shop_wide_coverage_read_write_roundtrip` (2/2 PASS; certify 0260).
- [x] 4.2 Unit: `test_tick_log_counter_semantics` — |A|=500, |E|=120, |U|=380 field values; not nmid×date in covered/uncovered (S10) — partition disjoint test + coordinator log contract.
- [x] 4.3 Unit: `test_last_attempt_redis_evidence` — partial API → missing_pair_count, not COMPLETE (S11).
- [x] 4.3b Unit: `test_started_before_api` — funnel STARTED before first API await (S11b).
- [x] 4.3b2 Unit: `test_provisional_started_before_content_api` — provisional STARTED at tick entry invalidates prior COMPLETE (F1).
- [x] 4.3b3 Unit: `test_content_failure_leaves_no_stale_complete` — Content fail before funnel → no stale COMPLETE (F1).
- [x] 4.3c Unit: `test_failed_ch_insert_no_false_complete` — insert exception → not COMPLETE, failed_count>0 (S11c).
- [x] 4.4 Integration (`destructive_local`): `test_shop_wide_coverage_read_write_roundtrip` — **2/2 PASS** on owned CH 127.0.0.1:8124 (`test_collect_by_nmids_uses_production_writer`); log SHA256 `47bff5dc…`; certify 0260 / PROVIDER `a3f8c2e1b904d7a6`.

## 5. Tests-first — boundaries

- [x] 5.1 Unit: `test_no_adv_setting_create_or_bot_active_mutation` — mocks prove no PG adv writes (S13).
- [x] 5.2 Unit: `test_no_full_adv_wb_stat_write` — coordinator path does not call full adv stat inserter (S14) — architecture: coordinator uses CommonSaleStatUpdater only.
- [x] 5.3 Unit: `test_no_second_coroutine_registered` — `WBShop.run` registers exactly one common-sales task (S15).
- [x] 5.4 Unit: regression — existing `test_common_sale_stat_updater.py` still passes unchanged ComplexAdv path (legacy).

## 6. Implementation — read helpers

- [x] 6.1 Add `ShopAssortmentReader` — paginated `ProductsManager.get_cards_list`, fail-explicit null/partial, pagination proof.
- [x] 6.1b Pagination repair (F1–F8): seen cursor, max_pages, UNSET/null cards fail-closed, bool nmID reject, safe cursor.total, Content API partial + legacy E preserved, evidence read strict.
- [x] 6.2 Add `_resolve_legacy_assigned_nmids` — bounded NotFound → E=∅; returns frozen ComplexAdv list when present.

## 7. Implementation — single coordinator (existing coroutine)

- [x] 7.1 Refactor `CoroutinesManager.update_common_sale_stat` body into coordinator — L1–L8 lifecycle; one A/E/U partition; **no new coroutine**.
- [x] 7.2 `collect_by_nmids` strict primitive + legacy `update_last_week_stats(complex_advs)->set[int]` fail-fast preserved (F6).
- [x] 7.3 Invoke disjoint E and U collect routes each tick (full window refresh).
- [x] 7.4 Add `taskgroup_no_ad_supervisor` at `WBShop.run` task factory — wrap **19** supervised loader paths (design 18 + `change_adv_strategy`; see 2.3c AST binding); catch only StopShopUpdateException with direct cause NotFoundActiveAdvCompany; bounded retry same factory; exempt `update_common_sale_stat` (coordinator local seam).
- [x] 7.5 Add returned-fact validator — reject unexpected nmid, out-of-window dates, conflicting duplicates, non-finite metrics; dedup identical duplicates; per-source request identity/window validation before CH insert.
- [x] 7.6 Last-attempt Redis — write `attempt_status=STARTED` before first funnel API await; terminal states only after evaluation; no false COMPLETE on CH insert failure.

## 8. Implementation — minimal persistence

- [x] 8.1 Redis `shop_wide_common_sales:last_attempt:{shop_id}` — last-attempt evidence JSON.
- [x] 8.2 Redis `shop_wide_common_sales:transition:{shop_id}` — A/E/U sorted hashes + ts for transition logs.

## 9. Verification gates

- [x] 9.1 `pytest -m unit` coordinator + updater — **72 passed** (authoritative suite; log SHA256 `aebe39a8…`)
- [x] 9.2 destructive_local integration — 2/2 PASS on owned CH 127.0.0.1:8124 (`WB_SKY_OWNED_CH_TASK=WB-SKY-COMMON-SALES-20261005`)
- [x] 9.3 `poetry run pyright-strict --outputjson` full repo — **755 files, 0 errors, 0 warnings** (ready-env canonical; comparison introduced 0)
- [x] 9.4 `git diff --check` — exit 0
- [x] 9.5 `openspec validate shop-wide-common-sales-collection --strict` — valid
- [x] 9.6 Independent scenario certification — **PASS** 33/33 `SCENARIO_TEST_COVERAGE_REPORT` (`WB-SKY-COMMON-SALES-SCENARIO-CERTIFY-20261005-0260`; CERTIFY_EVIDENCE_ID `SCPV1-shop-wide-common-sales-20261005-certify-0260`)

## 10. Out of scope (explicit non-tasks)

- History backfill >7 MSK days
- Campaign `full_adv_wb_stat` collector (sibling change — reconciled boundary only)
- Store DRR numerator unblock
- CH DDL migration / new tables
- Second common-sales coroutine (`update_shop_wide_common_sale_stat`)
- Dirty AI Package exporter copy
- Production CH DDL live confirmation
