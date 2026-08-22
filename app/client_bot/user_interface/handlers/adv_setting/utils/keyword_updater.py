"""Утилиты массового обновления KeywordSetting из UI adv_setting.

FINDING-PBH-010-R1: массовый hard_status reset пропускает кампании под
``is_ab_hold_structural_freeze`` (PENDING_SETUP/ACTIVE) — peer shop
``apply_defaults`` skip.

ROOT-001: результат несёт ``skipped_count`` (held кампании), чтобы UX
не утверждал A/B Hold skip при нуле пропусков.
"""

from sqlalchemy import CursorResult, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet, KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

_STRUCTURAL_FREEZE_MODES = (
    CardAbHoldMode.PENDING_SETUP.value,
    CardAbHoldMode.ACTIVE.value,
)


class KeywordUpdateResult(int):
    """Результат ``update_keywords``: int-значение = updated_count + skipped_count.

    Наследует ``int``, чтобы существующие call sites / ассерты вида
    ``assert result == N`` оставались валидны; атрибут ``skipped_count`` —
    число AdvSetting кабинета в structural freeze (PENDING_SETUP/ACTIVE).
    """

    skipped_count: int

    def __new__(
        cls, updated_count: int, skipped_count: int = 0
    ) -> "KeywordUpdateResult":
        """Создаёт int-совместимый результат с числом Hold-пропусков.

        Args:
            updated_count: суммарный rowcount UPDATE (non-v3 + v3).
            skipped_count: число кампаний кабинета под structural freeze.
        """
        obj = int.__new__(cls, updated_count)
        obj.skipped_count = skipped_count
        return obj


def _non_frozen_adv_setting_filter():
    """SQL filter: exclude PENDING_SETUP/ACTIVE (NULL/off remain eligible)."""
    return or_(
        AdvSetting.card_ab_hold_mode.is_(None),
        AdvSetting.card_ab_hold_mode.notin_(_STRUCTURAL_FREEZE_MODES),
    )


async def update_keywords(
    session: AsyncSession,
    wb_user_cabinet_original_id: int,
) -> KeywordUpdateResult:
    """Снимает BLACK_LIST с ключей кабинета; для V3 дополнительно ставит strategy OFF.

    Кампании под A/B Hold structural freeze (PENDING_SETUP/ACTIVE) пропускаются —
    ordinary hard_status mass UPDATE Forbidden (peer: apply_defaults skip).

    Args:
        session: async SQLAlchemy-сессия.
        wb_user_cabinet_original_id: id WBUserCabinet, чьи кампании обновляем.

    Returns:
        ``KeywordUpdateResult``: int-значение = число затронутых строк UPDATE;
        ``.skipped_count`` = число AdvSetting кабинета в structural freeze.
    """

    adv_setting_ids_subquery = (
        select(AdvSetting.id)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        .where(_non_frozen_adv_setting_filter())
    )
    v3_adv_setting_ids_subquery = (
        select(AdvSetting.id)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        .where(AdvSetting.bot_active.is_(True))
        .where(_non_frozen_adv_setting_filter())
    )
    skipped_count_stmt = (
        select(func.count())
        .select_from(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        .where(AdvSetting.card_ab_hold_mode.in_(_STRUCTURAL_FREEZE_MODES))
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
    skipped_count_result = await session.execute(skipped_count_stmt)
    if not isinstance(update_non_v3_result, CursorResult):
        raise TypeError("expected CursorResult from non-v3 KeywordSetting UPDATE")
    if not isinstance(update_v3_result, CursorResult):
        raise TypeError("expected CursorResult from v3 KeywordSetting UPDATE")
    update_non_v3_result_count = update_non_v3_result.rowcount
    update_v3_result_count = update_v3_result.rowcount
    updated_count = update_v3_result_count + update_non_v3_result_count
    skipped_count = int(skipped_count_result.scalar_one())
    await session.commit()
    return KeywordUpdateResult(updated_count, skipped_count)
