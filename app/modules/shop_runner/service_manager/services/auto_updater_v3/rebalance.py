"""v3 rebalance hook from ``white_list_tail_trimmer`` (replaces v2 tail trim)."""

from __future__ import annotations

import logging

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    apply_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

logger = logging.getLogger(__name__)


async def run_white_list_rebalance_v3(complex_adv: ComplexAdv) -> None:
    """Transfer one aggression level from worst active key to best OFF key by rating."""
    keywords = await complex_adv.get_keywords()
    offs = [kw for kw in keywords if kw.strategy_mode == KeywordStrategyMode.OFF]
    actives = [kw for kw in keywords if kw.strategy_mode != KeywordStrategyMode.OFF]
    if not offs or not actives:
        logger.debug("[adv_id=%s] v3 rebalance: no pair", complex_adv.adv_id)
        return
    offs.sort(key=lambda k: k.rating or 0.0, reverse=True)
    actives.sort(key=lambda k: k.rating or 0.0)
    best_off = offs[0]
    worst_active = actives[0]
    if (best_off.rating or 0.0) <= (worst_active.rating or 0.0):
        logger.debug(
            "[adv_id=%s] v3 rebalance: OFF not better than worst active",
            complex_adv.adv_id,
        )
        return
    action = V3Action(
        action=V3ActionType.REBALANCE_TRANSFER,
        from_keyword_setting_id=worst_active.keyword_setting_original_id,
        to_keyword_setting_id=best_off.keyword_setting_original_id,
        reason="tail_trimmer_rebalance",
    )
    await apply_v3_actions([action])
