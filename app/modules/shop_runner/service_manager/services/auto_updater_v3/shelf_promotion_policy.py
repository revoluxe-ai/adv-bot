"""Полочная фаза V3: ``rec_system_mode`` + авто ``started``.

Почему стратегии отличаются: ``auto_updater_traffic_policy``.

Decision matrix (UNDERPERFORM), механика выбора:
- ``organic > shelf`` → **послойная** + aggr=MIN, общий пул (без shelf-only).
- ``shelf >= organic`` или DTO нет → **поштучная**: shelf pending, затем non-shelf;
  ``aggressiveness`` (1/2/3) в этой ветке **не используется**.

Отдельно от ``AdvSetting.strategy`` (MIN_CPO/MAX_CONV).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ActivationStrategy,
    ShelfClickMode,
    activation_strategy_for_shelf_underperform,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_overspend_actions,
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

_PreparedEntry = tuple["KeywordV3Context", KeywordStrategyMode, bool]
_PreparedList = list[_PreparedEntry]
_PoolEntry = tuple["KeywordV3Context", KeywordStrategyMode, bool, V3Action]


def _is_shelf_pending_keyword(ctx: KeywordV3Context) -> bool:
    kw = ctx.keyword
    return (
        kw.above_rec_conversion is True
        and kw.hard_status == _HARD_STATUS_AUTO_MODE
        and kw.status == KeywordStatus.BAD
        and kw.reason != KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
    )


def _piecewise_sort_key(
    entry: _PoolEntry,
) -> tuple[float, int, str]:
    ctx = entry[0]
    conv = float(ctx.keyword.conv_views_to_orders)
    ks_id = int(ctx.keyword.keyword_setting_original_id)
    return (-conv, ks_id, ctx.keyword.text)


def _collect_up_pool(
    prepared: _PreparedList,
    *,
    include: bool,
) -> list[_PoolEntry]:
    pool: list[_PoolEntry] = []
    for ctx, mode, proven in prepared:
        if include != _is_shelf_pending_keyword(ctx):
            continue
        act = try_valid_rollout_up(ctx, mode, proven)
        if act is not None:
            pool.append((ctx, mode, proven, act))
    return pool


def _pick_one_piecewise_up(
    pool: list[_PoolEntry],
    *,
    reason_prefix: str,
) -> list[V3Action]:
    if not pool:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason=f"{reason_prefix}_no_up")]
    pool.sort(key=_piecewise_sort_key)
    action = pool[0][3]
    return [
        V3Action(
            action=action.action,
            keyword_setting_id=action.keyword_setting_id,
            reason=reason_prefix,
        )
    ]


def _plan_piecewise_shelf_then_non_shelf(prepared: _PreparedList) -> list[V3Action]:
    shelf_pool = _collect_up_pool(prepared, include=True)
    if shelf_pool:
        return _pick_one_piecewise_up(shelf_pool, reason_prefix="piecewise_shelf")
    non_shelf_pool = _collect_up_pool(prepared, include=False)
    return _pick_one_piecewise_up(non_shelf_pool, reason_prefix="piecewise_non_shelf")


def _plan_underperform_shelf(
    prepared: _PreparedList,
    *,
    click_mode: ShelfClickMode,
) -> list[V3Action]:
    strategy = activation_strategy_for_shelf_underperform(click_mode)
    if strategy == ActivationStrategy.LAYERED:
        return plan_rollout_underperform_one(prepared, V3RolloutAggressiveness.MIN)
    return _plan_piecewise_shelf_then_non_shelf(prepared)


def plan_shelf_promotion_actions(
    prepared: _PreparedList,
    *,
    state: SalesStates,
    click_mode: ShelfClickMode,
    plan_max_pay_for_order: float | None = None,
) -> list[V3Action]:
    """Полочная фаза: UP/DOWN без 1–2–3 rollout; underperform по click_mode."""
    if state == SalesStates.OPTIMAL:
        return [V3Action(action=V3ActionType.DO_NOTHING, reason="optimal")]

    if state == SalesStates.OVERSPEND:
        if plan_max_pay_for_order is not None:
            return plan_overspend_actions(
                prepared, max_pay_for_order=float(plan_max_pay_for_order)
            )
        return plan_rollout_down_one(prepared, reason="overspend")

    if state == SalesStates.STABLE:
        return plan_rollout_down_one(prepared, reason="stable")

    if state == SalesStates.UNDERPERFORM:
        return _plan_underperform_shelf(prepared, click_mode=click_mode)

    return [V3Action(action=V3ActionType.DO_NOTHING, reason="unknown_state")]
