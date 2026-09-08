# HUNT evidence: ROOT-001 leftover-usable 90d AND-stop neighborhood

```text
CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: ROOT-001
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z/4ae535b7
WORKER_ID: BOUNDED_HUNTER
WORKER_EXECUTION_ID: WEX/BOUNDED_HUNTER/6b40a73f89
HUNT_RESULT: CLEAR
CANDIDATE_COUNT: 0
```

## Invariant hunted

A leftover success-tranche with `remaining>0` and not expired must keep `campaign_usable` / overlay usable even when `created_at` is older than `PROMO_LOOKBACK_DAYS` (90d) and `pool=0`. The 90d lookback cutoff must not AND-stop a living leftover. Root fix is in `promo_ledger.load_campaign_ledgers`.

## Hunt result

`HUNT_RESULT=CLEAR`. No leftover-usable 90d AND-stop clone besides already-fixed ROOT-001. `CANDIDATES=[]`.

FINDING-H2..H6 already exist on this case as `different_invariant` backlog. They are not leftover-90d clones and were not promoted to hunt candidates. No second case invented.

## Neighborhood searched

| Surface | Role | 90d leftover-usable AND-stop? |
|---|---|---|
| `app/modules/auto_budget_manager/promo_ledger.py` `load_campaign_ledgers` | ROOT-001 writer | No. Post-fix loads allocation and spend **without** cutoff. |
| `load_success_tranches` / `load_spend_rows` | Optional `cutoff=` helper | Only leftover-usable caller is `load_campaign_ledgers`, which does **not** pass cutoff. No other production caller. |
| `PromoStateService.refresh` | Known writer | Calls `load_campaign_ledgers` without cutoff. `_UPD_LOOKBACK_DAYS` bounds WB `get_costs_history` ingest only. |
| `resolve_promo_availability` / `campaign_ledger_from_rows` / `apply_spend_fefo` | Accounting | Drops leftover only via `is_expired(expires_at)`, not `created_at` lookback. |
| `RedisPromoStateManager.set` | Known writer | Persists `campaigns[].usable` as given. Redis TTL 48h / stale 15m are snapshot freshness, not leftover `created_at`. |
| `fraction_from_cached_state` | Known reader | Skips `not campaign.usable`. No 90d age filter. |
| `WBShopDataManager._build_pre_complex_adv` | Known reader | Uses `fraction_from_cached_state`. No leftover lookback. |
| `auto_shelf_bid_control_view_provider` overlay helper | Reader | Same `fraction_from_cached_state`. No leftover lookback. |
| `WBAutoBudgetTopUp` queries in `AutoBudgetService` | Daily top-up sums | Filter by `date_msk` / setting, not leftover-usable overlay cutoff. |
| `PROMO_LOOKBACK_DAYS` usages | Constant | Only `promo_ledger.py` (constant + leftover-usable no-cutoff comments) and `promo_state_service.py` (UPD ingest recovery). |

Repo-wide `PROMO_LOOKBACK_DAYS` / `timedelta(days=90)` leftover overlay writers/readers: none besides the ROOT-001 path (fixed) and UPD ingest recovery (not leftover-usable overlay AND-stop).

## Inspected, not a clone

`PromoStateService._UPD_LOOKBACK_DAYS` still equals 90. ROOT-001 / FIX-ROOT-001 / MINIMAL_FIX_PLAN explicitly left UPD ingest lookback unchanged. That window fetches WB costs history; it does not drop a living leftover success-tranche from the campaign ledger. Missing old spend would overstate remaining (keep usable), not AND-stop overlay when leftover remains. Not SAME_INVARIANT leftover-cutoff.

Optional `cutoff` on `load_success_tranches` / `load_spend_rows` remains for window-aligned callers. Leftover-usable path does not use it. No second production writer applies `created_at>=now-90d` to leftover overlay.

## Existing backlog observed (not candidates)

Already materialized on this case with `RELATION_TO_ROOT=different_invariant`, `STATUS=backlog`. Not leftover-90d AND-stop clones:

- FINDING-H2 — campaign `f` denominator uses `budget_after`/wallet instead of top-up unit (`promo_accounting.py`).
- FINDING-H3 — one-tick overlay lag after pool and leftover exhausted (`manager.py`).
- FINDING-H4 — `plan_fact_stats` persists overlay.plan instead of raw `get_plan_data`.
- FINDING-H5 — keyword GOOD/BAD resolve wipes overlay CPO via AdvSetting/CH.
- FINDING-H6 — `pick_cashback_for_topup` prefers expired package over live FEFO.

## Forbidden actions not taken

No production edits, tests edits, git commit, alembic, RaisePlanOnPromobonuses enable, second case, relation classification, FINDING-H2..H6 claim/mutation, ROOT-001 mutation, family/ writes, CHECKPOINT/LEDGER/CASE/ROUTE-TRACE writes, HUNTER_IMPLEMENTED_FIX / HUNTER_WROTE_RED / HUNTER_CHOSE_ROUTE / HUNTER_CLOSED_CANDIDATE.

## Artifacts

- `results/HUNT-ROOT-001.md`
- `results/HUNT-CANDIDATES.json`
