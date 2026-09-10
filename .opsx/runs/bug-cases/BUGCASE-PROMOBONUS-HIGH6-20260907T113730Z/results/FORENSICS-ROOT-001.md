# FORENSICS ROOT-001

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
INTAKE_ID: INTAKE-001
FINDING_ID: ROOT-001
COMMAND: /opsx-fix-bug
GO: no
CREATED_AT: 2026-09-07T12:12:00Z
PERSISTENCE_DECISION: new_finding
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z/ROOT-001/2026-09-07T11:54:28Z
ROUTE_RECONCILIATION: MATCH
CURRENT_CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A

## Verdict

VERDICT: fix_now
RUNTIME_REACHABLE: yes
WRITE_BOUNDARY_REACHABLE: yes
DEAD_OR_LEGACY: no
FOLLOW_UP_SCOPE: none
AUTO_MATERIALIZE: false

## Invariant

Overlay не должен AND-stop (`usable=false` / `M=1`), пока на кампании есть non-expired leftover (`remaining>0`), даже при `pool=0`. Окно `PROMO_LOOKBACK_DAYS=90` не имеет права исключить живой leftover из `load_campaign_ledgers`.

## Evidence chain

1. Runtime entrypoint: `app/modules/shop_runner/wb_shop.py` создаёт `coroutines_manager.auto_budget_watchdog(only_bot_active=False)`.
2. Manager: `CoroutinesManager.auto_budget_watchdog` → `AutoBudgetService.refresh_promo_state`.
3. Direct call: `PromoStateService.refresh` → `load_campaign_ledgers(session, advert_ids, now=now, ...)`.
4. Causal defect: `load_campaign_ledgers` всегда ставит `cutoff = now - PROMO_LOOKBACK_DAYS` и передаёт его в `load_success_tranches` (`created_at >= cutoff`) и `load_spend_rows` (`upd_time >= cutoff`).
5. Accounting: `campaign_ledger_from_rows` → `usable = remaining > 0`. Если success-tranche старше 90d выпала, `remaining=0` → `campaign_usable=false`.
6. Availability: `resolve_promo_availability` делает `usable = pool_usable or campaign_usable`. При `pool=0` и ложном `campaign_usable=false` → `usable=false`, `stop_on_exhaustion=true`.
7. Write boundary: `RedisPromoStateManager.set` пишет `campaigns[].usable` / `campaign_usable`.
8. Downstream: `WBShopDataManager._load_cached_promo_state` → `fraction_from_cached_state` пропускает `not campaign.usable` → `f=0` / conservative `M=1` (AND-stop overlay OFF).

## Callers

- runtime_entrypoints: `wb_shop.py` shop-runner TaskGroup; `CoroutinesManager.auto_budget_watchdog`
- direct_callers: `PromoStateService.refresh`
- indirect_callers: `AutoBudgetService.refresh_promo_state`
- test_only_callers: `tests/unit/auto_budget_manager/test_promo_ledger.py` (window alignment only; не leftover старше 90d)

## Existing tests (gap)

- `test_allocation_and_spend_windows_are_aligned` закрепляет 90d alignment, не leftover-usable.
- `test_upd_ingest_uses_recovery_window_then_daily_overlap` покрывает UPD ingest watermark, не overlay usable.
- Нет regression, который падает, когда leftover старше окна остаётся non-expired и `pool=0`.

## Minimal fix plan (not applied this hop)

- files allowed: `app/modules/auto_budget_manager/promo_ledger.py` (узко: leftover-usable не режется 90d cutoff); опционально узкий caller `PromoStateService.refresh`, если cutoff надо снять только для leftover-usable.
- files forbidden: tests (RED пишет `/opsx-test`); product за пределами ledger/refresh; alembic; enable `RaisePlanOnPromobonuses`; FINDING-H2..H6.
- exact behavior: leftover success-tranche с `remaining>0` и не expired остаётся `campaign_usable=true` вне 90d окна; spend/allocation window alignment не должен false-stop живой leftover.
- no-op: не расширять UPD ingest окно без отдельного finding.

## Stop conditions

- GO отсутствует → production/app не менять.
- RED принадлежит `/opsx-test`.
- FINDING-H2..H6 не стартовать (`MAX_ACTIVE_FINDINGS=1`, backlog).
- Не закрывать finding (`closed_fixed` запрещён из fix-bug).

## Next

/opsx-test case=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z finding=ROOT-001
