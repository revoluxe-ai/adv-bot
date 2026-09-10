# ADJUDICATION INTAKE-001

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
INTAKE_ID: INTAKE-001
COMMAND: /opsx-fix-bug
GO: no
CREATED_AT: 2026-09-07T11:50:00Z
PERSISTENCE_DECISION: new_finding
ACTIVE_FINDING_ID: ROOT-001
MAX_ACTIVE_FINDINGS: 1

## Verdict per item

| ID | Verdict | runtime_reachable | write_boundary | FINDING_ID | STATUS |
|---|---|---|---|---|---|
| H1 | fix_now | yes | Redis overlay usable | ROOT-001 | available |
| H2 | fix_now | yes | Redis overlay M | FINDING-H2 | backlog |
| H3 | fix_now | yes | WB auto-budget top-up this tick | FINDING-H3 | backlog |
| H4 | fix_now | yes | CH plan_fact_stats | FINDING-H4 | backlog |
| H5 | fix_now | yes | keyword GOOD/BAD → minus/bids | FINDING-H5 | backlog |
| H6 | fix_now | yes | WB top-up cashback | FINDING-H6 | backlog |

Не duplicate REBUILD ROOT-001 (Telegram rec-bid get_effective_promo_plan). Другой case, другой causal path.

Architecture Decision Missing для promo leftover/overlay denominator (openspec/decisions/index.md не содержит promo overlay decision). Classifier решает IMPLEMENTATION_BUG vs SPEC_BUG.

## H1 evidence chain

shop-runner `auto_budget_watchdog` → `AutoBudgetService.refresh_promo_state` → `PromoStateService.refresh` → `load_campaign_ledgers` (`cutoff=now-90d`) → `resolve_promo_availability` → `RedisPromoStateManager.set`

False AND-stop: leftover success-tranche с `created_at` старше 90d исключается, `remaining=0`, при `pool=0` `usable=false`.

## H2 evidence chain

`campaign_ledger_from_rows` denominator = `campaign_budget_total` else `budget_after`. Refresh не передаёт budgets → leftover 200 / wallet 5000 ≠ M=1.25.

## H3 evidence chain

`get_complex_advs` (stale Redis) → `refresh_promo_state` (new Redis, DTO not updated) → top-up uses stale raised limits.

## H4 evidence chain

`update_plan_fact_stats` → `get_pre_complex_advs` → `_build_pre_complex_adv` `plan_data=overlay.plan` → `process_pre_adv` → `insert_plan_fact_stats`.

## H5 evidence chain

`CalculatedKeywordsManager.__get_calculated_keywords` override `resolved_target_cost` from `AdvSetting.target/max` + CH fact → `_apply_above_target_cooldown` GOOD/BAD.

## H6 evidence chain

`pick_cashback_for_topup` no `is_expired` skip → `select_topup_balance_decision` → WB deposit.

## Follow-up

AUTO_MATERIALIZE: false
FOLLOW_UP_SCOPE: none (H2–H6 already persisted as backlog packets; not new cases)

NEXT_COMMAND:
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z chat_label="SUP-PROMOBONUS-FIX-20260907"
