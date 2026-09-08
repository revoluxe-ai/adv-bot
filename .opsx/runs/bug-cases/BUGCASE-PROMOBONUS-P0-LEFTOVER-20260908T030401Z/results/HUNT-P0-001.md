# HUNT P0-001

```text
HUNT_RESULT: CLEAR
HUNT_PASSES_EXECUTED: 1
WORKER_ID: BOUNDED_HUNTER
WORKER_EXECUTION_ID: WEX_BOUNDED_HUNTER_P0_FANOUT
CASE_ID: BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z
FINDING_ID: P0-001
EXECUTED_AT: 2026-09-08T03:25:44Z
```

Scoped search for same-invariant violations: leftover/last_tranche fraction derivation
outside package-percent path. `promo_accounting.py` fixed in root. `pool_usable_from_pick`
already uses `promo_fraction_from_amounts`. `promo_overlay.py` / PlanFactProvider /
shop_runner consume cached fraction — no recompute of leftover/last_tranche. No HC-*.
