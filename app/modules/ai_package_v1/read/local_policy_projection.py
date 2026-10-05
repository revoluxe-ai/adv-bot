"""Projection локальной политики AdvSetting без импорта control-plane.

Дублирует bounded subset из `project_local_policy_from_adv_setting` для
export-owned контракта; не зависит от wb_sky_control_plane.
"""

from __future__ import annotations

from typing import Any

from app.modules.common_slaves.wildberries.models.models import AdvSetting


def project_local_policy_fields(row: AdvSetting) -> dict[str, Any]:
    """Извлекает LOCAL_POLICY поля из AdvSetting без side effects.

    Args:
        row: ORM строка AdvSetting из read-only SELECT.

    Returns:
        Словарь с ключами bot_active, bidder_active, parsing_active, budget,
        sales, bid_control, keyword_policy — значения как в PG (None сохраняется).
    """
    budget = {
        "auto_budget_watchdog_enabled": row.auto_budget_watchdog_enabled,
        "auto_budget_daily_limit": row.auto_budget_daily_limit,
        "search_auto_budget_daily_limit": row.search_auto_budget_daily_limit,
        "use_common_budget": row.use_common_budget,
        "common_budget_daily_limit": row.common_budget_daily_limit,
        "auto_budget_total_limit": row.auto_budget_total_limit,
        "search_auto_budget_total_limit": row.search_auto_budget_total_limit,
        "common_budget_total_limit": row.common_budget_total_limit,
    }
    sales: dict[str, object] = {
        "orders_source_for_auto_mode": row.orders_source_for_auto_mode.value,
        "plan_for_sales_for_day": row.plan_for_sales_for_day,
        "target_price_for_order": row.target_price_for_order,
        "max_price_for_order": row.max_price_for_order,
        "sales_predict_method": row.sales_predict_method.value,
        "strategy": row.strategy.value if row.strategy is not None else None,
        "auto_update_strategy": row.auto_update_strategy,
    }
    bid_control: dict[str, object] = {
        "auto_shelf_bid_control_enabled": row.auto_shelf_bid_control_enabled,
        "auto_shelf_bid_control_strategy": (
            row.auto_shelf_bid_control_strategy.value
            if row.auto_shelf_bid_control_strategy is not None
            else None
        ),
        "bidder_for_auto": row.bidder_for_auto,
        "max_cpm": row.max_cpm,
        "bidder_step": row.bidder_step,
    }
    keyword_policy: dict[str, object] = {
        "black_phrases": list(row.black_phrases or []),
        "relevant_phrases": list(row.relevant_phrases or []),
        "auto_update_minus_phrases": row.auto_update_minus_phrases,
        "auto_update_white_list": row.auto_update_white_list,
    }
    return {
        "bot_active": row.bot_active,
        "bidder_active": row.bidder_active,
        "parsing_active": row.parsing_active,
        "budget": budget,
        "sales": sales,
        "bid_control": bid_control,
        "keyword_policy": keyword_policy,
    }
