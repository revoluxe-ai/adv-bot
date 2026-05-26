"""Gap-rebalance V3: срез хвоста БС ниже первой «дыры» OFF в сортировке MIN_CPO.

Вызывается в начале ``process_adv_v3`` (не из ``white_list_tail_trimmer``).
Алгоритм: первая OFF с активными ниже → хвост в OFF → N×UP (N = сумма mode_level хвоста).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ActivationStrategy,
    ShelfClickMode,
    activation_strategy_for_shelf_underperform,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    apply_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    keyword_has_proven_ad_stats,
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
    step_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.sort_utils import (
    sort_white_list_by_min_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    plan_cost_first_up_one,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

logger = logging.getLogger(__name__)

_PreparedEntry = tuple["KeywordV3Context", KeywordStrategyMode, bool]
_PreparedList = list[_PreparedEntry]


def find_first_ladder_gap_index(sorted_wl: list[CalculatedKeyword]) -> int | None:
    """Индекс первой OFF, под которой есть активные (mode_level > 0) ключи БС.

    Args:
        sorted_wl: БС, уже отсортированные по MIN_CPO (дешёвые сверху).

    Returns:
        Индекс якоря OFF или None, если дыры нет.
    """
    for i, kw in enumerate(sorted_wl):
        if stored_strategy_mode(kw) != KeywordStrategyMode.OFF:
            continue
        if any(
            mode_level(stored_strategy_mode(below)) > 0
            for below in sorted_wl[i + 1 :]
        ):
            return i
    return None


def _build_prepared(contexts: list[KeywordV3Context]) -> _PreparedList:
    prepared: _PreparedList = []
    for ctx in contexts:
        mode = stored_strategy_mode(ctx.keyword)
        proven = keyword_has_proven_ad_stats(ctx.keyword)
        prepared.append((ctx, mode, proven))
    return prepared


def _plan_rebalance_up_once(
    prepared: _PreparedList,
    *,
    shelf_promotion_active: bool,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
) -> list[V3Action]:
    """Один UP по политике текущей ветки (shelf / non-shelf), без DOWN/cleanup."""
    if shelf_promotion_active:
        strategy = activation_strategy_for_shelf_underperform(shelf_click_mode)
        if strategy == ActivationStrategy.LAYERED:
            return plan_cost_first_up_one(
                prepared,
                click_mode=shelf_click_mode,
                layered=True,
                aggressiveness=V3RolloutAggressiveness.MIN,
                piecewise_shelf=False,
            )
        return plan_cost_first_up_one(
            prepared,
            click_mode=shelf_click_mode,
            layered=False,
            aggressiveness=V3RolloutAggressiveness.MIN,
            piecewise_shelf=True,
        )
    return plan_cost_first_up_one(
        prepared,
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        layered=True,
        aggressiveness=aggressiveness,
        piecewise_shelf=False,
    )


def _mutate_prepared_after_up(prepared: _PreparedList, action: V3Action) -> None:
    """Обновить mode в prepared после запланированного UP (следующая итерация цикла)."""
    if action.keyword_setting_id is None:
        return
    for idx, (ctx, mode, proven) in enumerate(prepared):
        if ctx.keyword.keyword_setting_original_id != action.keyword_setting_id:
            continue
        if action.target_strategy_mode is not None:
            nxt = action.target_strategy_mode
        else:
            nxt = step_up(mode)
        if nxt is None:
            return
        prepared[idx] = (ctx, nxt, proven)
        return


def plan_ladder_gap_rebalance(
    prepared: _PreparedList,
    *,
    shelf_promotion_active: bool,
    shelf_click_mode: ShelfClickMode,
    rollout_aggressiveness: int | None,
) -> list[V3Action]:
    """Спланировать FORCE_OFF хвоста и N×UP (N = сумма mode_level хвоста).

    Args:
        prepared: Контексты всех ключей кампании с профилями.
        shelf_promotion_active: Полочная фаза.
        shelf_click_mode: Режим кликов shelf/organic.
        rollout_aggressiveness: 1–3 вне полки.

    Returns:
        Список действий: сначала FORCE_OFF, затем UP.
    """
    keywords = [ctx.keyword for ctx, _m, _p in prepared]
    sorted_wl = sort_white_list_by_min_cpo(keywords)
    gap_idx = find_first_ladder_gap_index(sorted_wl)
    if gap_idx is None:
        return []

    tail = sorted_wl[gap_idx + 1 :]
    if not tail:
        return []

    aggr = normalize_v3_rollout_aggressiveness(rollout_aggressiveness)
    actions: list[V3Action] = []
    budget = 0
    for kw in tail:
        budget += mode_level(stored_strategy_mode(kw))
        ks_id = kw.keyword_setting_original_id
        if ks_id is None:
            continue
        actions.append(
            V3Action(
                action=V3ActionType.FORCE_OFF,
                keyword_setting_id=ks_id,
                reason="ladder_gap_tail_off",
            )
        )

    if budget <= 0:
        return actions

    # In-memory prepared: reflect tail OFF before UP planning
    wl_off_ids = {kw.keyword_setting_original_id for kw in tail}
    working: _PreparedList = []
    for ctx, mode, proven in prepared:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id in wl_off_ids:
            working.append((ctx, KeywordStrategyMode.OFF, proven))
        else:
            working.append((ctx, mode, proven))

    applied_ups = 0
    for _ in range(budget):
        up_batch = _plan_rebalance_up_once(
            working,
            shelf_promotion_active=shelf_promotion_active,
            shelf_click_mode=shelf_click_mode,
            aggressiveness=aggr,
        )
        if not up_batch or up_batch[0].action != V3ActionType.UP:
            remaining = budget - applied_ups
            if remaining > 0:
                logger.info(
                    "v3_gap_rebalance: UP stopped early applied=%s budget=%s reason=%s",
                    applied_ups,
                    budget,
                    up_batch[0].reason if up_batch else "empty",
                )
            break
        up_action = up_batch[0]
        actions.append(
            V3Action(
                action=up_action.action,
                keyword_setting_id=up_action.keyword_setting_id,
                target_strategy_mode=up_action.target_strategy_mode,
                reason="ladder_gap_rebalance_up",
                selection_log=up_action.selection_log,
            )
        )
        _mutate_prepared_after_up(working, up_action)
        applied_ups += 1

    return actions


async def run_ladder_gap_rebalance_v3(
    complex_adv: ComplexAdv,
    *,
    contexts: list[KeywordV3Context],
    shelf_promotion_active: bool,
    shelf_click_mode: ShelfClickMode,
    rollout_aggressiveness: int | None,
) -> bool:
    """Применить gap-rebalance, если есть действия.

    Returns:
        True, если были применены изменения.
    """
    prepared = _build_prepared(contexts)
    actions = plan_ladder_gap_rebalance(
        prepared,
        shelf_promotion_active=shelf_promotion_active,
        shelf_click_mode=shelf_click_mode,
        rollout_aggressiveness=rollout_aggressiveness,
    )
    if not actions:
        logger.debug("[adv_id=%s] v3 gap rebalance: no actions", complex_adv.adv_id)
        return False

    force_count = sum(1 for a in actions if a.action == V3ActionType.FORCE_OFF)
    up_count = sum(1 for a in actions if a.action == V3ActionType.UP)
    logger.info(
        "[adv_id=%s] v3 gap rebalance: force_off=%s up=%s",
        complex_adv.adv_id,
        force_count,
        up_count,
    )
    await apply_v3_actions(actions)
    return True
