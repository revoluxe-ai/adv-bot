"""Shared logic for checking balance before enabling paid options (unified financial pattern)."""

from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules import balance_manager
from app.modules.common_slaves.wildberries.models import AdvSetting


def format_insufficient_funds_message(required_price: float, available: float) -> str:
    """Single message text for 'insufficient funds' used by all paid-option toggles."""
    return (
        f"Недостаточно средств для включения настройки: "
        f"нужно {required_price:.2f} ₽, доступно {available:.2f} ₽.\n"
        "Пополните баланс и попробуйте снова."
    )


async def get_adv_setting_and_check_funds_for_enabling(
    session: AsyncSession,
    *,
    adv_id: int | None = None,
    adv_setting_id: int | None = None,
    send_adv_not_found: Callable[[], Awaitable[object]],
    send_no_cabinet: Callable[[], Awaitable[object]],
    get_required_price: Callable[
        [AsyncSession, str, int], Awaitable[float]
    ] | None = None,
    send_insufficient_funds: Callable[[float, float], Awaitable[object]]
    | None = None,
) -> AdvSetting | None:
    """Load AdvSetting (by adv_id or adv_setting_id), run null checks and optionally balance check.

    When get_required_price and send_insufficient_funds are provided, also checks that
    balance+bonus >= required price and invokes send_insufficient_funds on failure.
    Callbacks are used so this module stays free of telegram/bot dependencies.
    Returns the AdvSetting if all checks pass, None otherwise (callbacks are invoked on failure).
    """
    if (adv_id is None) == (adv_setting_id is None):
        raise ValueError("Exactly one of adv_id or adv_setting_id must be set")

    if adv_id is not None:
        stmt = (
            select(AdvSetting)
            .options(selectinload(AdvSetting.wb_cabinet))
            .where(AdvSetting.adv_id == adv_id)
        )
    else:
        stmt = (
            select(AdvSetting)
            .options(selectinload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_setting_id)
        )
    adv_setting = await session.scalar(stmt)
    if adv_setting is None:
        await send_adv_not_found()
        return None
    if adv_setting.wb_cabinet is None:
        await send_no_cabinet()
        return None

    if get_required_price is not None and send_insufficient_funds is not None:
        balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(
            adv_setting.wb_cabinet.id
        )
        available = balance + bonus
        shop_id = adv_setting.wb_cabinet.shop_id or ""
        required_price = await get_required_price(
            session, shop_id, adv_setting.id
        )
        if available < required_price:
            await send_insufficient_funds(required_price, available)
            return None

    return adv_setting
