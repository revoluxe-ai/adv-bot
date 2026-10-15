---
cursor:
  subagentId: "bc-32bdaafb-bc6f-532c-901a-2eb4845c2b03"
---

# Leg-CPO CH seam fix (separate-auto-search-cpo)

## Summary

- **Seed:** `distribute_orders_across_window_days` ensures auto/search order sums are 2/3 on the 2-day window (search 2+1 on earliest days); spend totals unchanged (600/300).
- **Integration:** `WBShopDataManager` test passes `plan_fact_reader=MagicMock()`; `AdvSettingMenu` test patches `sm` to reuse `async_session` (fixes asyncpg loop mismatch); auto-shelf view expects `OptimizationMetric.CPC` when live fact CPO ≥ resolve target; snapshot `end_date` compared by calendar day.
- **Stage:** Merged `origin/stage` (`1443649281543bc00411d9940a047037ed6d3ffd`) into `separate-auto-search-cpo` (merge commit, no pyrightconfig conflict).

## Verification

```text
ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1 ALLOW_DESTRUCTIVE_TEST_DB=1 TEST_INFRA_REUSE=1 \
CLICKHOUSE_PORT=8124 CLICK_HOUSE_HOST=127.0.0.1 CLICK_HOUSE_USER=CLICK_HOUSE_USER \
CLICK_HOUSE_PASSWORD=password poetry run pytest -m destructive_local \
tests/integration/test_leg_cpo_ch_external_gap_seams.py -q --tb=short
→ 10 passed

poetry run pytest -m unit tests/unit/support/test_leg_cpo_ch_seed.py \
tests/unit/test_leg_cpo_economics.py -q → 10 passed
```

Containers: `leg-cpo-ch-proof-rerun`, `leg-cpo-pg-proof-rerun` (removed after run).

## Commit

`9b97462b1` — `fix(tests): leg-CPO CH seed order totals and integration seams`
