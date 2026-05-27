"""Синхронизация ``KeywordSetting.target_place`` для V3 по профилю ставок CH.

Вызывается из ``process_adv_v3`` после apply (и при раннем выходе plan/fact, если
сработал gap-rebalance). Корутина ``update_individual_keyword_target_places`` для V3
не использует этот модуль (только V2).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.engine import Result

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    resolve_keyword_bid_profile,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


async def sync_keyword_target_places_v3(
    adv: WBAdvDTO,
    bid_profiles: dict[str, list[BidPosition]],
) -> None:
    """Пересчёт ``target_place`` по профилю и текущему ``strategy_mode`` в БД.

    Для OFF сохранённый ``target_place`` не меняем: торги OFF отрезаются в
    ``UpdateClusterBidsManager``. Нет профиля в CH — ``target_place`` сбрасывается в None.
    """
    predictor = build_predict_keywords_target_place()
    stmt = select(KeywordSetting).where(
        KeywordSetting.adv_setting_id == adv.adv_setting_original_id
    )
    async with sm(read_only=False) as session:
        result: Result[tuple[KeywordSetting]] = await session.execute(stmt)
        keywords = result.scalars().all()
        for keyword in keywords:
            if keyword.strategy_mode == KeywordStrategyMode.OFF:
                logger.debug(
                    "Skip target_place update for OFF keyword=%s adv_id=%s",
                    keyword.text,
                    adv.adv_id,
                )
                continue
            profile = resolve_keyword_bid_profile(bid_profiles, keyword.text)
            if not profile:
                logger.error(
                    "No bid profile for keyword %s, adv_id=%s; clearing target_place",
                    keyword.text,
                    adv.adv_id,
                )
                keyword.target_place = None
                continue
            keyword.target_place = predictor.get_target_position_for_strategy_mode(
                profile,
                keyword.strategy_mode,
            )
        await session.commit()
