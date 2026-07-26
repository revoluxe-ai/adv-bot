"""Утилиты массового обновления KeywordSetting из UI adv_setting."""

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet, KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


async def update_keywords(session: AsyncSession,
                          wb_user_cabinet_original_id: int) -> int:
    """Снимает BLACK_LIST с ключей кабинета; для V3 дополнительно ставит strategy OFF.

    Args:
        session: async SQLAlchemy-сессия.
        wb_user_cabinet_original_id: id WBUserCabinet, чьи кампании обновляем.

    Returns:
        Суммарное число затронутых строк UPDATE (non-v3 + v3).
    """

    adv_setting_ids_subquery = (
        select(AdvSetting.id)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    v3_adv_setting_ids_subquery = (
        select(AdvSetting.id)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        .where(AdvSetting.automatic_version == 3)
    )
    stmt_non_v3 = (
        update(KeywordSetting)
        .where(
            KeywordSetting.adv_setting_id.in_(adv_setting_ids_subquery),
            KeywordSetting.adv_setting_id.notin_(v3_adv_setting_ids_subquery),
            KeywordSetting.hard_status == const.BLACK_LIST,
        )
        .values(hard_status=const.AUTO_MODE)
    )
    stmt_v3 = (
        update(KeywordSetting)
        .where(
            KeywordSetting.adv_setting_id.in_(v3_adv_setting_ids_subquery),
            KeywordSetting.hard_status == const.BLACK_LIST,
        )
        .values(
            hard_status=const.AUTO_MODE,
            strategy_mode=KeywordStrategyMode.OFF,
        )
    )
    update_non_v3_result = await session.execute(stmt_non_v3)
    update_v3_result = await session.execute(stmt_v3)
    if not isinstance(update_non_v3_result, CursorResult):
        raise TypeError("expected CursorResult from non-v3 KeywordSetting UPDATE")
    if not isinstance(update_v3_result, CursorResult):
        raise TypeError("expected CursorResult from v3 KeywordSetting UPDATE")
    update_non_v3_result_count = update_non_v3_result.rowcount
    update_v3_result_count = update_v3_result.rowcount
    updated_count = update_v3_result_count + update_non_v3_result_count
    await session.commit()
    return updated_count
