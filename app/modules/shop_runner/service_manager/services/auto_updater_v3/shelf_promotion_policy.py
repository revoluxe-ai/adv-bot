"""Полочная фаза V3: ``rec_system_mode`` + авто ``started`` — UP/DOWN без 1–2–3 rollout.

Отдельно от ``AdvStrategySelector`` (поле ``strategy`` MIN_CPO/MAX_CONV по орг/пол и pending shelf).
Здесь — лестница ``strategy_mode`` / ``hard_status`` на ключах. Критерий «полочного pending»
совпадает с ``AdvStrategySelector._all_shelf_keywords_activated`` (см. ``_is_shelf_pending_keyword``).
Сравнение ``organic_clicks`` vs ``shelf_clicks`` в этот модуль **не входит** (только в селекторе стратегии).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_rollout_down_one,
    plan_rollout_underperform_one,
    try_valid_rollout_up,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

_HARD_STATUS_AUTO_MODE = 1


def _is_shelf_pending_keyword(ctx: KeywordV3Context) -> bool:
    kw = ctx.keyword
    return (
        kw.above_rec_conversion is True
        and kw.hard_status == _HARD_STATUS_AUTO_MODE
        and kw.status == KeywordStatus.BAD
        and kw.reason != KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
    )


def plan_shelf_promotion_actions(
    prepared: list[tuple[KeywordV3Context, KeywordStrategyMode, bool]],
    *,
    state: SalesStates,
) -> list[V3Action]:
    """Mirror v2 shelf focus: pending shelf keywords first on UP; DOWN same as global."""
    if state == SalesStates.OPTIMAL:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="optimal")]

    if state == SalesStates.OVERSPEND:
        return plan_rollout_down_one(prepared, reason="overspend")

    if state == SalesStates.STABLE:
        return plan_rollout_down_one(prepared, reason="stable")

    if state == SalesStates.UNDERPERFORM:
        shelf_pool: list[tuple[KeywordV3Context, KeywordStrategyMode, bool, V3Action]] = []
        for ctx, mode, proven in prepared:
            if not _is_shelf_pending_keyword(ctx):
                continue
            act = try_valid_rollout_up(ctx, mode, proven)
            if act is not None:
                shelf_pool.append((ctx, mode, proven, act))
        if shelf_pool:
            shelf_pool.sort(
                key=lambda t: float(t[0].keyword.conv_views_to_orders),
                reverse=True,
            )
            return [shelf_pool[0][3]]
        return plan_rollout_underperform_one(prepared, V3RolloutAggressiveness.MAX)

    return [V3Action(action=V3ActionType.DO_NOTHING, reason="unknown_state")]
