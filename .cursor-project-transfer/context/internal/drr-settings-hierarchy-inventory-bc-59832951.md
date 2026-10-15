---
cursor:
  subagentId: "bc-59832951-0e2a-5881-a763-183e0795e37b"
---

# drr-settings-hierarchy — repository inventory (2026-10-07)

## Coordinator decision (2026-10-07)

**FINAL_STATUS:** `BLOCKED_BY_PRODUCT_CONTROL_CONTEXT`

Do **not** implement on the current campaign-oriented model. `PLANNING_REQUIRED` inventory accepted.

### Dependency

```text
drr-settings-hierarchy
  depends_on
product-control-context
```

### Block reasons

- Configured DRR-percent authority does not exist.
- DRR→CPO owner does not exist.
- SKU control must not attach to campaign-oriented `AdvSetting`.
- `WBCard` / nmID must become the canonical product anchor for the new control-plane layer first.

### Explicit prohibitions (this change)

- No missing calculator inside `drr-settings-hierarchy`.
- No DRR columns on `AdvSetting`.
- No migrations or UI for this feature.
- No env bootstrap for this blocked change.

### Target architecture (future, not to implement here)

**Precedence:** SKU → CATEGORY → SHOP → LEGACY

**Configured profile (conceptual):** `target_drr_percent`, `max_drr_percent`

**Legacy/runtime compatibility (unchanged until product-control chooses migration seam):**

- `target_price_for_order`
- `max_price_for_order`

---

## Authority

- **AUTHORITY_LOCATION:** `REMOTE_COMMITTED` (`stage` @ `c956e1673`, matches `origin/stage`)
- **OpenSpec change `drr-settings-hierarchy`:** not present under `openspec/changes/` (no branch on remote)

## CURRENT_SKU_DRR_SOURCE

**Absent on stage.** `AdvSetting` has sales-plan CPO fields only:

- `plan_for_sales_for_day`
- `target_price_for_order` (float, nullable)
- `max_price_for_order` (int, nullable)

No `drr`, `*_drr_percent`, or similar columns in `app/modules/common_slaves/wildberries/models/models.py` or Alembic history (`git log --all -S'target_drr_percent'` → no app commits).

## CURRENT_DRR_CALCULATION_OWNER

**No configured-DRR → target/max CPO path in `app/`.**

Runtime plan/CPO today:

1. `PlanFactProvider.get_plan_data(adv)` builds `PlanData` from the three AdvSetting fields above (`app/modules/plan_fact/provider.py`).
2. `resolve_target_cost*` in `app/shared/domains/wb/utils/cost_resolver.py` chooses target vs max CPO from plan + `fact_predict_orders` (plan-fact threshold), not from DRR %.

OpenSpec contract only (not implemented in bidder domain):

- `openspec/specs/ai-package-multi-window-analysis/spec.md` — target CPO = revenue per order × target DRR (dynamic bidder explicitly out of scope in archived design).

Scripts/analytics DRR (spend/GMV) are unrelated to configured shop/SKU DRR %.

## DRR readers / writers (app)

| Area | DRR role |
|------|----------|
| `app/modules/ai_package_v1/**` | Analytic metric IDs / blockers (`SHOP_DRR`, `SKU_DRR`), not configuration |
| `app/modules/shop_runner/.../coverage_evidence.py` | `STORE_DRR_NUMERATOR_STATUS` blocker constant |
| Sales plan Telegram UI | No DRR fields |
| Shop runner / V3 | Uses `target_price_for_order` / `max_price_for_order` via plan_fact |

## CURRENT_SHOP_SETTINGS_AUTHORITY

- **Model:** `WBCabinet` (`app/modules/common_slaves/wildberries/models/wb_cabinet.py`) — shop-level `default_max_cpm`, balance, `active`, etc. No DRR column.
- **UI pattern:** `app/client_bot/user_interface/handlers/shop_settings.py` — FSM + callback for `ChangeShopDefaultMaxCPM` (analog for shop DRR UI).
- **Shop menu:** `app/modules/shop_menu/message.py` — main shop keyboard; no «Настройки магазина» / DRR entry today.

## CATEGORY_IDENTITY

- `WBCategory` (`wb_category_name`, cabinet-scoped list on `WBCabinet.wb_categories`).
- `WBCard.wb_category_id` → category for a card/SKU.
- **Not trivial for AdvSetting:** campaigns use `nmids[]`; mapping SKU→category requires card graph, no existing category-level settings store or DRR column.

**CATEGORY_IMPLEMENTED:** NO  
**CATEGORY_DEFERRED_REASON:** No authoritative per-campaign category settings entity; only card→category linkage. Adding category DRR would need new storage + resolver inputs beyond V1 shop scope.

## Related migrations

None for configured DRR % on PG models.

## Complexity assessment

**COMPLEXITY:** HIGH (prerequisite gap)

V1 shop DRR is mechanically moderate (column + resolver + UI), but spec requires feeding resolved DRR into an **existing** DRR→CPO calculator that is **not present** on `origin/stage`. Implementing calculator here risks duplicate logic vs future domain module.

## Recommended next step

**Blocked.** Unblock via `product-control-context` (WBCard/nmID product anchor + control-plane), then revisit `drr-settings-hierarchy` with SKU → CATEGORY → SHOP → LEGACY precedence.

## Environment note

Cloud VM: `poetry` not on PATH, no `.venv`; pytest/pyright/openspec gates not runnable without env setup.
