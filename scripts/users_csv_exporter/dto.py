from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, AsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.pricer.pricer import Pricer, TariffDetails
from app.modules.common_advs_stat.wb_common_stat_period_totals import (
    sum_orders_and_buyouts_last_days_rub,
)
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as _get_session_maker

SessionMaker = Callable[..., AsyncContextManager[AsyncSession]]


@dataclass(slots=True)
class UserCabinetDTO:
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
    last_30_days_topups: float
    last_30_days_orders_sum_rub: float
    last_30_days_buyouts_sum_rub: float

    @classmethod
    async def from_wb_user_cabinet(
        cls,
        wb_user_cabinet: WBUserCabinet,
        pricer: Pricer,
        session_maker: SessionMaker = _get_session_maker,
    ) -> "UserCabinetDTO":
        cabinet = wb_user_cabinet.wb_cabinet

        balance = _to_float(cabinet.calculated_balance)
        bonus = _to_float(cabinet.calculated_bonus)
        balance_plus_bonus = balance + bonus

        adv_settings = getattr(cabinet, "adv_settings", None) or []
        active_campaigns = sum(1 for adv in adv_settings if adv.bot_active)

        tariff_details = await _fetch_tariff_details(
            pricer=pricer,
            shop_id=cabinet.shop_id,
            session_maker=session_maker,
        )

        total_per_day = tariff_details.total_per_day if tariff_details else 0.0
        balance_days_left = (
            balance_plus_bonus / total_per_day
            if total_per_day
            else None
        )

        cutoff = datetime.utcnow() - timedelta(days=30)
        topups = _sum_recent_payments(cabinet.balance_payments, cutoff)
        topups += _sum_recent_payments(cabinet.bonus_payments, cutoff)

        nmids = _cabinet_adv_nmids(cabinet)
        orders_rub, buyouts_rub = await sum_orders_and_buyouts_last_days_rub(
            nmids, pass_days=30
        )

        return cls(
            cabinet_name=wb_user_cabinet.name,
            shop_id=cabinet.shop_id,
            balance=balance,
            bonus=bonus,
            balance_plus_bonus=balance_plus_bonus,
            active_campaigns=active_campaigns,
            has_active_campaign=active_campaigns > 0,
            tariff_mode=tariff_details.mode.value if tariff_details else None,
            tariff_count=tariff_details.count if tariff_details else None,
            tariff_price_per_adv=tariff_details.price_per_adv if tariff_details else None,
            tariff_total_per_month=tariff_details.total_per_month if tariff_details else None,
            tariff_total_per_day=tariff_details.total_per_day if tariff_details else None,
            balance_days_left=balance_days_left,
            last_30_days_topups=topups,
            last_30_days_orders_sum_rub=orders_rub,
            last_30_days_buyouts_sum_rub=buyouts_rub,
        )


@dataclass(slots=True)
class UserDTO:
    user_id: int
    telegram_id: int | None
    login: str
    cabinets: list[UserCabinetDTO]

    @classmethod
    async def from_user(
        cls,
        user: User,
        pricer: Pricer,
        session_maker: SessionMaker = _get_session_maker,
    ) -> "UserDTO":
        # ВАЖНО: relation должен быть загружен (selectinload/joinedload),
        # иначе на async ORM может прилететь lazy-load в неожиданный момент.
        wb_user_cabinets = getattr(user, "wb_user_cabinets", None) or []

        cabinets_dto = [
            await UserCabinetDTO.from_wb_user_cabinet(
                wb_user_cabinet=wb_uc,
                pricer=pricer,
                session_maker=session_maker,
            )
            for wb_uc in wb_user_cabinets
        ]

        return cls(
            user_id=user.id,
            telegram_id=user.user_telegram_id,
            login=user.username or "",
            cabinets=cabinets_dto,
        )


def _cabinet_adv_nmids(cabinet: WBCabinet) -> list[int]:
    adv_settings = getattr(cabinet, "adv_settings", None) or []
    seen: set[int] = set()
    for adv in adv_settings:
        raw = getattr(adv, "nmids", None) or []
        for n in raw:
            try:
                seen.add(int(n))
            except (TypeError, ValueError):
                continue
    return list(seen)


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


def _sum_recent_payments(
    payments: Iterable[Any] | None, cutoff: datetime
) -> float:
    if not payments:
        return 0.0

    total = 0.0
    for payment in payments:
        if not payment:
            continue
        amount = getattr(payment, "amount", None)
        timestamp = getattr(payment, "transaction_date_time", None)
        if amount is None or timestamp is None:
            continue
        if amount <= 0:
            continue
        if timestamp < cutoff:
            continue
        total += float(amount)
    return total
