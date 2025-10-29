"""Модуль для расчета стоимости тарифов."""

from typing import Sequence

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.settings import settings
from .tariffs import tariffs
from .tariffs_text import text


class Pricer:
    """Класс для расчета стоимости тарифов."""

    @property
    def text(self):
        return text

    def __init__(self) -> None:
        self._tariffs = tariffs

    @staticmethod
    async def get_active_complex_advs_count(session: AsyncSession, shop_id: str) -> int:
        stmt = (
            select(AdvSetting)
            .options(
                load_only(
                    AdvSetting.adv_id,
                    AdvSetting._search_adv_id,
                    AdvSetting.name,
                    AdvSetting.active_status,
                )
            )
            .join(AdvSetting.wb_cabinet)
            .where(
                WBCabinet.shop_id == shop_id,
                AdvSetting.bot_active == True,
            )
        )

        result = await session.execute(stmt)
        auto_advs: Sequence[AdvSetting] = result.scalars().all()
        search_advs_ids = [adv.search_adv_id for adv in auto_advs if adv.search_adv_id]
        stmt_for_search_adv_ids = select(AdvSetting.adv_id).where(
            and_(
                AdvSetting.adv_id.in_(search_advs_ids),
                AdvSetting.active_status == "started",
            )
        )
        result = await session.execute(stmt_for_search_adv_ids)
        search_adv_ids: set[int] = set(result.scalars().all())
        count_active_complex_adv = 0
        for auto_adv in auto_advs:
            if (
                auto_adv.active_status == "started"
                or auto_adv.search_adv_id in search_adv_ids
            ):
                count_active_complex_adv += 1
        return count_active_complex_adv

    async def get_month_tariff_for_count_advs(
        self, session: AsyncSession, shop_id: str
    ) -> int:
        """
        Возвращает стоимость за все артикулы в зависимости от количества артикулов.
        Цена за месяц = цена_тарифа * количество_артикулов
        """
        count: int = await self.get_active_complex_advs_count(session, shop_id)
        base_tariff: int | float = self.get_price_for_count_advs_in_cabinet_for_month(
            count
        )
        automatic_tariff: int = await self.get_automactic_tariff(
            session, shop_id, count
        )
        return int(base_tariff + automatic_tariff)

    @staticmethod
    def get_tariff_for_day(tariff_for_month: int) -> float:
        return round(tariff_for_month / 30, 2)

    async def get_price_for_day_for_shop(
        self, session: AsyncSession, shop_id: str
    ) -> int | float:
        price_for_month_for_shop = await self.get_month_tariff_for_count_advs(
            session, shop_id
        )
        price_for_day = self.get_tariff_for_day(price_for_month_for_shop)
        return price_for_day

    @staticmethod
    def get_price_for_count_advs_in_cabinet_for_month(count_advs: int) -> float:
        for limit, price in sorted(tariffs.items()):
            if count_advs <= limit:
                return price * count_advs
        # Если больше всех лимитов, берем максимальную цену
        return tariffs[max(tariffs)] * count_advs

    @staticmethod
    def get_payment_for_adv(sum_payment: int, count_advs: int) -> float:
        return sum_payment / count_advs

    async def get_automactic_tariff(
        self, session: AsyncSession, shop_id: str, max_count: int
    ) -> int:
        month_tariff_for_white_list_auto_updater = (
            await self._get_month_tariff_for_white_list_updater(
                session, shop_id, max_count
            )
        )
        month_tariff_for_autoupdate_target_place = (
            await self._get_month_tariff_for_autoupdate_target_place(
                session, shop_id, max_count
            )
        )
        return (
            month_tariff_for_white_list_auto_updater
            + month_tariff_for_autoupdate_target_place
        )

    @staticmethod
    async def _get_month_tariff_for_white_list_updater(
        session: AsyncSession, shop_id: str, max_count: int
    ) -> int:
        stmt = (
            select(func.count(AdvSetting.id))
            .join(WBCabinet)
            .where(
                WBCabinet.shop_id == shop_id,
                AdvSetting.auto_update_white_list == True,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0
        count = int(count)
        count = min(count, max_count)
        sum_result: int = count * settings.WHITE_LIST_AUTO_UPDATER_MONTH_TARIFF
        return sum_result

    @staticmethod
    async def _get_month_tariff_for_autoupdate_target_place(
        session: AsyncSession, shop_id: str, max_count: int
    ) -> int:
        stmt = (
            select(func.count(AdvSetting.id))
            .join(WBCabinet)
            .where(
                WBCabinet.shop_id == shop_id,
                AdvSetting.auto_update_target_place == True,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0
        count = int(count)
        count = min(count, max_count)
        return count * settings.AUTO_UPDATE_TARGET_PLACE_MONTH_TARIFF
