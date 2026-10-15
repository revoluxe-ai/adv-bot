---
cursor:
  subagentId: "bc-67b2f562-013b-5bf6-afa1-c746a73c45d5"
---

# Slice B independent review (`cursor/attribution-facts-contract-slice-b-89e7`)

**Verdict: REPAIR_REQUIRED**

Branch/commit reviewed: `b9224f876` feat(attribution-facts): Slice B ingest and membership resolver.

## Verification matrix

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Raw apps/nms before DayStats collapse | **PASS** — `maybe_ingest_fullstats_chunk` runs before `full_stats_item_to_full_adv_stat` in `fullstats/adapter.py`; normalizer walks `days→apps→nms`. |
| 2 | History over inventory | **PASS** — `MembershipSnapshotResolver.resolve` queries history first; inventory only if history misses. |
| 3 | Inventory fallback → PARTIAL, not COMPLETE | **FAIL** — see HIGH finding. |
| 4 | Missing membership → UNKNOWN | **PASS** — `classify_ordered_nm` with `snapshot=None` → UNKNOWN; S07 batch test. |
| 5 | Physical adv grain | **PASS** — `AttributionFactKey.physical_adv_id`; separate resolver per advertId; `allow_pair_aggregate: False`. |
| 6 | No spend duplication | **PASS** — ingest in-memory only; metrics exclude spend; `full_adv_wb_stat.insert` unchanged sole spend write. |
| 7 | No Slice C CH persistence/DDL | **PASS** — no observation DDL; CH adapters read history/inventory only. |
| 8 | S05–S09 vs tests/receipt | **PARTIAL** — see MEDIUM findings; receipt overstates S06. |

## Findings

### HIGH — Inventory fallback can yield `COMPLETE` coverage (criterion 3 / S06)

`coverage_for_ingest_source` and `evaluate_window_coverage` append `ATTRIBUTION_SOURCE_PARTIAL` to `reason_codes` when `partial_membership_fallback=True`, but still return `AttributionCoverageStatus.COMPLETE` when reconciliation passes (`ingest_models.py` ~90–101, `coverage.py` ~66–96).

Effect: `can_emit_direct_linked_economics(coverage)` is true after inventory-only membership, so DIRECT/LINKED CPO/DRR are allowed despite scenario plan S06 (“THEN PARTIAL”) and explicit review criterion “not COMPLETE”.

`test_s06_inventory_fallback_partial` only asserts `resolved.partial_fallback` and resolver reason codes — not `batch.coverage.status`.

### MEDIUM — S06 scenario receipt truthfulness

`slice-b-l1-audit.receipt.json` marks S06 PASS on resolver-only evidence; does not prove ingest coverage stays PARTIAL or economics stay blocked.

### MEDIUM — S07 slice-B test narrower than scenario plan

`test_s07_missing_membership_fail_closed` checks fact `UNKNOWN` only. Plan S07 also targets economics fail-closed (covered in Slice A `test_s07_*` on derived metrics, not end-to-end on `build_ingest_batch` coverage). Batch may report `COMPLETE` when reconciliation passes but all rows are UNKNOWN — economics blocked by zero denominator, not `BLOCKED_BY_ATTRIBUTION_FACTS`.

### LOW — Spec precedence step 3 unused

`MembershipSnapshotResolver` accepts `collect_time_promoted_nm_ids` but never uses it (`resolver.py`); spec lists collect-time WB `nm_settings` as third precedence — deferred, not Slice B blocker if out of scope.

## Evidence anchors

- Seam order: `app/core/mp/wb/api/adapter/promotion_client/fullstats/adapter.py` L104–112
- Wiring: `tick_wiring.py` L133–147 → `unmanaged_orchestrator.py` L269–293
- Resolver precedence: `membership/resolver.py` L67–123

Tests not executed in review VM (`poetry` unavailable).
