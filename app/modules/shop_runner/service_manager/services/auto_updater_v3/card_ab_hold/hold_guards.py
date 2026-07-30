"""HOLD overspend/PFO guards без ordinary NORMAL preamble.

Spec ``card-ab-hold-mode``: при ACTIVE только guard перерасхода vs max CPO;
без TP update / WL / enable / calibration UP.

Owner A_PRIME / PBH-002: symmetric ``pfo_recovery`` / ``return_on`` /
``restore_on`` when a confirmed-set keyword recovers (PASS) after safety OFF.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AbHoldSetupAction,
    classify_ab_hold_setup_keyword,
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

# auto_on floor after pfo_recovery (same as setup return_on).
_AB_HOLD_RECOVERY_ON_MODE = KeywordStrategyMode.MIN_CPA


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


def select_ab_hold_pfo_recovery_on_keyword_ids(
    keywords: list[CalculatedKeyword],
    *,
    max_pay_for_order: float,
    allowed_phrases: Iterable[str] | None = None,
) -> list[int]:
    """Ids for return_on / restore_on after PFO recovers within confirmed set.

    Owner A_PRIME: SAFETY_OFF when PFO>max Allowed; AUTO_ON when PFO recovers
    within frozen confirmed set. Does not change membership.

    Args:
        keywords: calculated keywords for the campaign.
        max_pay_for_order: plan max CPO ceiling.
        allowed_phrases: confirmed-set texts; ``None`` = no membership filter.

    Returns:
        keyword_setting ids currently OFF that classify PASS (pfo_recovery).
    """
    ceiling = float(max_pay_for_order)
    allowed: set[str] | None = (
        {str(t) for t in allowed_phrases} if allowed_phrases is not None else None
    )
    on_ids: list[int] = []
    for kw in keywords:
        if not is_v3_operable_hard_status(kw.hard_status):
            continue
        try:
            if int(kw.strategy_mode) != int(KeywordStrategyMode.OFF):
                continue
        except (TypeError, ValueError):
            if kw.strategy_mode is not KeywordStrategyMode.OFF:
                continue
        text = str(getattr(kw, "text", None) or "")
        if allowed is not None and text not in allowed:
            continue
        action = classify_ab_hold_setup_keyword(
            pay_for_order=kw.pay_for_order,
            views=int(kw.views),
            max_pay_for_order=ceiling,
        )
        if action != AbHoldSetupAction.PASS_FIX_TARGET:
            continue
        on_ids.append(int(kw.keyword_setting_original_id))
    return on_ids


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


async def apply_ab_hold_pfo_recovery_ons(
    *,
    adv_id: int,
    keyword_ids: list[int],
) -> int:
    """Persist return_on / recovery_on after PFO recovers (A_PRIME auto_on).

    Args:
        adv_id: campaign id (logging).
        keyword_ids: keyword_setting ids to restore_on (MIN_CPA).

    Returns:
        Число обновлённых id.
    """
    if not keyword_ids:
        return 0
    on_hs = hard_status_for_strategy_mode(_AB_HOLD_RECOVERY_ON_MODE)
    async with sm(read_only=False) as session:
        stmt_return_on = (
            update(KeywordSetting)
            .where(KeywordSetting.id.in_(keyword_ids))
            .values(
                hard_status=on_hs,
                strategy_mode=_AB_HOLD_RECOVERY_ON_MODE,
            )
        )
        _ = await session.execute(stmt_return_on)
        await session.commit()
    logger.info(
        "[adv_id=%s] ab_hold pfo_recovery return_on count=%s",
        adv_id,
        len(keyword_ids),
    )
    return len(keyword_ids)
