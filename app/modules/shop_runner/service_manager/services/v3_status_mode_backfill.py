"""Backfill/checker для консистентности ``hard_status`` и ``strategy_mode`` в V3."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    is_v3_campaign,
    repaired_strategy_mode_for_v3,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


async def backfill_v3_status_mode_consistency(
    *,
    dry_run: bool = True,
    adv_setting_id: int | None = None,
) -> int:
    """Проверить и (опционально) исправить рассинхрон в V3-кампаниях.

    Args:
        dry_run: Если ``True``, только считает проблемные записи без записи в БД.
        adv_setting_id: Если задан — только ключи этой РК (после включения V3 в UI).

    Returns:
        Количество найденных несогласованных ключей.
    """
    async with sm(read_only=False) as session:
        stmt = (
            select(KeywordSetting, AdvSetting.bot_active, AdvSetting.strategy)
            .join(AdvSetting, AdvSetting.id == KeywordSetting.adv_setting_id)
            .where(AdvSetting.bot_active.is_(True))
        )
        if adv_setting_id is not None:
            stmt = stmt.where(AdvSetting.id == int(adv_setting_id))
        rows = (await session.execute(stmt)).all()
        mismatched = 0
        for keyword_setting, bot_active, adv_strategy in rows:
            if not is_v3_campaign(bot_active):
                continue
            repaired_mode = repaired_strategy_mode_for_v3(
                hard_status=int(keyword_setting.hard_status),
                strategy_mode=keyword_setting.strategy_mode,
                adv_strategy=adv_strategy,
            )
            if repaired_mode == keyword_setting.strategy_mode:
                continue
            mismatched += 1
            if not dry_run:
                keyword_setting.strategy_mode = repaired_mode

        if not dry_run and mismatched:
            await session.commit()

    logger.warning(
        "V3 status/mode consistency check finished: mismatched=%s dry_run=%s",
        mismatched,
        dry_run,
    )
    return mismatched
