"""Активация ключей без данных V3: OFF → MIN_CPA, ``target_place=0`` (мин. ставка WB).

«Нет данных» на уровне **ключа** — как в V2: нельзя посчитать себестоимость заказа
(``orders_per_1000_rub`` / ``pay_for_order`` из ``conv_views_to_orders`` и CPM каскада).

На уровне **кампании** — ``SalesStates.NO_DATA`` (``detect_campaign_state``).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    apply_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

logger = logging.getLogger(__name__)

# 0 = «нет целевой позиции из CH, торговать на min bid» (см. UpdateClusterBidsManager).
NO_DATA_TARGET_PLACE_FALLBACK: int = 0

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2


def _hard_status_allows_up(hard_status: int) -> bool:
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def keyword_v2_pay_for_order_unavailable(keyword: CalculatedKeyword) -> bool:
    """Нет CPO ключа по той же цепочке, что V2 (рейтинг / ``pay_for_order``).

    ``orders_per_1000_rub = conv_views_to_orders × 1_000_000 / CPM``;
    CPO = ``1000 / orders_per_1000_rub``. Если CPM неизвестен или заказов на 1000₽ нет —
    данных для экономического решения по ключу нет.

    Args:
        keyword: Рассчитанный ключ (CPM из каскада, conv из CH).

    Returns:
        True, если ``pay_for_order`` в V2 был бы ``None``.

    Raises:
        TypeError: если передан не ``CalculatedKeyword`` (например ORM ``KeywordSetting``).
    """
    if not isinstance(keyword, CalculatedKeyword):
        raise TypeError(
            "keyword_v2_pay_for_order_unavailable expects CalculatedKeyword, "
            f"got {type(keyword).__name__}"
        )
    if keyword.pay_for_order is not None:
        return False
    orders = calc_orders_per_1000_rub(
        keyword.conv_views_to_orders,
        keyword.cpm,
    )
    if orders is None:
        return True
    return calc_pay_for_order(orders) is None


def keyword_lacks_v3_decision_data(ctx: "KeywordV3Context") -> bool:
    """Ключ без данных для V3: нет V2 CPO (не матрица CH)."""
    return keyword_v2_pay_for_order_unavailable(ctx.keyword)


def split_prepared_by_v2_cpo(
    prepared: PreparedList,
) -> tuple[PreparedList, PreparedList]:
    """Разделить prepared на ключи с V2 CPO и без (для ``SalesStates.NO_DATA``).

    Returns:
        (with_v2_cpo, without_v2_cpo) — оба списка в формате PreparedList.
    """
    with_cpo: PreparedList = []
    without_cpo: PreparedList = []
    for entry in prepared:
        ctx, _mode = entry
        if keyword_v2_pay_for_order_unavailable(ctx.keyword):
            without_cpo.append(entry)
        else:
            with_cpo.append(entry)
    return with_cpo, without_cpo


def plan_no_data_min_up_actions(prepared: PreparedList) -> list[V3Action]:
    """Включить на MIN_CPA все OFF-ключи без V2 CPO (минимальная ставка по режиму).

    Returns:
        Список UP (может быть пустым).
    """
    actions: list[V3Action] = []
    for ctx, mode in prepared:
        if mode != KeywordStrategyMode.OFF:
            continue
        if not keyword_lacks_v3_decision_data(ctx):
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        actions.append(
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=ks_id,
                target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                reason="no_data_min_bid",
            )
        )
    return actions


def _build_prepared(
    contexts: list["KeywordV3Context"],
) -> PreparedList:
    prepared: PreparedList = []
    for ctx in contexts:
        prepared.append((ctx, stored_strategy_mode(ctx.keyword)))
    return prepared


async def run_no_data_activation_v3(
    complex_adv: "ComplexAdv",
    *,
    contexts: list["KeywordV3Context"],
) -> bool:
    """Применить массовый OFF→MIN_CPA для ключей без V2 CPO (каждый тик preamble).

    Returns:
        True, если были изменения в БД.
    """
    prepared = _build_prepared(contexts)
    actions = plan_no_data_min_up_actions(prepared)
    if not actions:
        return False
    logger.info(
        "[adv_id=%s] v3 no_data activation: up=%s",
        complex_adv.adv_id,
        len(actions),
    )
    await apply_v3_actions(actions, complex_adv=complex_adv)
    return True
