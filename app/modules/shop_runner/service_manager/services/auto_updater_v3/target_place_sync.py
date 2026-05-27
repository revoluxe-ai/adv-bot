"""Синхронизация ``KeywordSetting.target_place`` для V3 по профилю ставок CH.

Вызывается из ``process_adv_v3`` на каждом тике (``finally``), если включён individual mode.
Корутина ``update_individual_keyword_target_places`` для V3 не используется (только V2).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.engine import Result

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.debug_trace import (
    v3_debug,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    resolve_keyword_bid_profile,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


def _mode_for_target_place(strategy_mode: KeywordStrategyMode) -> KeywordStrategyMode:
    """Режим для расчёта позиции: OFF → MIN_CPA (предиктор не знает OFF)."""
    if strategy_mode == KeywordStrategyMode.OFF:
        return KeywordStrategyMode.MIN_CPA
    return strategy_mode


async def sync_keyword_target_places_v3(
    adv: WBAdvDTO,
    bid_profiles: dict[str, list[BidPosition]],
) -> None:
    """Пересчёт ``target_place`` для всех ключей РК по профилю и ``strategy_mode``.

    Обновляются все ключи, включая OFF (для OFF позиция из профиля как для MIN_CPA).
    Нет профиля в CH — ``target_place`` сбрасывается в None.
    """
    predictor = build_predict_keywords_target_place()
    stmt = select(KeywordSetting).where(
        KeywordSetting.adv_setting_id == adv.adv_setting_original_id
    )
    stats = {"updated": 0, "cleared": 0, "off": 0, "total": 0}
    async with sm(read_only=False) as session:
        result: Result[tuple[KeywordSetting]] = await session.execute(stmt)
        keywords = result.scalars().all()
        stats["total"] = len(keywords)
        for keyword in keywords:
            was_off = keyword.strategy_mode == KeywordStrategyMode.OFF
            if was_off:
                stats["off"] += 1
            profile = resolve_keyword_bid_profile(bid_profiles, keyword.text)
            if not profile:
                logger.error(
                    "No bid profile for keyword %s, adv_id=%s; clearing target_place",
                    keyword.text,
                    adv.adv_id,
                )
                keyword.target_place = None
                stats["cleared"] += 1
                continue
            calc_mode = _mode_for_target_place(keyword.strategy_mode)
            new_place = predictor.get_target_position_for_strategy_mode(
                profile,
                calc_mode,
            )
            keyword.target_place = new_place
            if new_place is None:
                stats["cleared"] += 1
            else:
                stats["updated"] += 1
        await session.commit()

    # region agent log
    v3_debug(
        hypothesis_id="TP-SYNC",
        location="target_place_sync.py:sync_keyword_target_places_v3",
        message="target_place sync committed",
        data={
            "adv_id": adv.adv_id,
            "profile_keys": len(bid_profiles),
            **stats,
        },
    )
    # endregion
