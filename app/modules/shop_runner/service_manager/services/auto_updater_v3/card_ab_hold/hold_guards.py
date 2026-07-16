"""HOLD overspend/PFO guards без ordinary NORMAL preamble.

Spec ``card-ab-hold-mode``: при ACTIVE только guard перерасхода vs max CPO;
без TP update / WL / enable / calibration UP.
"""

from __future__ import annotations

import logging

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    hard_status_for_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    cmp_over_threshold,
    pfo_off_plan_headroom_floor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    keyword_pfo_over_max,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    is_v3_operable_hard_status,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


def is_ab_hold_campaign_deep_overspend(
    *,
    fact_pay_for_order: float | None,
    max_pay_for_order: float,
) -> bool:
    """True, если fact в зоне pfo_off (как ``is_deep_overspend`` без AdvState)."""
    if fact_pay_for_order is None:
        return False
    max_pay = float(max_pay_for_order)
    if max_pay <= 0:
        return False
    return cmp_over_threshold(
        float(fact_pay_for_order),
        pfo_off_plan_headroom_floor(max_pay),
    )


def select_ab_hold_overspend_off_keyword_ids(
    keywords: list[CalculatedKeyword],
    *,
    max_pay_for_order: float,
) -> list[int]:
    """Operable active ключи с pay_for_order > max (HOLD PFO-off guard)."""
    ceiling = float(max_pay_for_order)
    out: list[int] = []
    for kw in keywords:
        if not is_v3_operable_hard_status(kw.hard_status):
            continue
        if kw.strategy_mode == KeywordStrategyMode.OFF:
            continue
        if not keyword_pfo_over_max(kw.pay_for_order, ceiling):
            continue
        out.append(int(kw.keyword_setting_original_id))
    return out


async def apply_ab_hold_overspend_offs(
    *,
    adv_id: int,
    keyword_ids: list[int],
) -> int:
    """Persist FORCE_OFF для hold-guard (strategy_mode OFF + hard_status).

    Returns:
        Число обновлённых id.
    """
    if not keyword_ids:
        return 0
    off_hs = hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
    async with sm(read_only=False) as session:
        stmt = (
            update(KeywordSetting)
            .where(KeywordSetting.id.in_(keyword_ids))
            .values(
                hard_status=off_hs,
                strategy_mode=KeywordStrategyMode.OFF,
                target_place=None,
            )
        )
        _ = await session.execute(stmt)
        await session.commit()
    logger.info(
        "[adv_id=%s] ab_hold overspend OFF count=%s",
        adv_id,
        len(keyword_ids),
    )
    return len(keyword_ids)
