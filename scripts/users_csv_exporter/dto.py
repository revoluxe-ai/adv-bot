from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, AsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.pricer.pricer import Pricer, TariffDetails
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as _get_session_maker

SessionMaker = Callable[..., AsyncContextManager[AsyncSession]]


@dataclass(slots=True)
class UserCabinetExportDTO:
    user_id: int
    telegram_id: int | None
    login: str
    cabinet_name: str
    shop_id: str
    balance: float
    bonus: float
    balance_plus_bonus: float
    active_campaigns: int
    has_active_campaign: bool
    tariff_mode: str | None
    tariff_count: int | None
    tariff_price_per_adv: float | None
    tariff_total_per_month: float | None
    tariff_total_per_day: float | None
    balance_days_left: float | None

    @classmethod
    async def from_models(
        cls,
        user: User,
        wb_user_cabinet: WBUserCabinet,
        pricer: Pricer,
        session_maker: SessionMaker = _get_session_maker,
    ) -> "UserCabinetExportDTO":
        cabinet = wb_user_cabinet.wb_cabinet
        balance = _to_float(cabinet.calculated_balance)
        bonus = _to_float(cabinet.calculated_bonus)
        balance_plus_bonus = balance + bonus

        adv_settings = getattr(cabinet, "adv_settings", []) or []
        active_campaigns = sum(1 for adv in adv_settings if adv.bot_active)

        tariff_details = await _fetch_tariff_details(
            pricer, cabinet.shop_id, session_maker
        )
        total_per_day = (
            tariff_details.total_per_day if tariff_details else 0.0
        )
        balance_days_left = (
            balance_plus_bonus / total_per_day
            if total_per_day
            else None
        )

        return cls(
            user_id=user.id,
            telegram_id=user.user_telegram_id,
            login=user.username or "",
            cabinet_name=wb_user_cabinet.name,
            shop_id=cabinet.shop_id,
            balance=balance,
            bonus=bonus,
            balance_plus_bonus=balance_plus_bonus,
            active_campaigns=active_campaigns,
            has_active_campaign=active_campaigns > 0,
            tariff_mode=tariff_details.mode.value if tariff_details else None,
            tariff_count=tariff_details.count if tariff_details else None,
            tariff_price_per_adv=tariff_details.price_per_adv
            if tariff_details
            else None,
            tariff_total_per_month=tariff_details.total_per_month
            if tariff_details
            else None,
            tariff_total_per_day=tariff_details.total_per_day
            if tariff_details
            else None,
            balance_days_left=balance_days_left,
        )


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


async def _fetch_tariff_details(
    pricer: Pricer, shop_id: str, session_maker: SessionMaker
) -> TariffDetails | None:
    async with session_maker(read_only=True) as session:
        return await pricer.get_tariff_details(session, shop_id)
